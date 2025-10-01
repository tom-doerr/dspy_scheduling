"""Playwright configuration for e2e tests."""

from playwright.sync_api import sync_playwright

# Configuration for Playwright
BASE_URL = "http://localhost:5000"

# Browser options
HEADLESS = True
SLOW_MO = 0  # Milliseconds to slow down operations (useful for debugging)

# Test timeouts
DEFAULT_TIMEOUT = 30000  # 30 seconds
NAVIGATION_TIMEOUT = 30000  # 30 seconds
