"""Release metadata and lightweight runtime information for Rooze Ziba / ALIMJ."""

APP_NAME = "Rooze Ziba / ALIMJ"
VERSION = "80.2.0"
RELEASE_CHANNEL = "production"
PRODUCT_CODE = "ALIMJ"


def version_string() -> str:
    return f"{APP_NAME} {VERSION} ({RELEASE_CHANNEL})"


def product_label() -> str:
    return f"{APP_NAME} v{VERSION}"
