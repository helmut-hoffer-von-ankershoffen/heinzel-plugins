import type { Day, Hour, Page } from "./model";

/** A fictional Berlin forecast: an overcast day with rain coming. */
const clock = (hour: number) => `2026-11-07T${String(hour % 24).padStart(2, "0")}:00:00+01:00`;
export const hours: Hour[] = Array.from({ length: 24 }, (_, index) => ({
  at: `2026-11-${index + 9 < 24 ? "07" : "08"}T${String((index + 9) % 24).padStart(2, "0")}:00:00+01:00`,
  condition: index > 5 && index < 10 ? "rain" : index > 14 ? "clear" : "clouds",
  description: "overcast", temperature: 2.4 - index * 0.2, rain_chance: index > 5 && index < 10 ? 0.7 : 0.02, rain_mm: index > 5 && index < 10 ? 0.4 : 0,
}));
export const days: Day[] = Array.from({ length: 7 }, (_, index) => ({
  day: `2026-11-${String(7 + index).padStart(2, "0")}`,
  condition: index === 1 ? "rain" : "clouds", description: index === 1 ? "rain" : "overcast",
  high: 4 + index, low: -1 + index, rain_chance: index === 1 ? 0.8 : 0.05,
  sunrise: `2026-11-${String(7 + index).padStart(2, "0")}T07:12:00+01:00`, sunset: `2026-11-${String(7 + index).padStart(2, "0")}T16:31:00+01:00`,
}));
export const ready: Page = {
  state: "ready", message: "", provider: "open-meteo", fetched_at: "2026-11-07T08:38:00+00:00", stale: false, guessed: false,
  attribution: "Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com/",
  report: {
    now: {
      location: "Berlin, DE", condition: "clouds", description: "overcast", temperature: 2.4, feels_like: -0.4, high: 4, low: -1,
      rain_chance: 0.3, humidity: 87, wind_speed: 3.2, units: "metric", observed_at: clock(9), sunrise: days[0].sunrise, sunset: days[0].sunset,
    },
    hours, days, alerts: [],
  },
};
export const needsLocation: Page = { ...ready, state: "needs-location", report: null };
export const unavailable: Page = { ...ready, state: "unavailable", report: null, message: "Open-Meteo can't be reached." };
