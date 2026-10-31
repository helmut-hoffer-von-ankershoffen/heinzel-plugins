"""The module declaration, apart from `__init__.py` so the plugin's other files can import it."""

from heinzel import Module

module = Module("slack", "Tell the owner what needs them, and ask for approval of an exact draft, in their Slack DM.")
