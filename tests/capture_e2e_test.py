"""Capture a new unknown plugin against an installed SDK; production review gates remain intact."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from heinzel_plugin_tools import capture, planning, privacy

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("HZ_CAPTURE_E2E") != "1", reason="Opt-in installed-SDK browser journey; CI runs this explicitly"
    ),
]


def test_capture_review_freshness_and_recovery_for_a_new_plugin(tmp_path):
    owner = tmp_path / "heinzel-harbor"
    package = owner / "src/heinzel_harbor"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        'from heinzel import MetricWidget, Module\nmodule=Module("harbor", "A fictional harbor.")\n'
        "@module.operation\ndef hello() -> str:\n"
        '    """Greet someone in the fictional harbor."""\n    return "Hello, Mira!"\n'
        '@module.widget(source="hello")\ndef greeting(value: str) -> MetricWidget:\n'
        '    """Show the fictional harbor greeting."""\n'
        '    return MetricWidget(label="Harbor greeting", value=value)\n'
    )
    (owner / "pyproject.toml").write_text(
        '[project]\nname="heinzel-harbor"\nversion="0.1.0"\ndescription="A fictional harbor."\n'
        'dependencies=["heinzel>=0.9.8,<0.10"]\n'
        '[project.entry-points."heinzel.modules"]\nharbor="heinzel_harbor"\n'
        '[build-system]\nrequires=["hatchling>=1.29.0"]\nbuild-backend="hatchling.build"\n'
        '[dependency-groups]\ntest=["editables>=0.5","hatchling>=1.29.0"]\n'
    )
    (owner / "README.md").write_text("# Harbor\nA fictional useful greeting in Today and the CLI.\n")
    plan_path = owner / capture.PLAN
    plan_path.parent.mkdir()
    plan_path.write_text("""format = 1
browser_time = "2026-11-02T10:00:00+01:00"

[[scenes]]
name = "today"
surface = "ui"
route = "/"
caption = "Harbor greeting in Today, fictional demonstration"
steps = [{action="wait", text="Hello, Mira!"}]

[[scenes]]
name = "terminal"
surface = "ui"
route = "/"
caption = "The same fictional greeting in the app terminal"
steps = [{action="terminal", command=["harbor", "hello"]}]

[[scenes]]
name = "cli"
surface = "cli"
command = ["harbor", "hello"]
caption = "hz harbor hello, fictional demonstration"
""")

    def define():
        planning.record_definition(
            owner,
            capture.read_plan(owner),
            "# Synthetic CI story\nTest the real greeting in Today, the app terminal and the CLI with fictional Mira.",
            reviewer="Synthetic CI source-analysis fixture",
        )

    def command(*arguments):
        return subprocess.run(  # noqa: S603 - explicit synthetic owning commands, no shell
            [sys.executable, "-m", "heinzel_plugin_tools", *arguments],
            cwd=owner,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    def approve_synthetic_fixture():
        # CI knows every byte of this synthetic fixture; this is explicit test data, never a production bypass flag.
        folder = owner / privacy.DRAFT
        bundle = json.loads((folder / "review-input.json").read_text())
        privacy.validate_bundle(bundle, folder)
        receipt = {
            "format": 1,
            "bundle_sha256": bundle["bundle_sha256"],
            "reviewer": "Synthetic CI independent-review fixture",
            "decision": "approve",
            "checked_images": sorted(bundle["images"]),
            "checks": dict.fromkeys(privacy.CHECKS, True),
            "findings": [],
        }
        path = folder / "synthetic-review.json"
        path.write_text(json.dumps(receipt))
        published = command("screenshots", "--review-receipt", str(path), "--json")
        assert published.returncode == 0, published.stderr + published.stdout
        return json.loads(published.stdout)

    locked = command("lock")
    assert locked.returncode == 0, locked.stderr
    define()
    result = command("screenshots", "--draft", "--json")
    assert result.returncode == 0, result.stderr + result.stdout
    draft = json.loads(result.stdout)
    assert draft["review_required"]
    assert not (owner / capture.OUTPUT).exists()
    report = approve_synthetic_fixture()
    assert report["ok"] and report["fresh"] and report["privacy_reviewed"]
    assert len(report["screenshots"]) == 3
    assert Path(report["preview"]).is_file()
    assert (owner / "README.md").read_text().count("<img ") == 3
    images = {s["path"]: (owner / s["path"]).read_bytes() for s in report["screenshots"]}
    check = command("screenshots", "--check", "--json")
    assert check.returncode == 0 and json.loads(check.stdout)["fresh"]
    approved_files = [path for path in (owner / capture.OUTPUT).iterdir() if path.suffix != ".png"]
    approved_files += [owner / "README.md", owner / planning.DEFINITION, owner / planning.STORY, plan_path]
    approved_bytes = {path: path.read_bytes() for path in approved_files}
    for hook in ("end-of-file-fixer", "trailing-whitespace-fixer"):
        normalized = subprocess.run(  # noqa: S603 - exact pinned commit hooks, synthetic owning files
            [
                shutil.which("uv"),
                "run",
                "--no-project",
                "--with",
                "pre-commit-hooks==6.0.0",
                hook,
                *[str(path) for path in approved_files],
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert normalized.returncode == 0, "Generated review bytes must already satisfy commit whitespace hooks"
    assert all(path.read_bytes() == data for path, data in approved_bytes.items())
    assert command("screenshots-check", "--json").returncode == 0
    source = package / "__init__.py"
    source.write_text(source.read_text() + "# Interface change requires a new definition and capture.\n")
    stale = command("screenshots-check", "--json")
    assert stale.returncode == 1 and "stale" in json.loads(stale.stdout)["error"]
    original_plan = plan_path.read_text()
    plan_path.write_text(
        original_plan.replace(
            'steps = [{action="wait", text="Hello, Mira!"}]',
            'timeout_ms = 1000\nsteps = [{action="click", role="button", name="A missing fixture button"}]',
        )
    )
    define()
    failed = command("screenshots", "--draft", "--json")
    assert failed.returncode == 1
    error = json.loads(failed.stdout)
    assert not error["ok"] and "Scene today failed" in error["error"]
    assert "#token=" not in error["error"]
    assert (owner / ".preview/screenshots/today-failure.png").is_file()
    assert all((owner / path).read_bytes() == content for path, content in images.items())
    plan_path.write_text(original_plan)
    define()
    recovered = command("screenshots", "--draft", "--json")
    assert recovered.returncode == 0, recovered.stderr + recovered.stdout
    assert approve_synthetic_fixture()["fresh"]


def test_auth_presentation_is_redacted_before_success_and_failure_images(tmp_path):
    from playwright.sync_api import sync_playwright

    token = "fictional-capture-session-123456"  # noqa: S105 - deliberately fake authentication presentation
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            for name in ("success", "failure"):
                page.set_content(
                    f"<p>Share: http://127.0.0.1:1234/#token={token}</p>"
                    f'<input aria-label="Authentication link" value="http://127.0.0.1:1234/#token={token}">'
                    "<p>/var/folders/fictional-machine/T/hz-demo/state/contract.prose.md</p>"
                    "<p>CPU 36%; Memory 62%; Load 0.65</p>"
                )
                body = capture.safe_screenshot(
                    page,
                    tmp_path / f"{name}.png",
                    tokens=(token,),
                    private_paths=("/var/folders/fictional-machine/T/hz-demo",),
                )
                assert token not in body
                assert token not in page.locator("input").input_value()
                assert "#token=" not in body
                assert "hidden] hidden]" not in body
                assert "/var/folders/" not in body
                assert "/demo-profile/state/contract.prose.md" in body
                assert "CPU 36%" in body
                assert (tmp_path / f"{name}.png").is_file()
            page.set_content("<p>/Users/private-person/secret-state</p>")
            with pytest.raises(ValueError, match="private paths"):
                capture.safe_screenshot(page, tmp_path / "unsafe.png")
            assert not (tmp_path / "unsafe.png").exists()
        finally:
            browser.close()
