#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据供应链项目的数据需求, 从 api_index.json 抽取所选接口, 生成 接口文档汇总.md。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
apis = json.load(open(os.path.join(HERE, "api_index.json"), encoding="utf-8"))
by_url = {a["url"]: a for a in apis if a["url"]}

# 每个数据需求选定的接口 (url 唯一定位) + 业务标注
PICKS = [
    dict(no="1", label="物料主数据", status="✅ 已通（8300+）", purpose="货品库基础",
         url="/v2/mzv0/basedata/bd_material/Cus_MaterialInfoAI",
         note="货品主档来源。物料编码是后续所有接口的关联主键。"),
    dict(no="2", label="即时库存", status="✅ 已通（3900+）", purpose="各货品可用量",
         url="/v2/mzv0/im/im_inv_realbalance/AI_inv_realbalance",
         note="返回 `baseqty`（基本单位库存量），即 MRP 的现有可用量起点。\n"
              "> 同实体另有 `Cus_inv_realbalance`（入参为单值非数组）与 "
              "`WMS_inv_realbalanceQuery`（中山待检专用），字段一致，按调用方式择一。"),
    dict(no="3", label="生产BOM", status="✅ 已通（15900+，多层）", purpose="产品→子物料结构",
         url="/v2/fmm/pdm_mftbom/bomQuery",
         note="按 `material_masterid_number`（产品物料编码）查单层 BOM，返回 `entry` 组件明细。\n"
              "> 多层完整展开需用 `getBomForwardExpandResult`（BOM正查），其入参是 `bomid` 而非物料编码，"
              "需先用本接口取 BOM 内码。MRP 需求分解走「BOM 逐层展开 × 母件需求量」。"),
    dict(no="4", label="在制工单", status="🔴 2505 未订阅", purpose="MRP 在制抵扣",
         url="/v2/pom/pom_mftorder/batchQueryNew",
         note="生产工单批量查询（新）。在制抵扣量 = 工单数量 − 已入库数量（关注明细中的数量/状态字段）。\n"
              "> 状态：**需在 2505 环境订阅该接口后方可调用。**"),
    dict(no="5", label="采购在采", status="🔴 金蝶原列未提供，本汇总推荐替代接口", purpose="MRP 在采抵扣",
         url="/v2/pur/purorder/queryprogress",
         note="**推荐用「采购执行进度查询」**：返回订单 `qty` 与 `suminstockqty`（已入库）、"
              "`sumreceiptqty`（已收货）等，**在采未到货量 = qty − suminstockqty**，正是 MRP 在采抵扣所需。\n"
              "> 备选：`采购订单详情查询`（`/v2/pm/pm_purorderbill/query`，出参更全但需逐单查）。\n"
              "> 注意：本接口属 **SRM云·供应商协同**，仅覆盖走 SRM 协同的采购订单；若有非协同采购，"
              "需改用 `pm_purorderbill/query` 并自行汇总未入库量。单次最多返回 1000 条，需按 `pageIndex` 翻页。"),
    dict(no="6", label="历史销量", status="🔴 2505 未订阅", purpose="报表/外部预测参考（替代旺店通）",
         url="/v2/mzv0/im/im_saloutbill/Cus_im_saloutbillQuery",
         note="销售出库单查询（二开），作为历史销量/预测输入。\n"
              "> 状态：**需在 2505 环境订阅该接口后方可调用。**"),
]


def param_rows(params):
    rows = []
    for p in params:
        indent = "　" * max(0, p["level"] - 1)            # 全角空格表层级
        name = indent + ("└ " if p["level"] > 1 else "") + p["name"]
        if p["is_list"]:
            name += " []"
        req = "必填" if p["required"] else "可选"
        desc = (p["desc"] or "").replace("\n", " ").replace("|", "\\|")
        rows.append(f"| {name} | `{p['type']}` | {req} | {desc} |")
    return rows


def render_table(title, params):
    if not params:
        return [f"**{title}**: 无\n"]
    head = [f"**{title}**（{len(params)} 项）", "",
            "| 参数 | 类型 | 必填 | 说明 |", "|---|---|---|---|"]
    body = param_rows(params)
    table = head + body + [""]
    if len(params) > 35:   # 大表折叠, 保持文档可读
        return [f"<details><summary>{title}（{len(params)} 项，点击展开）</summary>", ""] + \
               head[2:] + body + ["", "</details>", ""]
    return table


lines = []
lines += [
    "# 供应链管理项目 · 金蝶接口文档汇总", "",
    "> 本文档由 `gen_summary.py` 从 `api_index.json`（解析自 1781 个 `.dts`）自动生成，参数与源接口文档一致。",
    "> 数据来源环境：金蝶云·苍穹/星瀚（A374）。", "",
    "## 一、通用调用说明", "",
    "所有接口均为 **POST**，请求头通用如下：", "",
    "| Header | 说明 |", "|---|---|",
    "| `Content-Type` | `application/json` |",
    "| `accesstoken` | 鉴权令牌（Token 方式）；其它策略见金蝶《认证鉴权指南》 |",
    "| `x-acgw-identity` | 调用方身份标识，第三方应用启用后自动颁发 |",
    "| `Idempotency-Key` | 选填，唯一 requestId，防止重复调用 |", "",
    "完整 URL = 网关域名 + 下表 `URL` 路径。", "",
    "## 二、数据需求 ↔ 接口总览", "",
    "| # | 数据 | 接口（number） | URL | 用途 | 状态 |",
    "|---|---|---|---|---|---|",
]
for p in PICKS:
    a = by_url.get(p["url"], {})
    lines.append(f"| {p['no']} | {p['label']} | `{a.get('number','?')}` | `{p['url']}` "
                 f"| {p['purpose']} | {p['status']} |")
lines += ["",
          "**MRP 净需求参考公式**：",
          "```",
          "净需求 = BOM展开需求量(3)  −  现有库存(2)  −  在制量(4)  −  在采未到货量(5)",
          "```",
          "其中历史销量(6)用于驱动需求预测，物料主数据(1)提供全链路关联主键（物料编码）。", "",
          "## 三、接口明细", ""]

for p in PICKS:
    a = by_url.get(p["url"])
    lines.append(f"### {p['no']}. {p['label']} — {p['status']}")
    lines.append("")
    if not a:
        lines += [f"> ⚠ 在 api_index.json 中未找到 `{p['url']}`。", ""]
        continue
    lines += ["| 项 | 值 |", "|---|---|",
              f"| 接口名称 | {a['name']} |",
              f"| 接口编码 number | `{a['number']}` |",
              f"| URL | `{a['url']}` |",
              f"| 方法 | {a['http_method']} |",
              f"| 所属模块 | {a['cloud']} / {a['app']} |"]
    if a.get("group"):
        lines.append(f"| 分组 | {a['group']} |")
    if a.get("description"):
        lines.append(f"| 接口说明 | {a['description']} |")
    lines.append(f"| 源文件 | `{a['file']}` |")
    lines.append("")
    lines += [f"**用途/调用要点**：{p['note']}", ""]
    lines += render_table("请求参数", a["request_params"])
    lines += render_table("返回参数", a["response_params"])
    lines += ["---", ""]

out = os.path.join(HERE, "接口文档汇总.md")
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("已生成:", out)
print("接口数:", len(PICKS), " 文件大小(KB):", round(os.path.getsize(out) / 1024, 1))
