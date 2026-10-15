type Cell = { day: unknown; hour: unknown; value: unknown };

export function heatmapData(rows: Cell[]) {
  const days = [...new Set(rows.map(row => String(row.day)))].sort();
  const hours = Array.from({ length: 24 }, (_, hour) => String(hour));
  const data = rows.flatMap(row => {
    const hour = Number(row.hour);
    if (row.value === null || row.value === undefined || row.value === "" ||
        !Number.isInteger(hour) || hour < 0 || hour > 23) return [];
    const value = Number(row.value);
    return Number.isFinite(value) ? [[hour, days.indexOf(String(row.day)), value]] : [];
  });
  return { days, hours, data };
}

export function heatmapDay(day: string, compact = false) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return "Unavailable date";
  const date = new Date(day + "T12:00:00Z");
  if (!Number.isFinite(date.getTime())) return "Unavailable date";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit", month: "short", ...(compact ? {} : { year: "numeric" }),
    timeZone: "UTC",
  }).format(date);
}

export function heatmapTooltip(input: unknown, days: string[]) {
  const value = (input as { value?: unknown })?.value;
  if (!Array.isArray(value) || value.length < 3 || value[2] === null) return "No observation";
  const [hour, day, intensity] = value.map(Number);
  if (!Number.isInteger(hour) || hour < 0 || hour > 23 || !days[day] || !Number.isFinite(intensity)) return "No observation";
  const clock = (h: number) => `${String(h).padStart(2, "0")}:00`;
  return `${heatmapDay(days[day])}<br/>${clock(hour)}–${clock(hour + 1)} · British local time<br/>Hourly mean: ${intensity.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} gCO₂/kWh`;
}
