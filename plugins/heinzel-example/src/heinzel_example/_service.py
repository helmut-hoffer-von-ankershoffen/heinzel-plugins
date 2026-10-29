"""The plugin's logic, independent of any head."""

from importlib.metadata import PackageNotFoundError, version

from heinzel import Kernel, __version__

from heinzel_example._models import ExampleAbout, ExampleGreeting, ExampleSettings

DISTRIBUTION = "heinzel-example"


class ExampleService:
    """Everything the example modules do; operations stay thin and call into it."""

    def __init__(self, kernel: Kernel, settings: ExampleSettings) -> None:
        """Create the service; the kernel and the plugin's settings are injected."""
        self._kernel = kernel
        self._settings = settings

    def about(self) -> ExampleAbout:
        """Describe the plugin and the Heinzelmännchen installation it runs in."""
        try:
            installed = version(DISTRIBUTION)
        except PackageNotFoundError:  # pragma: no cover - only when running from an uninstalled source tree
            installed = "0.0.0"
        return ExampleAbout(
            plugin=DISTRIBUTION,
            version=installed,
            heinzel_version=__version__,
            modules=[r.qualname for r in self._kernel.modules if r.origin.distribution == DISTRIBUTION],
        )

    def greet(self, name: str) -> ExampleGreeting:
        """Greet someone by name, the way the settings say."""
        return ExampleGreeting(text=f"{self._settings.greeting}, {name}!")
