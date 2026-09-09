"""Release metadata and lightweight runtime information for Rooze Ziba / ALIMJ."""
from __future__ import annotations

APP_NAME = "Rooze Ziba / ALIMJ"
VERSION = "58.0.0"
RELEASE_CHANNEL = "production"
PRODUCT_CODE = "ALIMJ"


def version_string() -> str:
    return f"{APP_NAME} {VERSION} ({RELEASE_CHANNEL})"


def product_label() -> str:
    return f"{APP_NAME} v{VERSION}"
