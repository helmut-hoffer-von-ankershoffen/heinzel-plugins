import pytest
from heinzel import Kernel, Status

from heinzel_atlassian import AtlassianService, AtlassianSettings
from heinzel_atlassian._auth import parse
from heinzel_atlassian._status import read

pytestmark = pytest.mark.unit

SITE = "acme.atlassian.net"


def status(fake, products=("Jira",)):
    return read(fake, 60.0, list(products))


def test_the_parser_reads_site_email_type_and_the_apps_that_are_missing(fake_acli):
    state = parse(fake_acli.auth("global_apps_missing"), 0)
    assert (state.signed_in, state.site, state.email, state.kind) == (True, SITE, "ada@example.com", "oauth")
    assert state.missing == ("Jira", "Confluence")


def test_the_parser_reads_signed_out_and_does_not_guess(fake_acli):
    assert parse(fake_acli.auth("global_unauthorized"), 1).signed_in is False
    assert parse("", 0).signed_in is None
    assert parse("something new", 0).signed_in is None
    assert parse("\x1b[32m✓ Authenticated\x1b[0m\n  Site: https://Acme.atlassian.net/\n", 0).site == SITE
    assert parse("✓ Authenticated\n  Site: evil.example.com\n", 0).site == ""


def test_signed_in_to_acli_but_jira_and_confluence_not_authorised_needs_attention(fake_acli):
    fake_acli.answer("auth status", fake_acli.auth("global_apps_missing"))
    fake_acli.fail("jira auth status", fake_acli.auth("jira_unauthorized"))
    fake_acli.fail("confluence auth status", fake_acli.auth("confluence_unauthorized"))
    found = status(fake_acli, ("Jira", "Confluence"))
    assert found.state == "needs-attention"
    assert found.cause == f"Signed in to acli as ada@example.com at {SITE}. Jira and Confluence are not authorised yet."
    assert (found.identity, found.site) == ("ada@example.com", SITE)
    assert found.command == "acli jira auth login --web"
    assert found.action == "Copy sign-in command"
    assert found.refresh == "Check again"
    assert [(p.product, p.authorised) for p in found.products] == [("Jira", False), ("Confluence", False)]


def test_fully_authorised_is_connected_without_an_action(fake_acli):
    fake_acli.answer("jira auth status", fake_acli.auth("authenticated"))
    fake_acli.fail("auth status", fake_acli.auth("global_unauthorized"))  # the global profile is not needed
    found = status(fake_acli)
    assert (found.state, found.site, found.identity) == ("connected", SITE, "ada@example.com")
    assert (found.command, found.action) == ("", "")


def test_one_product_authorised_and_the_other_not_names_the_other(fake_acli):
    fake_acli.answer("jira auth status", fake_acli.auth("authenticated"))
    fake_acli.fail("confluence auth status", fake_acli.auth("confluence_unauthorized"))
    found = status(fake_acli, ("Jira", "Confluence"))
    assert (found.state, found.cause) == ("needs-attention", "Confluence is not authorised yet.")
    assert found.command == "acli confluence auth login --web"


def test_not_logged_in_anywhere_is_not_connected(fake_acli):
    found = status(fake_acli)
    assert (found.state, found.cause, found.identity, found.site) == ("not-connected", "Not signed in to acli.", "", "")
    assert found.command == "acli jira auth login --web"


def test_acli_not_installed_names_the_install(fake_acli):
    fake_acli.location = None
    found = status(fake_acli)
    assert (found.state, found.command, found.action) == ("not-installed", "brew install acli", "Copy install command")
    assert fake_acli.calls == []


def test_an_answer_that_is_not_understood_needs_attention_without_a_verdict(fake_acli):
    fake_acli.answer("jira auth status", "???")
    found = status(fake_acli)
    assert found.state == "needs-attention"
    assert found.products[0].authorised is None


def test_the_site_comes_from_acli_when_the_setting_is_empty(fake_acli):
    fake_acli.answer("jira auth status", fake_acli.auth("authenticated"))
    assert fake_acli.site(AtlassianSettings()) == f"https://{SITE}"
    assert fake_acli.site(AtlassianSettings(site_url="https://mine.atlassian.net")) == "https://mine.atlassian.net"


def test_the_site_falls_back_to_the_global_profile(fake_acli):
    fake_acli.answer("auth status", fake_acli.auth("global_apps_missing"))
    assert fake_acli.site(AtlassianSettings()) == f"https://{SITE}"


def test_no_site_when_acli_is_signed_out_or_missing(fake_acli):
    assert fake_acli.site(AtlassianSettings()) is None
    fake_acli.location = None
    assert fake_acli.site(AtlassianSettings()) is None


def test_the_doctor_check_carries_the_verdict_and_the_login_command(fake_acli):
    fake_acli.answer("auth status", fake_acli.auth("global_apps_missing"))
    fake_acli.fail("jira auth status", fake_acli.auth("jira_unauthorized"))
    bindings = type("B", (), {"bound": lambda self, c: "atlassian" if c == "tracker" else None})()
    checks = {c.name: c for c in AtlassianService(Kernel(), AtlassianSettings(), fake_acli).checks(bindings)}
    acli = checks["acli"]
    assert acli.status is Status.DEGRADED
    assert acli.login is not None
    assert (acli.login.signed_in, acli.login.account, acli.login.site) == (False, "ada@example.com", SITE)
    assert acli.login.command == "acli jira auth login --web"
    assert checks["site"].status is Status.UP
    assert "ada@example.com" in acli.detail
    assert all("token" not in str(c).lower() for c in checks.values())
