"""
conftest.py — Shared pytest fixtures and configuration.

All test modules in this package inherit these fixtures automatically.
"""

import asyncio
import pytest


# ---------------------------------------------------------------------------
# Asyncio mode
# ---------------------------------------------------------------------------
# pytest-asyncio >= 0.21 requires explicit mode declaration.
# "auto" means async test functions are automatically collected without needing
# the @pytest.mark.asyncio decorator on every test.
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (handled by pytest-asyncio)"
    )


# ---------------------------------------------------------------------------
# Shared sample data
# ---------------------------------------------------------------------------

@pytest.fixture
def safe_url():
    return "https://www.google.com"


@pytest.fixture
def phishing_url():
    """A clearly typosquatted URL used across agent tests."""
    return "https://paypa1-secure-login.xyz"


@pytest.fixture
def ip_url():
    return "http://192.168.1.1/admin"


@pytest.fixture
def phishing_message():
    return (
        "URGENT: Your GTBank account has been compromised. "
        "Click http://gtbank-secure-verify.com/login to restore access."
    )
