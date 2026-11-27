"""Exercise the actual fixture record-assembly code without starting an app or vendor."""

import ast
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.utils import canonicalize_name

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[1] / "plugins"


def execute(body, env):
    # Only repository-owned record wiring runs, with public-API doubles; no imports, app or vendor starts.
    exec(compile(ast.Module(body=body, type_ignores=[]), "<fixture record assembly>", "exec"), env)  # noqa: S102


@dataclass(frozen=True)
class Origin:
    distribution: str
    version: str
    builtin: bool


def assembled(name, arguments, *, installed=True, ambiguous=False, builtin=False):
    source = ast.parse((ROOT / f"heinzel-{name}" / "docs/screenshot_fixture.py").read_text())
    origin = Origin(distribution=f"heinzel-{name}", version="1.2.3", builtin=builtin)
    initial = [SimpleNamespace(qualname=name, module=object(), origin=origin)] if installed else []
    if ambiguous:
        initial.append(
            SimpleNamespace(qualname=name + ".other", module=object(), origin=Origin(f"heinzel-{name}", "2.0.0", False))
        )
    seen = []
    configuration = SimpleNamespace(settings=lambda *_: None)

    class Kernel:
        def __init__(self, _settings, records, _errors, _configuration):
            seen.extend(records)

        def bind(self, *_args):
            pass

    def record(qualname, module, owner):
        return SimpleNamespace(qualname=qualname, module=module, origin=owner)

    env = dict(
        Config=SimpleNamespace(load=lambda: configuration),
        Settings=object(),
        discover=lambda: (list(initial), {}),
        Kernel=Kernel,
        ModuleRecord=record,
        Origin=Origin,
        canonicalize_name=canonicalize_name,
        sys=SimpleNamespace(argv=["fixture", *arguments]),
        build=lambda _: lambda: None,
        configuration=configuration,
        inbox=object(),
        showcase=object(),
        TailscaleCli=object(),
        DemoCli=lambda: object(),
    )
    if name in {"atlassian", "github"}:
        body = [next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "launch")]
        execute(body, env)
        env["launch"](env["showcase"], object(), object())
    elif name == "tailscale":
        body = next(n for n in reversed(source.body) if isinstance(n, ast.Try)).body
        execute(body, env)
    else:
        start = next(
            i
            for i, n in enumerate(source.body)
            if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Tuple)
            and any(isinstance(x, ast.Name) and x.id == "records" for x in n.targets[0].elts)
        )
        execute(source.body[start:], env)
    return seen, origin


@pytest.mark.parametrize("name", ["atlassian", "github", "tailscale", "zoom"])
def test_ui_does_not_claim_an_uninstalled_documentation_distribution(name):
    records, owner = assembled(name, ["ui"])
    assert [r.qualname for r in records] == ([name, "inbox"] if name == "zoom" else [name])
    assert all(r.origin is owner for r in records)


@pytest.mark.parametrize("name", ["atlassian", "github", "tailscale", "zoom"])
def test_cli_keeps_the_actual_documentation_requester(name):
    records, owner = assembled(name, ["showcase", "example"])
    assert records[-1].qualname == "showcase"
    assert records[0].origin is owner
    if name == "zoom":
        assert records[1].origin is owner


def test_zoom_requires_the_real_installed_owning_origin():
    with pytest.raises(ValueError, match="unambiguous"):
        assembled("zoom", ["ui"], installed=False)


@pytest.mark.parametrize("option", ["ambiguous", "builtin"])
def test_zoom_refuses_an_ambiguous_or_builtin_owner(option):
    with pytest.raises(ValueError, match="unambiguous"):
        assembled("zoom", ["ui"], **{option: True})


def test_zoom_fixture_does_not_present_its_mailbox_as_a_shipped_connector():
    import json

    plan = json.loads((ROOT / "heinzel-zoom/docs/screenshot-definition.json").read_text())
    for scene in plan["scenes"]:
        if scene["surface"] == "ui":
            assert not any(
                word in scene["route"]
                for word in ("/plugins", "/connectors", "settings=plugins", "settings=connectors")
            )
