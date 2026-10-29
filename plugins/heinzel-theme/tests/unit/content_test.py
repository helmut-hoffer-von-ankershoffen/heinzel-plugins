import tomllib
from pathlib import Path

import pytest
from heinzel import SoundscapeLet, ThemeLet

from heinzel_theme import module

pytestmark = pytest.mark.unit


def test_theme_and_soundscapes_are_owned_public_contributions(make_kernel):
    kernel = make_kernel(theme=module)
    ((_, theme),) = kernel.lets(ThemeLet)
    assert (theme.name, theme.theme.title) == ("heinzelmaennchen", "Heinzelmännchen")
    assert theme.logos() is not None
    sounds = {let.name: let.soundscape for _, let in kernel.lets(SoundscapeLet)}
    assert {name: sound.stream.video for name, sound in sounds.items()} == {
        "claude-fm": "tRsQsTMvPNg",
        "focus": "5Le8Mrx3uA0",
        "hyper-focus": "uNw_a7HFwvg",
    }
    assert sounds["focus"].pairs_with == ("heinzelmaennchen",)
    assert all(sound.stream.provider == "youtube" for sound in sounds.values())


def test_standard_profile_membership_is_declared_only_by_the_plugin():
    metadata = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())
    assert metadata["tool"]["heinzel"]["plugin"]["profiles"] == ["standard"]
    assert metadata["project"]["dependencies"] == ["heinzel>=0.9.0,<0.10"]
