"""Pytest configuration for both unit and e2e tests."""

import pytest

try:
    from playwright.sync_api import BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Configuration for Playwright e2e tests
BASE_URL = "http://localhost:5000"
HEADLESS = True


# Note: Unit test fixtures are now in test_app.py to avoid conflicts
# The client fixture in test_app.py uses proper database isolation


# Playwright fixtures for e2e tests
@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Configure browser launch arguments."""
    return {
        "headless": HEADLESS,
        "args": ["--no-sandbox", "--disable-setuid-sandbox"]
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "base_url": BASE_URL
    }


@pytest.fixture
def page(context: BrowserContext) -> Page:
    """Create a new page for each test."""
    page = context.new_page()
    page.set_default_timeout(30000)
    yield page
    page.close()
