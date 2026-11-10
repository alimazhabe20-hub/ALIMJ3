"""Backward-compatible weather module alias.

The implementation lives in ``features_weather_weather``; this module keeps
legacy imports working without duplicating provider logic.
"""
from .features_weather_weather import *  # noqa: F401,F403
from .features_weather_weather import _request_get

# Historical private alias used by integrations and tests.
_get = _request_get
