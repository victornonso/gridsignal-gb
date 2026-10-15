import { test } from "node:test";
import assert from "node:assert/strict";
import { heatmapData, heatmapTooltip } from "../src/lib/heatmap.ts";
import {
  reportDate,
  londonMidnight,
  nextDate,
  number,
  getData,
  stamp,
  tableValue,
} from "../src/lib/api.ts";

test("British reporting date is independent of device/server timezone", () => {
  assert.equal(reportDate("2026-10-06T23:00:00Z"), "2026-10-07");
  assert.equal(reportDate("2026-12-01T00:00:00Z"), "2026-12-01");
});
test("British date filters span 23 and 25 hours on DST transition days", () => {
  const hours = (day) =>
    (new Date(londonMidnight(nextDate(day))) - new Date(londonMidnight(day))) /
    3600000;
  assert.equal(hours("2026-03-29"), 23);
  assert.equal(hours("2026-10-25"), 25);
});
test("Missing values are distinct from genuine zero observations", () => {
  assert.equal(number(null), "—");
  assert.equal(number(0), "0.00");
});

test("Heatmap cells retain distinct hours and true zeros while leaving missing readings empty", () => {
  const { days, hours, data } = heatmapData([
    { day: "2026-10-07", hour: 9, value: "207.5" },
    { day: "2026-10-07", hour: 10, value: "214" },
    { day: "2026-10-07", hour: 11, value: null },
    { day: "2026-10-07", hour: 12, value: 0 },
  ]);
  assert.equal(hours.length, 24);
  assert.deepEqual(data, [[9, 0, 207.5], [10, 0, 214], [12, 0, 0]]);
  const tooltip = heatmapTooltip({ value: data[0] }, days);
  assert.match(tooltip, /07 Oct 2026/);
  assert.match(tooltip, /09:00–10:00/);
  assert.match(tooltip, /207\.50 gCO₂\/kWh/);
  assert.doesNotMatch(tooltip, /series/i);
  assert.match(heatmapTooltip({ value: data[1] }, days), /214\.00/);
  assert.match(heatmapTooltip({ value: data[2] }, days), /0\.00/);
});

test("Hosted startup pages produce a useful retry message", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response("<html>Starting</html>", {
    headers: { "content-type": "text/html" },
  }));
  await assert.rejects(getData("overview", ""), /service is starting/);
});

test("Analytics requests preserve cancellation while allowing valid JSON", async (t) => {
  const controller = new AbortController();
  t.mock.method(globalThis, "fetch", async (_url, options) => {
    controller.abort();
    assert.equal(options.signal.aborted, true);
    return Response.json({ rows: [], meta: {} });
  });
  assert.deepEqual(await getData("overview", "", controller.signal), { rows: [], meta: {} });
});

test("Readable timestamps include year, seconds and the British DST zone", () => {
  assert.match(stamp("2026-10-14T13:53:46.863728Z"), /14 Oct 2026, 14:53:46 BST/);
  assert.match(stamp("2026-12-01T13:00:00Z"), /01 Dec 2026, 13:00:00 GMT/);
  assert.equal(stamp("bad-date"), "Unavailable");
  assert.equal(tableValue("finished_at", null), "\u2014");
});
test("PostgreSQL decimals are rounded; counts remain whole", () => {
  assert.equal(tableValue("age_minutes", "447.0249951166666667"), "447.02");
  assert.equal(tableValue("value", 68), "68.00");
  assert.equal(tableValue("row_count", 17280), "17,280");
  assert.equal(tableValue("source", "demand"), "demand");
  assert.match(tableValue("next_scheduled_at", "2026-10-14T18:23:00Z"), /19:23:00 BST/);
});
