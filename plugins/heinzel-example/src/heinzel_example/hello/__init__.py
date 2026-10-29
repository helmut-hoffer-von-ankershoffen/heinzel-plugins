"""A submodule. Its only operation shares its name, so the CLI collapses it to `hz example hello`."""

from typing import Annotated

from heinzel import Module
from pydantic import Field

from heinzel_example._models import ExampleGreeting
from heinzel_example._service import ExampleService

module = Module("hello", "Greet someone.")


@module.operation
def hello(
    service: ExampleService,
    name: Annotated[str, Field(description="Who to greet.")] = "world",
) -> ExampleGreeting:
    """Greet someone by name."""
    return service.greet(name)
