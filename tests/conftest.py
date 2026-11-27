"""Test-only configuration for the shared plugin toolkit."""

import pytest


@pytest.fixture
def fictional_capture_terms(monkeypatch):
    """Give opted-in gallery fixtures a synthetic term without disabling the CI guard."""
    monkeypatch.setenv("CONFIDENTIAL_TERMS", "fictional-capture-canary-8329")
