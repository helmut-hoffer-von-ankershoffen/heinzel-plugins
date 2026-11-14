"""Every capability the adapter declares is implemented with the protocol's methods and signatures (ADR 0028)."""

import inspect

import pytest
from heinzel import CredentialLet, ProviderLet
from heinzel.kernel import CAPABILITIES

from heinzel_atlassian import MULTI, AtlassianSettings, hosts, links, module

pytestmark = pytest.mark.unit

PROVIDERS = [let for let in module.lets if isinstance(let, ProviderLet)]


def test_the_adapter_serves_tracker_and_documents_read_only_on_the_configured_site():
    assert sorted((p.name, sorted(p.modes), p.hosts, p.configured_hosts) for p in PROVIDERS) == [
        ("atlassian:documents", ["read"], (), hosts),
        ("atlassian:tracker", ["read"], (), hosts),
    ]


def test_the_hosts_are_the_site_and_the_gateway_once_the_site_is_set(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))  # no acli to ask for a site
    assert hosts(AtlassianSettings()) == []
    assert hosts(AtlassianSettings(site_url="https://acme.atlassian.net/wiki")) == [
        "https://acme.atlassian.net",
        "api.atlassian.com",
    ]


def test_no_credential_is_declared_because_acli_owns_authentication():
    assert not [let for let in module.lets if isinstance(let, CredentialLet)]


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.name)
def test_methods_of_the_declared_modes_match_the_protocol(provider):
    capability = CAPABILITIES[provider.capability]
    optional = getattr(capability, "optional_methods", frozenset())  # ADR 0161 Core; none before
    served = [
        name
        for name, mode in capability.methods.items()
        if mode in provider.modes and (name not in optional or hasattr(provider.factory, name))
    ]
    assert served
    for name in served:
        implemented = inspect.signature(getattr(provider.factory, name), eval_str=True)
        declared = inspect.signature(getattr(capability.protocol, name), eval_str=True)
        assert implemented == declared, name


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.name)
def test_no_write_method_is_implemented(provider):
    capability = CAPABILITIES[provider.capability]
    writes = [name for name, mode in capability.methods.items() if mode == "write"]
    assert not [name for name in writes if hasattr(provider.factory, name)]


def test_links_are_the_site_host_only_never_the_gateway(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))  # no acli to ask for a site
    assert links(AtlassianSettings()) == []
    assert links(AtlassianSettings(site_url="https://acme.atlassian.net/wiki")) == ["acme.atlassian.net"]


def test_only_the_documents_provider_declares_links_and_only_on_a_core_that_knows_them():
    by_name = {p.name: p for p in PROVIDERS}
    tracker, documents = by_name["atlassian:tracker"], by_name["atlassian:documents"]
    assert not getattr(tracker, "links", ())
    assert getattr(tracker, "configured_links", None) is None
    assert not getattr(documents, "links", ())  # a function of settings is kept as `configured_links`
    assert getattr(documents, "configured_links", None) is (links if MULTI else None)


def test_confluence_does_not_search_until_acli_can():
    from heinzel_atlassian import Confluence

    assert not hasattr(Confluence, "search")
