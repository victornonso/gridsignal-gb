import type { EChartsCoreOption } from "echarts/core";
import type { Row } from "./api";
const fuelColours: Record<string, string> = {
  wind: "#57b794",
  solar: "#e4b44e",
  gas: "#c78a56",
  nuclear: "#9d8bc4",
  hydro: "#499eb1",
  biomass: "#989a45",
  coal: "#6c7075",
  imports: "#648bbb",
  other: "#a6adb3",
  oil: "#a36e66",
  pumped_storage: "#789fba",
};
const colours = [
  "#2d8066",
  "#c78a56",
  "#648bbb",
  "#9d8bc4",
  "#e4b44e",
  "#499eb1",
  "#989a45",
  "#6c7075",
  "#a6adb3",
];
const base: EChartsCoreOption = {
  color: colours,
  textStyle: {
    fontFamily: "Arial, sans-serif",
    color: "#65716b",
    fontSize: 11,
  },
  tooltip: {
    trigger: "axis",
    backgroundColor: "#fff",
    borderColor: "#dce3dd",
    textStyle: { color: "#253c32", fontSize: 12 },
  },
  legend: {
    bottom: 0,
    icon: "circle",
    itemWidth: 7,
    itemHeight: 7,
    textStyle: { fontSize: 10, color: "#65716b" },
  },
  grid: { left: 52, right: 24, top: 24, bottom: 54 },
  xAxis: {
    type: "category",
    axisLine: { lineStyle: { color: "#dce3dd" } },
    axisTick: { show: false },
    axisLabel: { color: "#65716b", fontSize: 10 },
  },
  yAxis: {
    type: "value",
    splitLine: { lineStyle: { color: "#edf0eb" } },
    axisLabel: { fontSize: 10 },
  },
};
export function chartOption(
  rows: Row[],
  kind: string,
  keys: string[],
  x = "time",
): EChartsCoreOption {
  if (kind === "donut")
    return {
      ...base,
      tooltip: { trigger: "item", formatter: "{b}: {c}%" },
      legend: { bottom: 0 },
      series: [
        {
          type: "pie",
          radius: ["48%", "70%"],
          center: ["50%", "44%"],
          label: { show: false },
          itemStyle: { borderColor: "#fff", borderWidth: 3 },
          data: rows.map((r) => ({
            name: r.label || r.fuel_id,
            value: Number(r.share),
            itemStyle: { color: String(r.colour || colours[0]) },
          })),
        },
      ],
    };
  if (kind === "heatmap") {
    const days = [...new Set(rows.map((r) => String(r.day)))];
    const hours = [...new Set(rows.map((r) => String(r.hour)))];
    return {
      ...base,
      grid: { left: 80, right: 18, top: 15, bottom: 55 },
      xAxis: { type: "category", data: hours },
      yAxis: { type: "category", data: days },
      visualMap: {
        min: 0,
        max: 400,
        show: false,
        inRange: { color: ["#f3f4e9", "#afd0ae", "#2d8066", "#163c32"] },
      },
      series: [
        {
          type: "heatmap",
          data: rows.map((r) => [
            hours.indexOf(String(r.hour)),
            days.indexOf(String(r.day)),
            Number(r.value),
          ]),
        },
      ],
    };
  }
  if (kind === "profile") {
    const hours = [...new Set(rows.map((r) => String(r.hour)))];
    return {
      ...base,
      xAxis: { ...(base.xAxis as object), data: hours },
      series: [false, true].map((weekend, i) => ({
        name: weekend ? "Weekends" : "Weekdays",
        type: "line",
        showSymbol: false,
        lineStyle: { width: 2 },
        itemStyle: { color: colours[i] },
        data: hours.map((h) => {
          const r = rows.find(
            (r) => String(r.hour) === h && r.weekend === weekend,
          );
          return r ? Number(r[keys[0] || "value"]) : null;
        }),
      })),
    };
  }
  if (kind === "ranking")
    return {
      ...base,
      grid: { left: 125, right: 30, top: 12, bottom: 32 },
      legend: { show: false },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "#edf0eb" } } },
      yAxis: {
        type: "category",
        inverse: true,
        data: rows.map((r) => r.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 10 },
      },
      series: [
        {
          type: "bar",
          barWidth: 11,
          itemStyle: { borderRadius: [0, 3, 3, 0], color: "#2d8066" },
          data: rows.map((r) => Number(r.value)),
        },
      ],
    };
  if (kind === "stacked" || kind === "multi" || kind === "outturn") {
    const category = kind === "multi" ? "region_id" : "fuel_id";
    const value =
      kind === "stacked" ? "share" : kind === "outturn" ? "power_mw" : "value";
    const times = [...new Set(rows.map((r) => String(r.time)))];
    const groups = [...new Set(rows.map((r) => String(r[category])))];
    return {
      ...base,
      xAxis: { ...(base.xAxis as object), data: times },
      series: groups.map((g, i) => ({
        name: kind === "multi" ? `Region ${g}` : g,
        type: "line",
        stack: kind === "stacked" ? "mix" : undefined,
        areaStyle: kind === "stacked" ? { opacity: 0.65 } : undefined,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: kind === "stacked" ? 1 : 2 },
        itemStyle: {
          color:
            kind === "multi"
              ? colours[i % colours.length]
              : fuelColours[g] || colours[i % colours.length],
        },
        data: times.map((t) => {
          const row = rows.find(
            (r) => String(r.time) === t && String(r[category]) === g,
          );
          return row ? Number(row[value]) : null;
        }),
      })),
    };
  }
  const categories = rows.map((r) => String(r[x] ?? ""));
  return {
    ...base,
    xAxis: {
      ...(base.xAxis as object),
      data: categories,
      axisLabel: {
        fontSize: 10,
        formatter: (v: string) =>
          v.includes("T")
            ? new Date(v).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "short",
              })
            : v,
      },
    },
    series: keys.map((key, i) => ({
      name: key.replaceAll("_", " "),
      type: kind === "bar" ? "bar" : "line",
      showSymbol: false,
      connectNulls: false,
      smooth: false,
      lineStyle: {
        width: i === 0 ? 2.5 : 1.5,
        type: key.includes("rolling") ? "dashed" : "solid",
      },
      areaStyle: kind === "area" && i === 0 ? { opacity: 0.08 } : undefined,
      itemStyle: { color: colours[i] },
      data: rows.map((r) => (r[key] === null ? null : Number(r[key]))),
    })),
  };
}
