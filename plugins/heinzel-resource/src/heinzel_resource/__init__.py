"""Bounded local measurements of the machine running hz, viewed by every head."""

from collections.abc import Callable
from datetime import UTC, datetime
from math import isfinite
from socket import gethostname
from threading import Lock
from time import monotonic

import psutil
from heinzel import Check, DetailLine, MetricWidget, Module, Status, StatusItem, StatusMeter, Tone
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from rich.table import Table

module = Module("resource", "Show this computer's CPU, memory and load.")

SAMPLE_SECONDS = 0.1
CACHE_SECONDS = 1.0
PERCENT_WARNING = 75
PERCENT_BAD = 90


class Resources(BaseModel):
    """A machine sample; unavailable values remain null with an explanation."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    hostname: str = Field(description="Hostname of the machine running hz.")
    sampled_at: AwareDatetime = Field(description="When the measurements were collected, in UTC.")
    cpu_percent: float | None = Field(ge=0, le=100, description="Machine CPU usage, 0 to 100 percent.")
    memory_percent: float | None = Field(ge=0, le=100, description="Machine memory usage, 0 to 100 percent.")
    load_1m: float | None = Field(ge=0, description="One-minute load average; unavailable on unsupported platforms.")
    logical_cores: int | None = Field(ge=1, description="Detected logical core count; null when unavailable.")
    problems: list[str] = Field(description="Why any measurement could not be read.")


class ResourceService:
    """One cached sampler, serialized across callers without a permanent worker."""

    def __init__(self) -> None:
        """No sampling until an operation asks for it."""
        self._lock = Lock()
        self._sample: Resources | None = None
        self._expires = 0.0

    def sample(self) -> Resources:
        """Collect at most once a second; CPU measurement waits for a 100 ms interval."""
        with self._lock:
            if self._sample is not None and monotonic() < self._expires:
                return self._sample
            problems: list[str] = []
            # A positive interval takes its own before/after readings, even on a new request thread.
            cpu = _read(lambda: psutil.cpu_percent(interval=SAMPLE_SECONDS), "CPU usage", problems, maximum=100)
            memory = _read(lambda: psutil.virtual_memory().percent, "Memory usage", problems, maximum=100)
            load = _read(lambda: psutil.getloadavg()[0], "Load average", problems)
            cores = _read(lambda: psutil.cpu_count() or 0, "Core count", problems, minimum=1)
            self._sample = Resources(
                hostname=gethostname(),
                sampled_at=datetime.now(UTC),
                cpu_percent=cpu,
                memory_percent=memory,
                load_1m=load,
                logical_cores=int(cores) if cores is not None else None,
                problems=problems,
            )
            self._expires = monotonic() + CACHE_SECONDS
            return self._sample


def _read(
    probe: Callable[[], float],
    name: str,
    problems: list[str],
    *,
    minimum: float = 0,
    maximum: float | None = None,
) -> float | None:
    """Keep one broken or unsupported native metric from hiding the remaining machine measurements."""
    try:
        value = probe()
    except (OSError, psutil.Error, NotImplementedError):
        value = None
    if value is not None and isfinite(value) and value >= minimum and (maximum is None or value <= maximum):
        return value
    problems.append(f"{name} is unavailable.")
    return None


module.service(ResourceService)


def render(sample: Resources) -> Table:
    """The same three measurements and detected capacity in a small table."""
    table = Table("Resource", "Usage")
    table.add_row("Hostname", sample.hostname)
    table.add_row("CPU", f"{sample.cpu_percent:g}%" if sample.cpu_percent is not None else "Unavailable")
    table.add_row("Memory", f"{sample.memory_percent:g}%" if sample.memory_percent is not None else "Unavailable")
    table.add_row("Load (1 min)", f"{sample.load_1m:g}" if sample.load_1m is not None else "Unavailable")
    table.add_row("Logical cores", str(sample.logical_cores) if sample.logical_cores is not None else "Unavailable")
    for problem in sample.problems:
        table.add_row("Note", problem)
    return table


@module.operation(render=render, audience="everyday")
def resource(service: ResourceService) -> Resources:
    """Show machine CPU/memory usage, one-minute load and logical cores; cache each sample for one second."""
    return service.sample()


__all__ = ["Resources", "module"]


def _tone(value: float | None) -> Tone:
    return (
        "neutral" if value is None else "bad" if value >= PERCENT_BAD else "warn" if value >= PERCENT_WARNING else "ok"
    )


def _percent(value: float | None) -> str:
    return "Unavailable" if value is None else f"{value:.0f}%"


@module.status(source="resource", name="machine", refresh="2s", order=600, slots={"footer": True, "sidebar": False})
def machine(sample: Resources) -> StatusItem:
    load_percent = (
        min(100.0, sample.load_1m / (2 * sample.logical_cores) * 100)
        if sample.load_1m is not None and sample.logical_cores
        else None
    )
    load_tone: Tone = "neutral"
    if sample.load_1m is not None and sample.logical_cores:
        load_tone = (
            "bad"
            if sample.load_1m > 2 * sample.logical_cores
            else "warn"
            if sample.load_1m > sample.logical_cores
            else "ok"
        )
    tones: list[Tone] = [_tone(sample.cpu_percent), _tone(sample.memory_percent), load_tone]
    tone: Tone = "bad" if "bad" in tones else "warn" if "warn" in tones or sample.problems else "ok"
    load = f"{sample.load_1m:.2f}" if sample.load_1m is not None else "Unavailable"
    return StatusItem(
        text="Computer resources",
        tone=tone,
        meters=[
            StatusMeter(label="CPU", value=sample.cpu_percent, tone=tones[0]),
            StatusMeter(label="Memory", value=sample.memory_percent, tone=tones[1]),
            StatusMeter(label="Load", value=load_percent, tone=tones[2]),
        ],
        detail=[
            DetailLine(text=f"Host: {sample.hostname}"[:80]),
            DetailLine(text=f"CPU: {_percent(sample.cpu_percent)}"),
            DetailLine(text=f"Memory: {_percent(sample.memory_percent)}"),
            DetailLine(text=f"Load (1 min): {load}; {sample.logical_cores or '?'} logical cores"),
            DetailLine(text="Load measures queued work; it is not a CPU percentage."),
            *[DetailLine(text=problem[:80], tone="warn") for problem in sample.problems],
        ],
    )


@module.widget(source="resource", name="machine", refresh="1m", order=600)
def overview(sample: Resources) -> MetricWidget:
    return MetricWidget(
        label="Computer resources", value=f"CPU {_percent(sample.cpu_percent)}", tone=_tone(sample.cpu_percent)
    )


@module.health
def sampling(service: ResourceService) -> list[Check]:
    sample = service.sample()
    return [
        Check(
            name="machine resources",
            status=Status.DEGRADED if sample.problems else Status.UP,
            detail=f"{sample.hostname}: " + ("; ".join(sample.problems) or "CPU, memory and load available"),
        )
    ]
