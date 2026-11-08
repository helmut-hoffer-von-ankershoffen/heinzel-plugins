/** The weather page's view model: the plugin's `page` answer turned into what is shown, free of React. */
import { t } from "./messages";
export type Condition = "clear" | "clouds" | "rain" | "drizzle" | "thunder" | "snow" | "fog" | "wind" | "heat" | "cold";
export type Units = "metric" | "imperial";
export type Now = {
  location: string; condition: Condition; description: string; temperature: number; feels_like: number;
  high: number; low: number; rain_chance: number; humidity: number; wind_speed: number; units: Units;
  observed_at: string; sunrise: string | null; sunset: string | null;
};
export type Hour = { at: string; condition: Condition; description: string; temperature: number; rain_chance: number; rain_mm: number };
export type Day = {
  day: string; condition: Condition; description: string; high: number; low: number; rain_chance: number;
  sunrise: string | null; sunset: string | null;
};
export type Alert = { event: string; sender: string; start: string; end: string; description: string };
export type Page = {
  state: "ready" | "needs-location" | "unavailable";
  report: { now: Now; hours: Hour[]; days: Day[]; alerts: Alert[] } | null;
  message: string; provider: string; attribution: string; fetched_at: string; stale: boolean; guessed: boolean;
};
export const SETTINGS_PATH = "/?settings=weather";

/** `-0.4` must read `0°`, never `-0°`. */
export const degrees = (value: number): string => `${Math.round(value) + 0}°`;
export const percent = (chance: number): string => `${Math.round(chance * 100)}%`;
export const unitLabel = (units: Units): string => (units === "metric" ? "°C" : "°F");

/** Berlin reads km/h: the plugin gives metres per second in metric and miles per hour in imperial. */
export function wind(speed: number, units: Units): { value: number; unit: string } {
  return units === "metric" ? { value: Math.round(speed * 3.6), unit: "km/h" } : { value: Math.round(speed), unit: "mph" };
}

/** Rain in the unit the plugin used: millimetres in metric, inches in imperial. */
export function precipitation(hours: Hour[], units: Units): string {
  const total = hours.reduce((sum, hour) => sum + hour.rain_mm, 0);
  if (units === "imperial") return `${total.toFixed(2)} in`;
  return `${total < 10 ? total.toFixed(1) : Math.round(total)} mm`;
}

/** The wall-clock time at the place: ISO strings carry the place's own offset, so the browser's zone is not used. */
export const placeTime = (iso: string): string => iso.slice(11, 16);
const dateOf = (iso: string): string => iso.slice(0, 10);

/** Night when the moment is outside that day's sunrise and sunset; without them, 21:00 to 06:00. */
export function isNight(iso: string, days: Day[]): boolean {
  const day = days.find((item) => item.day === dateOf(iso));
  const time = placeTime(iso);
  if (day?.sunrise && day.sunset) return time < placeTime(day.sunrise) || time >= placeTime(day.sunset);
  return time < "06:00" || time >= "21:00";
}

/** Today, Tomorrow, then the weekday: from the day's own date, so the browser's zone cannot shift it. */
export function dayLabel(day: string, index: number, locale?: string): string {
  if (index === 0) return t("weather.today");
  if (index === 1) return t("weather.tomorrow");
  const [year, month, date] = day.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, { weekday: "long", timeZone: "UTC" }).format(new Date(Date.UTC(year, month - 1, date)));
}

/** The freshness stamp in the viewer's own clock: `09:38`. */
export function updatedAt(iso: string, locale?: string, timeZone?: string): string {
  return new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", hour12: false, timeZone }).format(new Date(iso));
}

/** Where a day's low to high sits in the week's range, for the bar: 0 to 100. */
export function span(days: Day[], day: Day): { left: number; width: number } {
  const low = Math.min(...days.map((item) => item.low));
  const range = Math.max(...days.map((item) => item.high)) - low || 1;
  return { left: ((day.low - low) / range) * 100, width: Math.max(((day.high - day.low) / range) * 100, 6) };
}

export type Tile = { key: "wind" | "humidity" | "rain" | "precipitation"; value: string };
export function tiles(report: NonNullable<Page["report"]>): Tile[] {
  const { now, hours } = report;
  const speed = wind(now.wind_speed, now.units);
  return [
    { key: "wind", value: `${speed.value} ${speed.unit}` },
    { key: "humidity", value: `${now.humidity}%` },
    { key: "rain", value: percent(now.rain_chance) },
    { key: "precipitation", value: precipitation(hours.slice(0, 24), now.units) },
  ];
}

/** "Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com/" as its words and its link. */
export function attributionParts(text: string): { text: string; url: string | null } {
  const [words, link] = text.split(", https://");
  return { text: words, url: link ? `https://${link}` : null };
}
