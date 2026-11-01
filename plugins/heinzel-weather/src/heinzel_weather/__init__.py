"""Weather where you are, keyless from Open-Meteo (or OpenWeather with your key): now, the hours, the days, a heads-up.

`hz weather` is the weather now at your primary location, `hz weather show [LOCATION]` adds the next hours, days and
alerts, `hz weather forecast` the days. Each is a CLI command, an MCP tool and a REST endpoint. The daemon runs the
`watch` job, which records a notice when rain starts within the hour, the temperature swings or an alert is issued.
`hz weather info` names the provider and the attribution its data asks for (Open-Meteo: CC BY 4.0).

The web app gets the weather as data (ADR 0056): a footer and sidebar status item with the temperature and sky, and a
Today widget with the next days. `hz weather conditions` also says what the Heinzelmännchen wears for it (an umbrella,
sunglasses, a scarf): the `accessories` of its avatar.
"""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated

from heinzel import (
    Avatar,
    Check,
    ConfigEditor,
    Credentials,
    DetailLine,
    GraphicWidget,
    HeinzelError,
    Kernel,
    ListEntry,
    ListWidget,
    Navigate,
    NavSettings,
    Notifications,
    OpenUrl,
    Prompter,
    Status,
    StatusItem,
    WidgetAction,
)
from heinzel import __version__ as heinzel_version
from pydantic import Field, JsonValue
from rich.console import Group
from rich.table import Table
from rich.text import Text

from heinzel_weather._conditions import ui_icon, units_for_locale
from heinzel_weather._models import (
    Alert,
    Condition,
    Conditions,
    Day,
    Forecast,
    Hour,
    Info,
    Now,
    Observation,
    Provider,
    Report,
    Signals,
    UiWeather,
    Units,
    Watched,
    WeatherSettings,
)
from heinzel_weather._module import API_KEY, FALLBACK_VARIABLE, module
from heinzel_weather._service import MAX_DAYS, WeatherService

SETTINGS = Navigate(path="/?settings=weather")
"""Where a person sets the place: this plugin's section of Settings, never a command typed into a terminal."""
module.settings(WeatherSettings)
module.service(WeatherService)
module.skill(Path(__file__).parent / "skills")
module.nav(
    "weather",
    title="Weather",
    icon="cloud-sun",
    settings=NavSettings(sections=("weather",), group="preferences"),
    sidebar=SETTINGS,
)
MAX_TEXT = 80
"""The longest text of a status item or a widget title (ADR 0056)."""
Location = Annotated[
    str | None,
    Field(
        description='A place such as "Lisbon, PT" or coordinates such as "38.72,-9.14"; your primary one if left out.'
    ),
]
Days = Annotated[int, Field(ge=1, le=MAX_DAYS, description="How many days, from today.")]


def _now_line(now: Now) -> Text:
    unit = now.units.degree
    return Text(
        f"{now.icon}  {now.temperature:.0f}{unit} {now.description} in {now.location} "
        f"(feels like {now.feels_like:.0f}{unit}; today {now.low:.0f} to {now.high:.0f}{unit}, "
        f"{round(now.rain_chance * 100)}% rain)\n{now.attribution}"
    )


def _hours(hours: list[Hour], unit: str) -> Table:
    table = Table(title="Next hours", title_justify="left")
    for column in ("Time", "", "Temp", "Rain", "Sky"):
        table.add_column(column)
    for hour in hours:
        rain = f"{round(hour.rain_chance * 100)}%"
        table.add_row(  # Text, never markup: the descriptions come from OpenWeather
            Text(hour.at.strftime("%H:%M")),
            Text(hour.icon),
            Text(f"{hour.temperature:.0f}{unit}"),
            Text(rain),
            Text(hour.description),
        )
    return table


def _days(days: list[Day], unit: str) -> Table:
    table = Table(title="Days", title_justify="left")
    for column in ("Day", "", "Low", "High", "Rain", "Sky"):
        table.add_column(column)
    for day in days:
        table.add_row(
            Text(day.day.strftime("%a %d %b")),
            Text(day.icon),
            Text(f"{day.low:.0f}{unit}"),
            Text(f"{day.high:.0f}{unit}"),
            Text(f"{round(day.rain_chance * 100)}%"),
            Text(day.description),
        )
    return table


def _alerts(alerts: list[Alert]) -> list[Text]:
    return [
        Text(f"⚠ {alert.event}, {alert.start:%a %H:%M} to {alert.end:%a %H:%M} ({alert.sender})", style="bold")
        for alert in alerts
    ]


def _render_report(report: Report) -> Group:
    unit = report.now.units.degree
    return Group(_now_line(report.now), *_alerts(report.alerts), _hours(report.hours, unit), _days(report.days, unit))


def _render_forecast(forecast: Forecast) -> Group:
    return Group(Text(f"{forecast.location}"), _days(forecast.days, forecast.units.degree), Text(forecast.attribution))


def _weather_status(value: UiWeather) -> StatusItem:
    conditions = value.conditions
    now = conditions.now
    if now is None:
        return StatusItem(text="Set a location", icon="cloud", tone="warn", effect=SETTINGS)
    detail = [
        DetailLine(text=f"{now.description.capitalize()} · {now.location}"),
        DetailLine(text=f"Feels like {now.feels_like:.0f}{now.units.degree}"),
        DetailLine(
            text=f"Today {now.low:.0f} to {now.high:.0f}{now.units.degree} · {round(now.rain_chance * 100)}% rain"
        ),
    ]
    if conditions.guessed:
        detail.append(DetailLine(text="Place guessed from your time zone; set yours in Settings", tone="warn"))
    if value.stale:
        detail.append(DetailLine(text="Showing the last observation; refresh failed", tone="warn"))
    else:
        detail.append(DetailLine(text=conditions.attribution[:MAX_TEXT]))
    return StatusItem(
        text=f"{now.temperature:.0f}{now.units.degree} {now.location}{' · stale' if value.stale else ''}",
        tone="warn" if value.stale else "neutral",
        icon=ui_icon(now.condition),
        detail=detail,
        actions=[WidgetAction(label="Change place", icon="cloud", effect=SETTINGS)],
    )


def _weather_card(value: UiWeather) -> GraphicWidget | None:
    conditions = value.conditions
    now = conditions.now
    if now is None:
        return None
    stale = " · last observation" if value.stale else ""
    return GraphicWidget(
        label=f"Weather in {now.location}"[:MAX_TEXT],
        value=f"{round(now.temperature) + 0}{now.units.degree}",
        caption=f"{now.description[:24]}{stale} · {conditions.attribution.partition(', https://')[0]}",
        avatar=Avatar(accessories=conditions.accessories),
        size="medium",
    )


def _forecast_card(value: UiWeather) -> ListWidget | None:
    conditions = value.conditions
    now = conditions.now
    if now is None:
        return None
    degree = now.units.degree
    feels = f"feels like {round(now.feels_like) + 0}{degree}"
    worn = f", wearing {', '.join(conditions.accessories)}" if conditions.accessories else ""
    items = [
        ListEntry(
            text=f"{now.icon} {round(now.temperature) + 0}{degree} {now.description}",
            detail=f"{feels}{worn}",
        ),
        *(
            ListEntry(
                text=f"{day.day:%a} {day.icon} {round(day.low) + 0} to {round(day.high) + 0}{degree}",
                detail=f"{day.description}, {round(day.rain_chance * 100)}% rain",
            )
            for day in conditions.days[1:4]
        ),
    ]
    attribution_link = OpenUrl(url="https://open-meteo.com/") if conditions.provider is Provider.OPEN_METEO else None
    items.append(ListEntry(text=conditions.attribution, effect=attribution_link))
    return ListWidget(title=f"Weather in {now.location}"[:MAX_TEXT], items=items)


@module.operation(audience="everyday")
def ui(service: WeatherService) -> UiWeather:
    """Return the shared cached observation for the app's status and Today card."""
    return service.ui_weather()


@module.operation
def observe(service: WeatherService) -> Observation:
    """Read the shared 15-minute weather evidence and candidate changes without emitting notices.

    Raises:
        HeinzelError: If no prior observation exists and the provider or required credentials are unavailable.
    """
    return service.observation()


@module.status(source="ui", name="weather-now", refresh="15m", slots={"footer": True, "sidebar": True})
def current_weather(value: UiWeather) -> StatusItem:
    """Show the current condition and temperature in the footer and sidebar."""
    return _weather_status(value)


@module.widget(source="ui", name="weather-today", refresh="15m")
def today_weather(value: UiWeather) -> GraphicWidget | None:
    """Show the current temperature with the weather accessory on Today."""
    return _weather_card(value)


@module.widget(source="ui", name="forecast-today", refresh="15m")
def forecast_today(value: UiWeather) -> ListWidget | None:
    """Show the current weather and near forecast on Today."""
    return _forecast_card(value)


@module.operation(render=_now_line, audience="everyday")
def weather(service: WeatherService) -> Now:
    """Show the weather now at your primary location, with today's high, low and chance of rain.

    Raises:
        HeinzelError: If no location is set, the selected provider needs a key, or the provider fails.
    """
    return service.now()


@module.operation(render=_render_report, audience="everyday")
def show(service: WeatherService, location: Location = None) -> Report:
    """Show the weather now, the next 12 hours, the next 5 days and any severe weather alerts.

    Raises:
        HeinzelError: If no location is set, the place is unknown, the selected provider needs a key,
            or the provider fails.
    """
    return service.report(location)


@module.operation(render=_render_forecast)
def forecast(service: WeatherService, location: Location = None, days: Days = 5) -> Forecast:
    """Show the next days: high, low, chance of rain and the sky.

    Raises:
        HeinzelError: If no location is set, the place is unknown, the selected provider needs a key,
            or the provider fails.
    """
    return service.forecast(location, days)


@module.operation
def signals(service: WeatherService) -> Signals:
    """Show what a theme can follow: the weather now in one word, and today's sunrise and sunset.

    Raises:
        HeinzelError: If no location is set, the selected provider needs a key, or the provider fails.
    """
    return service.signals()


def _conditions_line(result: Conditions) -> Text:
    if result.now is None:
        return Text("No place is set: choose one in Settings > Weather.")
    worn = f" Wearing: {', '.join(result.accessories)}." if result.accessories else ""
    return Text(f"{_now_line(result.now)}{worn}")


@module.operation(render=_conditions_line, audience="expert")
def conditions(service: WeatherService) -> Conditions:
    """Show the weather now, the next days and what the Heinzelmännchen wears, or that a place is still to be set.

    Raises:
        HeinzelError: If the provider fails.
    """
    return service.conditions()


@module.operation(audience="expert")
def info(service: WeatherService) -> Info:
    """Show this plugin's version, the Heinzelmännchen it runs on, where the weather comes from and its attribution."""
    try:
        own = version("heinzel-weather")
    except PackageNotFoundError:
        own = "unknown"
    return service.info(own, heinzel_version)


@module.job(schedule="*/5 * * * *", name="watch", timeout="2m")
def watch(service: WeatherService, kernel: Kernel) -> JsonValue:
    """Check the forecast every `weather.refresh_minutes`; notice rain within the hour, a swing, a severe alert."""
    notifications = kernel.resolve(Notifications) if kernel.provides(Notifications) else None
    return service.watch(notifications).model_dump(mode="json")


@module.health
def ready(service: WeatherService, settings: WeatherSettings, credentials: Credentials) -> list[Check]:
    """A location is set, and an API key if the provider is OpenWeather; nothing is asked of the provider."""
    checks: list[Check] = []
    if settings.locations:
        detail = f"{', '.join(settings.locations)} in {service.units.value} units"
        checks.append(Check(name="locations", status=Status.UP, detail=detail))
    elif service.guessed:
        detail = f"{service.places[0]}, guessed from your time zone; set yours in Settings > Weather"
        checks.append(Check(name="locations", status=Status.UP, detail=detail))
    else:
        checks.append(Check(name="locations", status=Status.DEGRADED, detail="none set", fix="hz setup weather"))
    if not service.ready():
        checks.append(credentials.attention(API_KEY, f"no OpenWeather API key stored, nor {FALLBACK_VARIABLE} set"))
    return checks


@module.setup(required=False)
def setup(settings: WeatherSettings, prompter: Prompter, editor: ConfigEditor, credentials: Credentials) -> None:
    """Pick the places you want the weather for, the units and the provider, and an OpenWeather key if you use it."""
    default = ", ".join(settings.locations) or "Berlin, DE"
    answer = prompter.text("Places, yours first, separated by ';' (a city and country, or lat,lon)", default=default)
    places = [place.strip() for place in answer.replace(";", "\n").splitlines() if place.strip()]
    if answer == default and settings.locations:
        places = list(settings.locations)
    local = units_for_locale()
    units = prompter.choice("Units", [unit.value for unit in Units], default=(settings.units or local).value)
    provider = prompter.choice("Provider", [p.value for p in Provider], default=settings.provider.value)
    if (
        provider == Provider.OPENWEATHER
        and not credentials.has(API_KEY)
        and prompter.confirm("Store an OpenWeather API key now?")
    ):
        try:
            credentials.set(API_KEY, prompter.secret("OpenWeather API key"))
        except HeinzelError as error:
            prompter.say(str(error))
    path = editor.write("weather.locations", places)
    if settings.units is not None or units != local.value:  # unset follows the locale
        editor.write("weather.units", units)
    if provider != settings.provider.value:
        editor.write("weather.provider", provider)
    prompter.say(f"Saved to {path}.")


__all__ = [
    "Alert",
    "Condition",
    "Conditions",
    "Day",
    "Forecast",
    "Hour",
    "Info",
    "Now",
    "Observation",
    "Provider",
    "Report",
    "Signals",
    "Units",
    "Watched",
    "WeatherService",
    "WeatherSettings",
    "module",
]
