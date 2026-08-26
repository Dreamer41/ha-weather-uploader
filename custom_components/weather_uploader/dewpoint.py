"""Automatic Dew Point calculation used by the Weather Network Uploader."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from .uploaders.base import BaseUploader

_LOGGER = logging.getLogger(__name__)


def calculate_dew_point(temp_c: float, humidity_percent: float) -> float | None:
    """Calculate Dew Point in Celsius using the Ecowitt-style formula."""
    if not (0.0 < humidity_percent <= 100.0):
        return None
    return round(
        (humidity_percent / 100.0) ** 0.125 * (112.0 + 0.9 * temp_c)
        + 0.1 * temp_c
        - 112.0,
        1,
    )


def prepare_upload_data(data: dict[str, float]) -> dict[str, float]:
    """Return an upload snapshot with automatic Dew Point when possible.

    Temperature and humidity are already normalized by the coordinator,
    so both values come from the same snapshot used for the upload.
    An explicitly mapped dewpoint is never overwritten.
    """
    result = dict(data)
    temp = result.get("temperature")
    humidity = result.get("humidity")
    if temp is None or humidity is None or result.get("dewpoint") is not None:
        return result

    dewpoint = calculate_dew_point(temp, humidity)
    if dewpoint is not None:
        result["dewpoint"] = dewpoint
    return result


_original_send: Callable[..., Awaitable[bool]] | None = None


async def _send_with_automatic_dewpoint(
    self: BaseUploader, data: dict[str, float]
) -> bool:
    """Send a snapshot after adding the calculated Dew Point."""
    upload_data = prepare_upload_data(data)

    if "dewpoint" in data:
        temp = data.get("temperature")
        humidity = data.get("humidity")
        calculated = (
            calculate_dew_point(temp, humidity)
            if temp is not None and humidity is not None
            else None
        )
        if calculated is not None:
            _LOGGER.debug(
                "%s Dew Point cross-check: mapped=%.1f C, calculated=%.1f C, "
                "difference=%+.1f C",
                self.name,
                data["dewpoint"],
                calculated,
                data["dewpoint"] - calculated,
            )

    if "dewpoint" not in data and "dewpoint" in upload_data:
        _LOGGER.debug(
            "%s automatic Dew Point: %.1f C from T=%.1f C RH=%.1f%%",
            self.name,
            upload_data["dewpoint"],
            upload_data["temperature"],
            upload_data["humidity"],
        )

    assert _original_send is not None
    return await _original_send(self, upload_data)


def install() -> None:
    """Install the upload-time Dew Point hook once."""
    global _original_send
    if _original_send is not None:
        return
    _original_send = BaseUploader.send
    BaseUploader.send = _send_with_automatic_dewpoint
