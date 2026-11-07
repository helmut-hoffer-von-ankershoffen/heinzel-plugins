import { describe, expect, it } from "vitest";
import { days, hours, ready } from "./fixture";
import { dayLabel, degrees, isNight, percent, placeTime, precipitation, span, tiles, unitLabel, updatedAt, wind } from "./model";

describe("formatting", () => {
  it("rounds temperatures and never shows a negative zero", () => {
    expect(degrees(2.4)).toBe("2°");
    expect(degrees(-0.4)).toBe("0°");
    expect(degrees(-1.6)).toBe("-2°");
  });
  it("reads km/h in metric and mph in imperial", () => {
    expect(wind(3.2, "metric")).toEqual({ value: 12, unit: "km/h" });
    expect(wind(7.4, "imperial")).toEqual({ value: 7, unit: "mph" });
    expect(unitLabel("metric")).toBe("°C");
    expect(unitLabel("imperial")).toBe("°F");
  });
  it("formats chances and rain in the plugin's unit", () => {
    expect(percent(0.704)).toBe("70%");
    expect(precipitation(hours, "metric")).toBe("1.6 mm");
    expect(precipitation(hours, "imperial")).toBe("1.60 in");
  });
});

describe("time at the place", () => {
  it("takes the clock from the ISO string, not the browser zone", () => {
    expect(placeTime("2026-11-07T14:00:00+01:00")).toBe("14:00");
  });
  it("is night before sunrise and from sunset, by that day's sun", () => {
    expect(isNight("2026-11-07T06:00:00+01:00", days)).toBe(true);
    expect(isNight("2026-11-07T12:00:00+01:00", days)).toBe(false);
    expect(isNight("2026-11-07T17:00:00+01:00", days)).toBe(true);
    expect(isNight("2026-12-30T12:00:00+01:00", [])).toBe(false);
    expect(isNight("2026-12-30T23:00:00+01:00", [])).toBe(true);
  });
  it("names today and tomorrow, then the weekday of the date itself", () => {
    expect(dayLabel("2026-11-07", 0, "en")).toBe("Today");
    expect(dayLabel("2026-11-08", 1, "en")).toBe("Tomorrow");
    expect(dayLabel("2026-11-09", 2, "en")).toBe("Monday");
  });
  it("stamps freshness in the viewer's clock", () => {
    expect(updatedAt("2026-11-07T08:38:00+00:00", "en-GB", "Europe/Berlin")).toBe("09:38");
  });
});

describe("layout numbers", () => {
  it("places each day's range within the week's", () => {
    const first = span(days, days[0]);
    expect(first.left).toBe(0);
    expect(span(days, days[6]).left + span(days, days[6]).width).toBeCloseTo(100);
  });
  it("lists wind, humidity, rain chance and rain", () => {
    expect(tiles(ready.report!).map((tile) => [tile.key, tile.value])).toEqual([
      ["wind", "12 km/h"], ["humidity", "87%"], ["rain", "30%"], ["precipitation", "1.6 mm"],
    ]);
  });
});
