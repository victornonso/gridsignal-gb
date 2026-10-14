import { test } from "node:test";
import assert from "node:assert/strict";
import {
  reportDate,
  londonMidnight,
  nextDate,
  number,
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
  assert.equal(number(0), "0");
});
