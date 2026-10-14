export const API = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
export type Row = Record<string, string | number | boolean | null>;
export type Result = {
  rows: Row[];
  meta: {
    sources?: { id: string; stale: boolean; observed_at: string | null }[];
    count?: number;
    limit?: number;
    offset?: number;
    possibly_truncated?: boolean;
  };
};
export async function getData(
  route: string,
  params: string,
  signal?: AbortSignal,
): Promise<Result> {
  // Free hosted APIs may take around a minute to resume after inactivity.
  const timeout = AbortSignal.timeout(90000);
  const response = await fetch(`${API}/${route}?${params}`, {
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      body.detail || `Analytics unavailable (${response.status})`,
    );
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("The analytics service is starting. Please retry in a moment.");
  }
  return response.json();
}
export function number(value: unknown, digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n)
    ? n.toLocaleString("en-GB", { maximumFractionDigits: digits })
    : String(value);
}
export function stamp(value: unknown) {
  return value
    ? new Date(String(value)).toLocaleString("en-GB", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/London",
      })
    : "No observation";
}
export function nextDate(day: string) {
  return new Date(new Date(day + "T12:00:00Z").getTime() + 86400000)
    .toISOString()
    .slice(0, 10);
}
export function reportDate(value: string) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(value));
  const part = (name: string) => parts.find((p) => p.type === name)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}
export function londonMidnight(day: string) {
  const date = new Date(day + "T00:00:00Z");
  const zone = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London",
    timeZoneName: "shortOffset",
  })
    .formatToParts(date)
    .find((p) => p.type === "timeZoneName")?.value;
  return `${day}T00:00:00${zone === "GMT+1" ? "+01:00" : "Z"}`;
}
