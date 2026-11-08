"""No text links in plugin chrome (owner 2026-11-08): navigation and actions are buttons, rows or PaneAction.

Mirrors the core web/src/test/links-standards.test.ts for `plugins/*/web/src/**/*.tsx`. The allowlist only shrinks.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted(
    path
    for path in ROOT.glob("plugins/*/web/src/**/*.tsx")
    if ".test." not in path.name and "node_modules" not in path.parts
)
# File (relative to the repository) -> opening link tags allowed, with the reason; entries may only be removed.
LINKS: dict[str, tuple[int, str]] = {
    "plugins/heinzel-weather/web/src/WeatherPage.tsx": (1, "CONVERT: icon-only source link becomes PaneAction href"),
}
CONTROLS = {"a", "Link", "NavLink", "button", "Button"}
LINK_LOOK = re.compile(
    r"(?<![\w-])(underline|hover:underline|underline-offset-\S+|decoration-\S+|text-primary)(?![\w-])|variant=\"link\""
)


def opening_tags(source: str):
    """Yield (name, text) for each JSX opening tag; braces nest so `=>` and `>` inside props do not end a tag."""
    for match in re.finditer(r"<([A-Za-z][\w.]*)(?=[\s/>])", source):
        depth, quote, index = 0, "", match.end()
        while index < len(source):
            char = source[index]
            if quote:
                quote = "" if char == quote and source[index - 1] != "\\" else quote
            elif char in "\"'`":
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            elif char == ">" and depth == 0 and source[index - 1] != "=":
                break
            index += 1
        yield match.group(1), source[match.start() : index + 1]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def test_links_only_where_listed():
    counts = {}
    for path in SOURCES:
        source = path.read_text()
        found = sum(
            1 for name, text in opening_tags(source) if name in {"a", "Link", "NavLink"} or 'role="link"' in text
        )
        if found:
            counts[relative(path)] = found
    for name, found in counts.items():
        assert name in LINKS and found <= LINKS[name][0], (
            f"{name}: {found} link tag(s); use a button, row or PaneAction"
        )


def test_controls_have_no_link_look():
    offenders = [
        f"{relative(path)}: {name}"
        for path in SOURCES
        for name, text in opening_tags(path.read_text())
        if name in CONTROLS and LINK_LOOK.search(text)
    ]
    assert offenders == []


def test_prose_markers_stay_out_of_plugins():
    assert [relative(path) for path in SOURCES if "data-prose-link" in path.read_text()] == []


def test_scanner_reads_multiline_tags_and_ignores_link_elements():
    source = (
        '<div>\n<Link\n  to="/x"\n  onClick={() => go()}\n  className="underline"\n>x</Link>'
        '<link rel="stylesheet" /><image href="a" /></div>'
    )
    tags = list(opening_tags(source))
    assert [name for name, _ in tags] == ["div", "Link", "link", "image"]
    assert "underline" in tags[1][1] and "go()" in tags[1][1]
    assert not any(name in {"a", "Link", "NavLink"} for name, _ in tags if name in {"link", "image"})
