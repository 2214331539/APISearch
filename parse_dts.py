#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析金蝶云·苍穹/星瀚 (Kingdee Cloud Cosmic) 导出的 .dts API 元数据文件,
批量抽取为统一的 JSON,作为 AI 检索系统的数据底座。

每个 .dts 文件由若干段拼接: (headerJSON)@ISC@[dataArray] ...
真正的 API 定义段是其 data 记录里含 `urlformat` 字段的那段;
其余 (分组 openapi_custom_sort / open_customgroup 等) 跳过。

用法:
    python3 parse_dts.py [源目录] [输出文件]
默认:
    源目录  = ./API服务(openapi_apilist)_A374
    输出文件 = ./api_index.json
"""

import os
import sys
import json
import re


# httpmethod 取值映射 (金蝶枚举)。未知值保留原值。
HTTP_METHOD = {"1": "POST", "2": "GET", "3": "PUT", "4": "DELETE", "5": "PATCH"}


def pick_lang(val, prefer=("zh_CN", "GLang", "zh_TW", "en_US")):
    """从多语言字段里取中文值;若不是 dict 直接返回。"""
    if isinstance(val, dict):
        for k in prefer:
            if val.get(k):
                return val[k]
        # 退而求其次取任意一个非空值
        for v in val.values():
            if v:
                return v
        return ""
    return val if val is not None else ""


def locate_api_segment(raw):
    """
    定位真正的 API 定义所在的数据段文本 (含 "urlformat" 的那段)。
    原文形如:  (h0)@ISC@[d0](h1)@ISC@[d1]...   按 @ISC@ split 后,
    data 数组在 parts[1:] 中,可能尾随下一个 header。返回从 '[' 起的子串。
    """
    parts = raw.split("@ISC@")
    # 优先含 urlformat 的段;截断文件回退到含接口定义标记的段
    for markers in (('"urlformat"',),
                    ('"bodyentryentity"', '"respentryentity"', '"methodname"',
                     '"apiservicetype"')):
        for seg in parts[1:]:
            if any(mk in seg for mk in markers):
                i = seg.find("[")
                if i >= 0:
                    return seg[i:]
    return None


def extract_balanced_array(text, key):
    """从 text 中按平衡括号抽出 "key":[ ... ] 子数组并解析。截断/失败返回 None。"""
    anchor = text.find('"%s":[' % key)
    if anchor < 0:
        return None
    start = text.find("[", anchor)
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
    return None  # 在闭合前被截断


_SCALAR_RE = {
    "number": r'"number":"([^"]*)"',
    "methodname": r'"methodname":"([^"]*)"',
    "urlformat": r'"urlformat":"([^"]*)"',
    "httpmethod": r'"httpmethod":"([^"]*)"',
    "classname": r'"classname":"([^"]*)"',
    "version": r'"version":"([^"]*)"',
}


def salvage_record(text):
    """对截断的数据段做尽力抢救: 抽出 body/resp 子数组 + 关键标量字段。"""
    rec = {}
    for key, pat in _SCALAR_RE.items():
        m = re.search(pat, text)
        if m:
            rec[key] = m.group(1)
    # 接口中文名留空, 由 parse_file 用文件名兜底 (截断文件里 "name" 多为创建人, 不可靠)
    rec["bodyentryentity"] = extract_balanced_array(text, "bodyentryentity") or []
    rec["respentryentity"] = extract_balanced_array(text, "respentryentity") or []
    return rec


def extract_body_params(rec):
    """抽取请求体参数 (bodyentryentity)。保留层级关系。"""
    out = []
    for p in rec.get("bodyentryentity", []) or []:
        ml = (p.get("multilanguagetext") or [{}])
        example = pick_lang(p.get("example")) or (ml[0].get("example") if ml else "")
        out.append({
            "name": p.get("paramname", ""),
            "type": p.get("paramtype", ""),
            "desc": pick_lang(p.get("bodyparamdes")),
            "required": str(p.get("must", "")) == "1",
            "level": int(p.get("body_level", 1) or 1),
            "is_list": bool(p.get("is_req_mul_value")),
            "example": example,
            "_id": p.get("id"),
            "_pid": p.get("pid"),
        })
    return out


def extract_resp_params(rec):
    """抽取返回参数 (respentryentity)。保留层级关系。"""
    out = []
    for p in rec.get("respentryentity", []) or []:
        out.append({
            "name": p.get("respparamname", ""),
            "type": p.get("respparamtype", ""),
            "desc": pick_lang(p.get("respdes")),
            "required": str(p.get("respparammust", "")) == "1",
            "level": int(p.get("resp_level", 1) or 1),
            "is_list": bool(p.get("is_resp_mul_value")),
            "example": pick_lang(p.get("respexample")),
            "_id": p.get("id"),
            "_pid": p.get("pid"),
        })
    return out


def build_search_text(api):
    """拼一段供 embedding / LLM 阅读的扁平化语义文本。"""
    lines = [f"接口名称: {api['name']}",
             f"接口编码: {api['number']}",
             f"URL: {api['url']}  方法: {api['http_method']}",
             f"所属模块: {api['cloud']} / {api['app']}"]
    if api.get("group"):
        lines.append(f"分组: {api['group']}")
    if api.get("description"):
        lines.append(f"说明: {api['description']}")

    def fmt(params, title):
        if not params:
            return
        lines.append(title + ":")
        for p in params:
            indent = "  " * max(0, p["level"] - 1)
            req = "必填" if p["required"] else "可选"
            lst = "[]" if p["is_list"] else ""
            lines.append(f"  {indent}- {p['name']}{lst} ({p['type']}, {req}): {p['desc']}")

    fmt(api["request_params"], "请求参数")
    fmt(api["response_params"], "返回参数")
    return "\n".join(lines)


def name_from_filename(fname):
    """从文件名 `前缀_<中文名>(<method>)_A374.dts` 抽中文名,作为兜底显示名。"""
    base = re.sub(r"\.dts$", "", fname)
    base = re.sub(r"_A374$", "", base)
    m = re.match(r"^(?:API服务|自定义API)_(.*?)\([^()]*\)$", base)
    return m.group(1) if m else base


def parse_file(path):
    raw = open(path, encoding="utf-8").read()
    seg = locate_api_segment(raw)
    if seg is None:
        raise ValueError("未找到含 urlformat 的 API 定义段")

    partial = False
    try:
        obj, _ = json.JSONDecoder().raw_decode(seg)   # 正常路径
        rec = obj[0] if isinstance(obj, list) and obj else {}
    except (json.JSONDecodeError, IndexError):
        rec = salvage_record(seg)                      # 截断文件: 尽力抢救
        partial = True

    fname = os.path.basename(path)
    api_type = "自定义API" if fname.startswith("自定义API") else "标准API"

    # 分组: 自定义用 customsort.name, 标准用 header 里的 group(若有)
    group = ""
    cs = rec.get("customsort")
    if isinstance(cs, dict):
        group = pick_lang(cs.get("name"))

    appinfo = rec.get("appid") or {}
    app_name = pick_lang(appinfo.get("name")) if isinstance(appinfo, dict) else ""
    cloud = ""
    if isinstance(appinfo, dict):
        bc = appinfo.get("bizcloud") or {}
        cloud = pick_lang(bc.get("name")) if isinstance(bc, dict) else ""

    http_raw = str(rec.get("httpmethod", ""))
    api = {
        "file": fname,
        "api_type": api_type,
        "partial": partial,
        "name": pick_lang(rec.get("name")) or name_from_filename(fname),
        "number": rec.get("number", ""),
        "method_name": rec.get("methodname", ""),
        "url": rec.get("urlformat", ""),
        "http_method": HTTP_METHOD.get(http_raw, http_raw),
        "app": app_name,
        "cloud": cloud,
        "group": group,
        "description": pick_lang(rec.get("discription")) or pick_lang(rec.get("remark")),
        "class_name": rec.get("classname", ""),
        "version": rec.get("version", ""),
        "request_params": extract_body_params(rec),
        "response_params": extract_resp_params(rec),
    }
    api["search_text"] = build_search_text(api)
    return api


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "API服务(openapi_apilist)_A374")
    out = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_index.json")

    files = sorted(f for f in os.listdir(src) if f.endswith(".dts"))
    apis, errors = [], []
    for f in files:
        try:
            apis.append(parse_file(os.path.join(src, f)))
        except Exception as e:
            errors.append((f, str(e)))

    with open(out, "w", encoding="utf-8") as fh:
        json.dump(apis, fh, ensure_ascii=False, indent=2)

    print(f"源目录   : {src}")
    print(f"输出文件 : {out}")
    print(f".dts 总数: {len(files)}")
    print(f"成功解析 : {len(apis)}")
    print(f"解析失败 : {len(errors)}")
    if errors:
        print("\n失败列表 (前20):")
        for f, e in errors[:20]:
            print(f"  - {f}: {e}")

    # 简单统计
    if apis:
        n_no_body = sum(1 for a in apis if not a["request_params"])
        n_no_resp = sum(1 for a in apis if not a["response_params"])
        print(f"\n无请求参数的接口: {n_no_body}   无返回参数的接口: {n_no_resp}")


if __name__ == "__main__":
    main()
