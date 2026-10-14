"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts/core";
import { MapChart } from "echarts/charts";
import {
  GeoComponent,
  TooltipComponent,
  VisualMapComponent,
  AriaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { getData } from "@/lib/api";
echarts.use([
  MapChart,
  GeoComponent,
  TooltipComponent,
  VisualMapComponent,
  AriaComponent,
  CanvasRenderer,
]);
export function RegionalMap({
  params,
  onSelect,
}: {
  params: string;
  onSelect: (id: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  const q = useQuery({
    queryKey: ["regions/ranking", params],
    queryFn: ({ signal }) => getData("regions/ranking", params, signal),
  });
  useEffect(() => {
    if (!ref.current || !q.data) return;
    let cancelled = false;
    let chart: echarts.ECharts | undefined;
    let observer: ResizeObserver | undefined;
    fetch("/dno-regions.geojson")
      .then((r) => {
        if (!r.ok) throw Error();
        return r.json();
      })
      .then((geo) => {
        if (cancelled || !ref.current) return;
        echarts.registerMap("gb-dno", geo);
        chart = echarts.init(ref.current);
        chart.setOption({
          animation: false,
          aria: { enabled: true },
          tooltip: {
            trigger: "item",
            formatter: (p: { name: string; value: number }) => {
              const r = q.data.rows.find((r) => String(r.id) === p.name);
              return r
                ? `${r.name}: ${Number(r.value).toFixed(2)} gCO₂/kWh`
                : "No observation";
            },
          },
          visualMap: {
            min: 0,
            max: 400,
            left: 10,
            bottom: 5,
            orient: "horizontal",
            text: ["Higher", "Lower"],
            textStyle: { fontSize: 9, color: "#596a60" },
            inRange: { color: ["#dceac8", "#73b18a", "#235d4e", "#173e35"] },
          },
          series: [
            {
              type: "map",
              map: "gb-dno",
              roam: false,
              layoutCenter: ["50%", "47%"],
              layoutSize: "95%",
              itemStyle: { borderColor: "#fff", borderWidth: 1 },
              emphasis: {
                label: { show: false },
                itemStyle: { areaColor: "#e4b44e" },
              },
              data: q.data.rows.map((r) => ({
                name: String(r.id),
                value: Number(r.value),
              })),
            },
          ],
        });
        chart.on("click", (p) => onSelect(p.name));
        observer = new ResizeObserver(() => chart?.resize());
        observer.observe(ref.current);
      })
      .catch(() => setError(true));
    return () => {
      cancelled = true;
      observer?.disconnect();
      chart?.dispose();
    };
  }, [q.data, onSelect]);
  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Carbon intensity, in place</h2>
          <p>NESO 2024 DNO boundaries · select a region to inspect</p>
        </div>
      </header>
      {error || q.isError ? (
        <p className="empty">
          The licensed boundary layer is unavailable. Use the regional rankings.
        </p>
      ) : (
        <div
          ref={ref}
          className="chart"
          style={{ height: 350 }}
          role="img"
          aria-label="Choropleth of 14 Great Britain DNO regions, showing mean forecast carbon intensity"
        />
      )}
      <p style={{ padding: "12px 20px", fontSize: 9, color: "#596a60" }}>
        Source: NESO Open Data Licence. Approximate DNO boundaries; simplified
        for display.
      </p>
    </section>
  );
}
