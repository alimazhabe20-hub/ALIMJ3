"""Release metadata and lightweight runtime information for Rooze Ziba."""
APP_NAME = "Rooze Ziba / ALIMJ"
VERSION = "41.0.0"
RELEASE_CHANNEL = "production"


def version_string() -> str:
    return f"{APP_NAME} {VERSION} ({RELEASE_CHANNEL})"
