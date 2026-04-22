"""Tests for the QR code generator."""
from __future__ import annotations

import base64

from services.qr_generator import generate_qr_base64


class TestGenerateQR:
    def test_returns_data_uri(self):
        result = generate_qr_base64("https://example.com")
        assert result.startswith("data:image/png;base64,")

    def test_decodable_base64(self):
        result = generate_qr_base64("https://example.com/attend?token=abc")
        # Strip the data URI prefix
        b64_data = result.split(",", 1)[1]
        # Should decode without error
        decoded = base64.b64decode(b64_data)
        assert len(decoded) > 0
        # PNG files start with these magic bytes
        assert decoded[:4] == b"\x89PNG"

    def test_different_urls_produce_different_qr(self):
        qr1 = generate_qr_base64("https://example.com/a")
        qr2 = generate_qr_base64("https://example.com/b")
        assert qr1 != qr2

    def test_empty_url(self):
        result = generate_qr_base64("")
        assert result.startswith("data:image/png;base64,")
