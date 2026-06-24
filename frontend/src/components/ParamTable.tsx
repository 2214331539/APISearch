import type { ApiParam } from "../api/types";

type ParamTableProps = {
  params: ApiParam[];
  emptyLabel: string;
};

export function ParamTable({ params, emptyLabel }: ParamTableProps) {
  if (!params.length) {
    return <div className="empty-strip">{emptyLabel}</div>;
  }

  return (
    <div className="param-table-wrap">
      <table className="param-table">
        <thead>
          <tr>
            <th>参数</th>
            <th>类型</th>
            <th>约束</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          {params.map((param, index) => (
            <tr key={`${param.name}-${index}`}>
              <td>
                <span className="param-name" style={{ paddingLeft: `${Math.max(0, param.level - 1) * 16}px` }}>
                  {param.level > 1 ? "└ " : ""}
                  {param.name}
                  {param.is_list ? "[]" : ""}
                </span>
              </td>
              <td>
                <code>{param.type || "-"}</code>
              </td>
              <td>
                <span className={param.required ? "tag danger" : "tag"}>{param.required ? "必填" : "可选"}</span>
              </td>
              <td>{param.desc || param.example || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
