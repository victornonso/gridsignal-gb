"use client";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getData, number, Row } from "@/lib/api";
import { chartOption } from "@/lib/charts";
const Chart = dynamic(() => import("./Chart"), {
  ssr: false,
  loading: () => <div className="skeleton chart" />,
});
function LoadingChart() {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(timer);
  }, []);
  return (
    <div role="status" aria-live="polite">
      <div className="skeleton chart" aria-hidden="true" />
      {slow && (
        <p className="empty">
          Connecting to the analytics service. After inactivity, this can take about a minute.
        </p>
      )}
    </div>
  );
}
export function DataTable({
  rows,
  onRow,
}: {
  rows: Row[];
  onRow?: (row: Row) => void;
}) {
  if (!rows.length)
    return (
      <p className="empty">
        No persisted observations in this selection. Try another period.
      </p>
    );
  const keys = Object.keys(rows[0]).filter(
    (k) => !["record_hash", "error", "old_value", "new_value"].includes(k),
  );
  return (
    <div className="table-scroll" tabIndex={0} aria-label="Scrollable data table">
      <table>
        <thead>
          <tr>
            {keys.map((k) => (
              <th scope="col" key={k}>
                {k.replaceAll("_", " ")}
              </th>
            ))}
            {onRow && <th scope="col">Explore</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={String(r.id ?? r.time ?? i)}>
              {keys.map((k) => (
                <td key={k}>
                  {r[k] === null
                    ? "—"
                    : typeof r[k] === "boolean"
                      ? r[k]
                        ? "Yes"
                        : "No"
                      : typeof r[k] === "object"
                        ? JSON.stringify(r[k])
                        : typeof r[k] === "number"
                          ? number(r[k], 2)
                          : String(r[k])}
                </td>
              ))}
              {onRow && (
                <td>
                  <button className="text-button" onClick={() => onRow(r)}>
                    Details →
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function AnalyticsPanel({
  title,
  subtitle,
  route,
  params,
  kind = "line",
  keys = ["value"],
  x = "time",
  wide = false,
  onSelect,
  onRow,
}: {
  title: string;
  subtitle: string;
  route: string;
  params: string;
  kind?: string;
  keys?: string[];
  x?: string;
  wide?: boolean;
  onSelect?: (value: string) => void;
  onRow?: (row: Row) => void;
}) {
  const q = useQuery({
    queryKey: [route, params],
    queryFn: ({ signal }) => getData(route, params, signal),
  });
  return (
    <section className={`panel ${wide ? "wide" : ""}`}>
      <header className="panel-header">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span className="panel-dot" aria-hidden="true" />
      </header>
      {q.isPending ? (
        <LoadingChart />
      ) : q.isError ? (
        <div className="error" role="alert">
          {q.error.message}
          <button onClick={() => q.refetch()}>Retry</button>
        </div>
      ) : !q.data.rows.length ? (
        <div className="empty">
          No observations in this selection.
          <br />
          <span>Change the period or check Data Operations.</span>
        </div>
      ) : kind === "table" ? (
        <DataTable rows={q.data.rows} onRow={onRow} />
      ) : (
        <Chart
          option={chartOption(q.data.rows, kind, keys, x)}
          label={`${title}. ${subtitle}. Data table follows.`}
          onSelect={onSelect}
        />
      )}
      {q.data?.meta.possibly_truncated && (
        <p className="result-limit">
          This view reached its row limit. Narrow the period or use CSV export
          for all filtered results.
        </p>
      )}
      {kind !== "table" && q.data?.rows.length ? (
        <details className="chart-data">
          <summary>View accessible data table</summary>
          <DataTable rows={q.data.rows} />
        </details>
      ) : null}
    </section>
  );
}
