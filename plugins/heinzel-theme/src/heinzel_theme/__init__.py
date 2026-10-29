"""The standard Heinzelmännchen theme and its independently owned soundscapes."""

from pathlib import Path

from heinzel import Module

module = Module("theme", "The Heinzelmännchen theme and its soundscapes.")
module.theme(Path(__file__).parent / "themes")
module.soundscape(Path(__file__).parent / "soundscapes")
