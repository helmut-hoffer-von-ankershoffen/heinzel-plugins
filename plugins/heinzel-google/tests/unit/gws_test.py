"""The session over `gws`: arguments, parsing, retries, paging, bounds, and messages that never carry a secret."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from heinzel import HeinzelError

from heinzel_google import GoogleSession, GoogleSettings, Process, _gws
from heinzel_google._gws import (
    CALENDAR_WRITE_SCOPE,
    LOGIN,
    MAIL_SCOPE,
    MAIL_WRITE_SCOPE,
    MAX_SAID,
    SCOPES,
    login_command,
    redact,
)

pytestmark = pytest.mark.unit

FILES = ("drive", "files", "get")
LIST = ("drive", "files", "list")
TOKEN = "ya29.a0AfH6SMBfakeaccesstokenneverShown"


def output(body: object, exit_code: int = 0, stderr: bytes = b"") -> Process:
    return Process(exit_code, json.dumps(body).encode(), stderr)


def get(session: GoogleSession) -> dict[str, object]:
    return session.get("Google Drive", FILES, {"fileId": "x"}, "file x")[0]


def failure(session: GoogleSession) -> str:
    with pytest.raises(HeinzelError) as caught:
        get(session)
    text = str(caught.value)
    assert TOKEN not in text
    return text


def test_a_get_runs_gws_with_an_argument_list(session, fake_gws, gws_path):
    fake_gws.json(FILES, {"id": "x"})
    assert session.get("Google Drive", FILES, {"fileId": "x", "supportsAllDrives": True}, "file x") == (
        {"id": "x"},
        len(json.dumps({"id": "x"})),
    )
    version, run = fake_gws.runs
    assert version.arguments == ["--version"]
    assert run.executable == gws_path
    assert run.arguments == [
        "drive",
        "files",
        "get",
        "--params",
        '{"fileId":"x","supportsAllDrives":true}',
        "--format",
        "json",
    ]
    assert run.timeout == GoogleSettings().timeout


def test_a_hostile_parameter_stays_one_argument(session, fake_gws):
    fake_gws.json(FILES, {})
    session.get("Google Drive", FILES, {"fileId": "x; rm -rf / --format table"}, "file x")
    assert fake_gws.api_runs[0].params == {"fileId": "x; rm -rf / --format table"}
    assert len(fake_gws.api_runs[0].arguments) == 7


def test_gws_is_found_on_path(fake_gws, gws_path, monkeypatch):
    directory = str(Path(gws_path).parent)
    monkeypatch.setenv("PATH", os.pathsep.join(["bin", ".", directory]))
    assert GoogleSession(GoogleSettings(), fake_gws).executable() == gws_path


def test_relative_path_entries_are_never_searched(fake_gws, tmp_path, monkeypatch):
    planted = tmp_path / "bin" / "gws"
    planted.parent.mkdir()
    planted.write_text("#!/bin/sh\n", encoding="utf-8")
    planted.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", os.pathsep.join(["bin", "."]))
    with pytest.raises(HeinzelError, match="looked on PATH"):
        GoogleSession(GoogleSettings(), fake_gws).executable()


def test_without_gws_nothing_runs(fake_gws, tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(HeinzelError, match=r"looked on PATH.*Install it: npm install -g @googleworkspace/cli"):
        GoogleSession(GoogleSettings(), fake_gws).executable()
    plain = tmp_path / "gws"
    plain.write_text("", encoding="utf-8")  # a file, but not executable
    with pytest.raises(HeinzelError, match=r"looked at .*gws, the path in google\.gws_path"):
        GoogleSession(GoogleSettings(gws_path=str(plain)), fake_gws).executable()
    assert fake_gws.runs == []


def test_gws_path_must_be_absolute():
    with pytest.raises(ValueError, match="absolute path"):
        GoogleSettings(gws_path="bin/gws")
    assert GoogleSettings(gws_path="  ").gws_path is None


def test_a_gws_that_cannot_start(session, fake_gws):
    fake_gws.error = PermissionError("denied")
    assert "Could not start gws: PermissionError" in failure(session)


def test_a_timeout(session, fake_gws):
    fake_gws.on(FILES, Process(None, b""))
    assert "did not answer file x within 60 seconds" in failure(session)


def test_too_much_output(session, fake_gws):
    fake_gws.on(FILES, Process(0, b"{", truncated=True))
    assert "larger than 10,000,000 bytes" in failure(session)


@pytest.mark.parametrize("stdout", [b"<html>", b"[1]"], ids=["not json", "a list"])
def test_success_without_a_json_object(session, fake_gws, stdout):
    fake_gws.on(FILES, Process(0, stdout))
    assert "something other than a JSON object" in failure(session)


def test_rate_limits_are_retried_with_backoff(session, fake_gws):
    limited = output({"error": {"code": 403, "errors": [{"reason": "userRateLimitExceeded"}]}}, 1)
    fake_gws.on(FILES, output({"error": {"code": 429}}, 1), limited, output({"id": "x"}))
    assert get(session) == {"id": "x"}
    assert fake_gws.slept == [1.0, 2.0]


def test_rate_limits_past_the_retries_say_when_to_retry(session, fake_gws):
    fake_gws.on(FILES, output({"error": {"code": 403, "details": [{"reason": "RATE_LIMIT_EXCEEDED"}]}}, 1))
    assert "rate limit is reached for file x after 3 retries: retry in a minute" in failure(session)
    assert fake_gws.slept == [1.0, 2.0, 4.0]


@pytest.mark.parametrize(
    ("process", "expected"),
    [
        (output({"error": {"code": 401, "message": "Access denied.", "reason": "authError"}}, 2), "not signed in"),
        (output({"error": {"code": 401, "message": "expired"}}, 1), "not signed in"),
        (
            output({"error": {"code": 403, "errors": [{"reason": "insufficientPermissions"}]}}, 1),
            "doesn't give Heinzel permission to read it",
        ),
        (output({"error": {"code": 403, "details": [{"reason": "SERVICE_DISABLED"}]}}, 1), "is not enabled"),
        (output({"error": {"code": 404}}, 1), "has no file x, or the signed-in account can't see it"),
        (output({"error": {"code": 403, "message": "no"}}, 1), "may lack access"),
        (output({"error": {"message": "offline"}}, 4), "could not load Google Drive's API description"),
        (Process(5, b"", b"panicked at src/main.rs"), "gws failed on file x (exit 5): panicked at src/main.rs"),
        (Process(3, b"", b""), "gws failed on file x (exit 3): no details"),
    ],
)
def test_failures_say_what_to_do(session, fake_gws, process, expected):
    fake_gws.on(FILES, process)
    assert expected in failure(session)


def test_not_signed_in_names_the_short_sign_in(session, fake_gws):
    fake_gws.on(FILES, output({"error": {"code": 401, "reason": "authError"}}, 2))
    text = failure(session)
    assert text.endswith("Sign in again: hz setup google.")
    assert "googleapis" not in text


def test_gws_text_is_cleaned_and_redacted_whole_before_it_is_cut(session, fake_gws):
    message = "x" * (MAX_SAID - 10) + TOKEN + "\u202e tail"  # the token straddles the cut
    fake_gws.on(FILES, output({"error": {"code": 500, "message": message}}, 1))
    text = failure(session)
    assert TOKEN[:12] not in text
    assert "\u202e" not in text


@pytest.mark.parametrize(
    "secret",
    # Shaped like the real thing, built so that no secret scanner mistakes the fakes for one.
    [TOKEN, "1//" + "f" * 30, "GOCSPX-" + "f" * 20, ".".join(["eyJ" + "a" * 8, "eyJ" + "b" * 8, "c" * 10])],
)
def test_redact_replaces_token_shaped_strings(secret):
    assert redact(f"before {secret} after") == "before *** after"


def page(items: list[object], token: str | None = None, size: int = 0) -> Process:
    body: dict[str, object] = {"files": items, "pad": "x" * size}
    if token:
        body["nextPageToken"] = token
    return output(body)


def test_pages_follow_the_page_token(session, fake_gws):
    fake_gws.on(LIST, page([{"id": 1}, "noise"], "p2"))
    fake_gws.on(LIST, page([{"id": 2}]), page="p2")
    found = [items for items, _ in session.pages("Google Drive", LIST, {"q": "x"}, "files", "files")]
    assert found == [[{"id": 1}], [{"id": 2}]]
    assert fake_gws.api_runs[1].params == {"q": "x", "pageToken": "p2"}


def test_pages_are_bounded_in_number_and_bytes(session, fake_gws, monkeypatch):
    monkeypatch.setattr(_gws, "MAX_PAGES", 2)
    fake_gws.on(LIST, page([], "again"))
    fake_gws.on(LIST, page([], "again"), page="again")
    with pytest.raises(HeinzelError, match="more than 2 pages"):
        list(session.pages("Google Drive", LIST, {}, "files", "files"))
    monkeypatch.setattr(_gws, "BUDGET", 100)
    fake_gws.on(LIST, page([], size=200))
    with pytest.raises(HeinzelError, match="pass 100 bytes; ask for a narrower window"):
        list(session.pages("Google Drive", LIST, {}, "files", "files"))


def test_a_page_without_a_list(session, fake_gws):
    fake_gws.json(LIST, {"files": "nope"})
    with pytest.raises(HeinzelError, match="without a list of files"):
        list(session.pages("Google Drive", LIST, {}, "files", "files"))


def test_deeply_nested_output_says_so(session, fake_gws, monkeypatch):
    def too_deep(data: bytes) -> object:
        raise RecursionError  # what json.loads raises past its nesting limit on some Pythons

    monkeypatch.setattr(_gws, "json", SimpleNamespace(loads=too_deep, dumps=json.dumps))
    fake_gws.on(FILES, Process(0, b"[" * 100_000 + b"]" * 100_000))
    assert "nests too deeply to read" in failure(session)


def test_an_error_printed_with_exit_zero_is_still_an_error(session, fake_gws):
    fake_gws.on(FILES, output({"error": {"code": 429}}), output({"error": {"code": 404}}))
    assert "has no file x" in failure(session)
    assert fake_gws.slept == [1.0]


def test_without_any_absolute_path_entry_nothing_is_found(fake_gws, monkeypatch):
    monkeypatch.setenv("PATH", "")
    with pytest.raises(HeinzelError, match="looked on PATH"):
        GoogleSession(GoogleSettings(), fake_gws).executable()


def test_the_version_is_checked_once_and_an_old_gws_is_refused(session, fake_gws):
    fake_gws.json(FILES, {"id": "x"})
    get(session)
    get(session)
    assert [r.arguments for r in fake_gws.runs].count(["--version"]) == 1
    fake_gws.version = Process(0, b"gws 0.21.9\n")
    with pytest.raises(HeinzelError, match=r"gws 0\.21\.9 is older than 0\.22\.0"):
        session.version()
    fake_gws.version = Process(0, b"something else")
    with pytest.raises(HeinzelError, match="gave no gws version, so it is not the Google Workspace CLI"):
        session.version()


GWS_0225 = b"gws 0.22.5\nThis is not an officially supported Google product.\n"
"""What `gws --version` of gws 0.22.5 prints, both lines."""


@pytest.mark.parametrize(
    ("stdout", "shown"),
    [(GWS_0225, "0.22.5"), (b"gws 0.22.0\n", "0.22.0"), (b"gws 1.3.0\nThis is not an officially supported\n", "1.3.0")],
    ids=["0.22.5 with its notice", "the oldest", "an unknown newer one"],
)
def test_every_gws_from_the_minimum_on_is_accepted(session, fake_gws, stdout, shown):
    fake_gws.version = Process(0, stdout)
    assert session.version() == shown


def test_a_gws_without_node_says_so_plainly(session, fake_gws, gws_path):
    fake_gws.version = Process(127, b"", b"env: node: No such file or directory\n")
    with pytest.raises(HeinzelError) as caught:
        session.version()
    assert str(caught.value) == (
        f"gws at {gws_path} needs Node.js, and Heinzel could not find it. "
        "Install Node.js (brew install node), then restart Heinzel. It said: env: node: No such file or directory"
    )


@pytest.mark.parametrize(
    ("process", "said"),
    [
        (Process(None, b""), "but it gave no answer within 10 seconds. Run {} --version in a terminal to see why."),
        (
            Process(1, b"", b"boom\nmore"),
            "but it failed to start (exit 1). Run {} --version in a terminal to see why. It said: boom",
        ),
        (Process(3, GWS_0225), "but it failed to start (exit 3). Run {} --version in a terminal to see why."),
    ],
    ids=["timeout", "an error", "a version with a failing exit"],
)
def test_a_gws_that_gives_no_version_names_where_and_what_next(session, fake_gws, gws_path, process, said):
    fake_gws.version = process
    with pytest.raises(HeinzelError) as caught:
        session.version()
    assert str(caught.value) == f"Heinzel found gws at {gws_path}, " + said.format(gws_path)


@pytest.mark.parametrize("which", [0, 1], ids=["Apple silicon", "Intel"])
def test_gws_is_found_where_homebrew_installs_it_under_a_launchd_path(fake_gws, no_homebrew, monkeypatch, which):
    installed = Path(no_homebrew[which]) / "gws"
    installed.parent.mkdir(parents=True)
    installed.write_text("#!/bin/sh\n", encoding="utf-8")
    installed.chmod(0o755)
    monkeypatch.setenv("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    assert GoogleSession(GoogleSettings(), fake_gws).executable() == str(installed)


def test_a_missing_gws_says_where_heinzel_looked(fake_gws, no_homebrew, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    with pytest.raises(HeinzelError) as caught:
        GoogleSession(GoogleSettings(), fake_gws).executable()
    assert str(caught.value) == (
        f"Heinzel can't find the Google Workspace CLI (gws): it looked on PATH, in {no_homebrew[0]} or "
        f"{no_homebrew[1]}. Install it: {_gws.INSTALL}."
    )


def test_gws_runs_with_its_own_directory_and_homebrew_after_path(no_homebrew):
    env = _gws.run_environment("/opt/tools/bin/gws", {"PATH": "/usr/bin:relative::/bin", "HOME": "/home/ada"})
    assert env == {"PATH": os.pathsep.join(["/usr/bin", "/bin", "/opt/tools/bin", *no_homebrew]), "HOME": "/home/ada"}


def test_a_linked_gws_runs_with_both_its_directories(no_homebrew, tmp_path):
    launcher = tmp_path / "lib" / "cli" / "run.js"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("", encoding="utf-8")
    link = tmp_path / "bin" / "gws"
    link.parent.mkdir()
    link.symlink_to(launcher)
    env = _gws.run_environment(str(link), {"PATH": "/usr/bin"})
    directories = [str(link.parent), str(launcher.resolve().parent)]
    assert env["PATH"] == os.pathsep.join(["/usr/bin", *directories, *no_homebrew])


def test_gws_gets_an_allowlisted_environment():
    source = {
        "PATH": "/bin",
        "HOME": "/home/ada",
        "LC_ALL": "C",
        "GOOGLE_WORKSPACE_CLI_CONFIG_DIR": "/home/ada/.config/gws",
        "HZ_CREDENTIAL_GITHUB_GITHUB_TOKEN": "t",
        "AWS_SECRET_ACCESS_KEY": "s",
        "GOOGLE_WORKSPACE_CLI_TOKEN": "another identity",
        "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE": "/elsewhere.json",
        "GOOGLE_WORKSPACE_CLI_SANITIZE_TEMPLATE": "projects/p/locations/l/templates/t",
        "GOOGLE_WORKSPACE_CLI_SANITIZE_MODE": "block",
        "GOOGLE_WORKSPACE_CLI_LOG": "gws=debug",
        "GOOGLE_WORKSPACE_CLI_LOG_FILE": "/somewhere/logs",
    }
    assert _gws.environment(source) == {
        "PATH": "/bin",
        "HOME": "/home/ada",
        "LC_ALL": "C",
        "GOOGLE_WORKSPACE_CLI_CONFIG_DIR": "/home/ada/.config/gws",
    }


def test_a_gws_that_starts_for_its_version_but_not_for_a_call(session, fake_gws):
    fake_gws.error, fake_gws.fail_after = PermissionError("denied"), 1
    assert "Could not start gws for file x: PermissionError" in failure(session)


INSERT = ("calendar", "events", "insert")


def write_failure(session: GoogleSession, api: str = "Google Calendar") -> str:
    with pytest.raises(HeinzelError) as caught:
        session.write(api, INSERT, {"calendarId": "primary"}, {"summary": "x"}, "the new event")
    return str(caught.value)


def test_a_write_passes_its_body_as_one_json_argument(session, fake_gws):
    fake_gws.json(INSERT, {"id": "e1"})
    assert session.write("Google Calendar", INSERT, {"calendarId": "primary"}, {"summary": "a; b"}, "x") == {"id": "e1"}
    (run,) = fake_gws.api_runs
    assert run.arguments == [
        *INSERT,
        "--params",
        '{"calendarId":"primary"}',
        "--json",
        '{"summary":"a; b"}',
        "--format",
        "json",
    ]


def test_a_write_without_a_body_or_an_answer_is_an_empty_object(session, fake_gws):
    fake_gws.on(INSERT, Process(0, b""))
    assert session.write("Google Calendar", INSERT, {"eventId": "e1"}, None, "event e1") == {}
    assert "--json" not in fake_gws.api_runs[0].arguments


def test_a_write_that_timed_out_says_to_look_before_retrying_and_is_not_retried(session, fake_gws):
    fake_gws.on(INSERT, Process(None, b""))
    assert "it may have happened: look in Google before trying again." in write_failure(session)
    assert len(fake_gws.api_runs) == 1


def test_a_rate_limited_write_is_retried_because_google_refused_it(session, fake_gws):
    fake_gws.on(INSERT, output({"error": {"code": 429}}, 1), output({"id": "e1"}))
    assert session.write("Google Calendar", INSERT, {}, {"summary": "x"}, "x") == {"id": "e1"}
    assert fake_gws.slept == [1.0]


@pytest.mark.parametrize(("api", "capability"), [("Google Calendar", "calendar"), ("Gmail", "mail")])
def test_a_write_without_the_write_scope_names_the_short_step_that_allows_it(session, fake_gws, api, capability):
    fake_gws.on(INSERT, output({"error": {"code": 403, "errors": [{"reason": "insufficientPermissions"}]}}, 1))
    text = write_failure(session, api)
    assert f"your Google sign-in lets Heinzel read your {capability} but not change it" in text
    assert text.endswith(f"To allow changes, run hz setup google and let Heinzel change your {capability}.")
    assert "googleapis" not in text


def test_a_conflicting_write_says_to_read_again(session, fake_gws):
    fake_gws.on(INSERT, output({"error": {"code": 409, "message": "changed"}}, 1))
    assert "it exists already or changed meanwhile (changed); look before retrying" in write_failure(session)


@pytest.mark.parametrize(
    "process",
    [
        output({"error": {"code": 503, "message": "backendError"}}, 1),
        Process(7, b"", b"connection reset"),
        Process(0, b"<html>"),
    ],
    ids=["a server error", "no answer", "no JSON"],
)
def test_a_write_that_failed_without_a_refusal_may_have_happened(session, fake_gws, process):
    fake_gws.on(INSERT, process)
    assert write_failure(session).endswith("It may have happened: look in Google before trying again.")
    assert len(fake_gws.api_runs) == 1


def test_a_refused_write_says_nothing_about_maybe(session, fake_gws):
    fake_gws.on(INSERT, output({"error": {"code": 400, "message": "bad"}}, 1))
    assert "may have happened" not in write_failure(session)


def test_a_read_may_post_a_body(session, fake_gws):
    fake_gws.json(INSERT, {"calendars": {}})
    assert session.get("Google Calendar", INSERT, {}, "x", body={"items": []})[0] == {"calendars": {}}
    assert fake_gws.api_runs[0].body == {"items": []}


def test_the_sign_in_asks_for_write_scopes_only_when_writes_are_allowed():
    assert login_command() == LOGIN
    assert login_command(mail=True).endswith(MAIL_SCOPE)
    both = login_command(mail=True, write=frozenset({"calendar", "mail"})).split()[-1].split(",")
    assert both == [*SCOPES, MAIL_WRITE_SCOPE, CALENDAR_WRITE_SCOPE]
    assert MAIL_SCOPE not in both  # gmail.modify reads too
