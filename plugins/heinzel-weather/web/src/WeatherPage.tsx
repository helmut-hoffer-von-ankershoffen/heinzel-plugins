import { CloudOff, CloudSun, Droplets, ExternalLink, Info, MapPin, TriangleAlert, Umbrella, Wind, X } from "lucide-react";
import { useState } from "react";
import { ConditionIcon } from "./ConditionIcon";
import { t } from "./messages";
import { Button, SettingsShortcut } from "./sdk";
import type { ViewProps } from "./sdk";
import { SETTINGS_PATH, attributionParts, dayLabel, degrees, isNight, percent, placeTime, span, tiles, unitLabel, updatedAt } from "./model";
import type { Day, Hour, Page } from "./model";

type Report = NonNullable<Page["report"]>;
const TILE_ICONS = { wind: Wind, humidity: Droplets, rain: Umbrella, precipitation: Droplets } as const;
const LABEL = { wind: "weather.wind", humidity: "weather.humidity", rain: "weather.rainChance", precipitation: "weather.precipitation" } as const;

/** Opens Settings > Weather through the app's own router: the same URL the sidebar's Settings uses. */
function openSettings() {
  window.history.pushState({}, "", SETTINGS_PATH);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function WeatherPage({ data, loading, onClose, flowing = false }: ViewProps) {
  const page = data as Page | undefined;
  const report = page?.state === "ready" ? page.report : null;
  const place = report?.now.location;
  return (
    <section className={flowing ? "wx" : "wx wx-fill"} aria-label={t("weather.title")}>
      <header className="wx-head">
        <CloudSun aria-hidden size={16} color="var(--color-primary)" />
        <h2>
          {place ? (<><span className="wx-sr">{t("weather.in")} </span>{place}</>) : t("weather.title")}
        </h2>
        {report && <Attribution text={page?.attribution ?? ""} />}
        {report && <SettingsShortcut section="weather" label={t("weather.changeLocation")} />}
        <Button variant="ghost" size="icon" aria-label={t("weather.close")} onClick={onClose}>
          <X aria-hidden />
        </Button>
      </header>
      <div className={flowing ? "wx-body" : "wx-body wx-scroll"}>
        <div className="wx-stack">
          {!page ? (
            <p role="status" className="wx-note">{loading ? t("weather.loading") : t("weather.unavailable.body")}</p>
          ) : page.state === "needs-location" ? (
            <Notice icon={MapPin} title={t("weather.setup.title")} body={t("weather.setup.body")} action={t("weather.setup.action")} />
          ) : !report ? (
            <Notice icon={CloudOff} title={t("weather.unavailable.title")} body={page.message || t("weather.unavailable.body")} action={t("weather.unavailable.action")} />
          ) : (
            <Forecast page={page} report={report} />
          )}
        </div>
      </div>
    </section>
  );
}

/** The data's licence asks for credit once: an info button that shows it on tap, hover and focus, with the link. */
function Attribution({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const { text: words, url } = attributionParts(text);
  return (
    <span className="wx-source" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
      <Button variant="ghost" size="icon" aria-label={t("weather.source")} aria-expanded={open} title={words} onClick={() => setOpen(true)} onFocus={() => setOpen(true)} onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}>
        <Info aria-hidden />
      </Button>
      {open && (
        <span role="status" className="wx-pop">
          {words}
          {url && (
            <a href={url} target="_blank" rel="noopener noreferrer" aria-label={t("weather.sourceLink")} title={t("weather.sourceLink")}>
              <ExternalLink aria-hidden />
            </a>
          )}
        </span>
      )}
    </span>
  );
}

function Notice({ icon: Icon, title, body, action }: { icon: typeof MapPin; title: string; body: string; action: string }) {
  return (
    <div className="wx-card wx-notice">
      <Icon aria-hidden />
      <h3>{title}</h3>
      <p>{body}</p>
      <Button onClick={openSettings}>{action}</Button>
    </div>
  );
}

function Forecast({ page, report }: { page: Page; report: Report }) {
  const { now, hours, days, alerts } = report;
  const degree = unitLabel(now.units);
  const stamp = updatedAt(page.fetched_at);
  const night = isNight(now.observed_at, days);
  return (
    <>
      {page.stale && (
        <p role="status" className="wx-banner">
          <TriangleAlert aria-hidden />
          {t("weather.stale", { at: stamp })}
        </p>
      )}
      {page.guessed && <p className="wx-note">{t("weather.guessed")}</p>}
      {alerts.length > 0 && (
        <ul aria-label={t("weather.alerts")} className="wx-alerts">
          {alerts.map((alert) => (
            <li key={`${alert.event}${alert.start}`} className="wx-banner wx-alert">
              <TriangleAlert aria-hidden />
              <span><strong>{alert.event}</strong> · {t("weather.alertUntil", { at: placeTime(alert.end) })} · {alert.sender}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="wx-card wx-hero">
        <div className="wx-now">
          <ConditionIcon condition={now.condition} night={night} />
          <div className="min-w-0">
            <p className="wx-temp">
              {degrees(now.temperature)}<span className="wx-sr">{degree}</span>
            </p>
            <p className="wx-sky">{now.description}</p>
            <p className="wx-sub">
              {t("weather.feelsLike", { value: degrees(now.feels_like) })} · {t("weather.highLow", { high: degrees(now.high), low: degrees(now.low) })}
            </p>
          </div>
        </div>
        <dl className="wx-tiles">
          {tiles(report).map((tile) => {
            const Icon = TILE_ICONS[tile.key];
            return (
              <div key={tile.key}>
                <dt><Icon aria-hidden />{t(LABEL[tile.key])}</dt>
                <dd>{tile.value}</dd>
              </div>
            );
          })}
        </dl>
      </div>
      <section aria-labelledby="weather-hourly">
        <h3 id="weather-hourly">{t("weather.hourly")}</h3>
        <ol className="wx-hours">
          {hours.slice(0, 24).map((hour, index) => <HourCell key={hour.at} hour={hour} days={days} first={index === 0} />)}
        </ol>
      </section>
      <section aria-labelledby="weather-daily">
        <h3 id="weather-daily">{t("weather.daily")}</h3>
        <ul className="wx-card wx-days">
          {days.slice(0, 7).map((day, index) => <DayRow key={day.day} day={day} days={days} index={index} />)}
        </ul>
      </section>
      <p className="wx-meta">
        <time dateTime={page.fetched_at}>{t("weather.updated", { at: stamp })}</time>
      </p>
    </>
  );
}

function HourCell({ hour, days, first }: { hour: Hour; days: Day[]; first: boolean }) {
  const rainy = hour.rain_chance >= 0.1;
  return (
    <li className="wx-card wx-hour">
      <time dateTime={hour.at}>{first ? t("weather.now") : placeTime(hour.at)}</time>
      <ConditionIcon condition={hour.condition} night={isNight(hour.at, days)} />
      <strong title={hour.description}>{degrees(hour.temperature)}</strong>
      <span className={rainy ? "wx-chance wet" : "wx-chance"}>
        <span aria-hidden>{rainy ? percent(hour.rain_chance) : "–"}</span>
        <span className="wx-sr">{t("weather.rain", { value: percent(hour.rain_chance) })}</span>
      </span>
    </li>
  );
}

function DayRow({ day, days, index }: { day: Day; days: Day[]; index: number }) {
  const bar = span(days, day);
  return (
    <li className="wx-day">
      <span className="wx-day-name">{dayLabel(day.day, index)}<span className="wx-sr">, {day.description}</span></span>
      <ConditionIcon condition={day.condition} />
      <span className="wx-chance">
        <span aria-hidden>{day.rain_chance >= 0.1 ? percent(day.rain_chance) : ""}</span>
        <span className="wx-sr">{t("weather.rain", { value: percent(day.rain_chance) })}</span>
      </span>
      <span className="wx-day-low">{degrees(day.low)}</span>
      <span aria-hidden className="wx-range"><i style={{ left: `${bar.left}%`, width: `${bar.width}%` }} /></span>
      <span className="wx-day-high">{degrees(day.high)}</span>
    </li>
  );
}
