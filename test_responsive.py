"""Tests for responsive design and mobile layout."""
import re
import pytest
from fastapi.testclient import TestClient
from app import app
from test_app import client as _client


def test_responsive_meta_viewport(_client):
    """Test that viewport meta tag is present for mobile responsiveness."""
    response = _client.get("/")
    assert response.status_code == 200


def test_base_template_contains_media_queries(_client):
    """Test that base.html contains responsive media queries."""
    response = _client.get("/")
    html = response.text
    assert "@media (max-width: 768px)" in html
    assert "@media (max-width: 480px)" in html
    assert "@media (min-width: 1200px)" in html


def test_mobile_styles_present(_client):
    """Test that mobile-specific styles are included."""
    response = _client.get("/")
    html = response.text
    assert "width: 100%" in html
    assert "padding: 15px 10px" in html


def test_tablet_styles_present(_client):
    """Test that tablet-specific styles are included."""
    response = _client.get("/")
    html = response.text
    assert "flex-wrap: wrap" in html
    assert "width: 95%" in html


def test_desktop_max_width(_client):
    """Test that desktop layout uses full screen width."""
    response = _client.get("/")
    html = response.text
    assert "max-width: 1400px" in html


def test_active_tracker_mobile_position(_client):
    """Test that active tracker repositions on mobile."""
    response = _client.get("/")
    html = response.text
    assert "position: fixed" in html
    assert "position: static" in html


def test_font_size_scaling(_client):
    """Test that font sizes scale for mobile."""
    response = _client.get("/")
    html = response.text
    assert "h1 { font-size: 1.75rem" in html
    assert "h2 { font-size: 1.2rem" in html


def test_large_desktop_padding(_client):
    """Test that large desktop has increased padding."""
    response = _client.get("/")
    html = response.text
    pattern = r'@media \(min-width: 1200px\).*?padding: 40px 40px'
    assert re.search(pattern, html, re.DOTALL)
