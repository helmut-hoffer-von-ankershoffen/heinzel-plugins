"""Show how a Heinzelmännchen plugin is built.

A Heinzelmännchen plugin, discovered through the `heinzel.modules` entry point in pyproject.toml. Every package
below it that declares `module = Module(...)` becomes a submodule (see `hello/`).
"""

from pathlib import Path

from heinzel import MetricWidget, Module, Navigate, NoticeKind, Notifications, StatusItem

from heinzel_example._models import ExampleAbout, ExampleSettings
from heinzel_example._service import ExampleService

module = Module("example", "Show how a Heinzelmännchen plugin is built.")
module.settings(ExampleSettings)
module.service(ExampleService)


@module.operation
def info(service: ExampleService) -> ExampleAbout:
    """Show this plugin's version, the Heinzelmännchen it runs on and the modules it brings."""
    return service.about()


@module.info
def system_info(service: ExampleService) -> ExampleAbout:
    """Contribute this plugin's details to `hz system info`."""
    return service.about()


__all__ = ["ExampleAbout", "ExampleService", "ExampleSettings", "module"]


@module.operation
def sample() -> int:
    """Read a tiny value used by every example representation."""
    return 42


@module.operation(read_only=False)
def notify(notifications: Notifications) -> str:
    """Send an example notice after the ordinary operation confirmation."""
    notice = notifications.emit(
        NoticeKind.PLUGIN, "Example is ready", route="/", command="hz example sample", key="example:ready"
    )
    return notice.title if notice else "Notifications are disabled"


@module.status(source="sample", order=700, slots={"footer": False, "sidebar": True})
def status(value: int) -> StatusItem:
    """Render checked data through the same host slots as built-in modules."""
    return StatusItem(text=f"Example: {value}", icon="star", effect=Navigate(path="/?panel=example:inspector"))


@module.widget(source="sample", order=700)
def today(value: int) -> MetricWidget:
    """Contribute a Today widget without a core change."""
    return MetricWidget(label="Example value", value=str(value))


module.action("inspect", label="Example", icon="star", effect=Navigate(path="/?panel=example:inspector"), order=700)
module.nav(title="Example", icon="star", sidebar=Navigate(path="/?panel=example:inspector"), order=700)
module.view(
    Path(__file__).parent / "views",
    abi=1,
    name="inspector",
    source="sample",
    title="Example",
    fallback="Run hz example sample to read the value.",
    order=700,
)
