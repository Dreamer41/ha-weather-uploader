"""Automatic Dew Point calculation for weather uploads.

This fork calculates Dew Point from the normalized temperature and relative
humidity values immediately before each network upload when no explicit
``dewpoint`` reading was mapped.

The calculation matches the Ecowitt-style formula used by the project:

    Td = RH^(1/8) * (112 + 0.9*T) + 0.1*T - 112

where RH is relative humidity as a fraction and T is degrees Celsius.
"""

from __future__ import annotations

import logging
from typing import Any

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


_original_send = BaseUploader.send


async def _send_with_automatic_dewpoint(
    self: BaseUploader, data: dict[str, float]
) -> bool:
    """Add an atomic calculated Dew Point when no mapped value exists.

    Temperature and humidity have already been read and normalized by the
    coordinator. The calculation therefore uses exactly the same snapshot
    that is passed to the uploader, avoiding the Home Assistant template
    sensor timing problem.

    If an explicit ``dewpoint`` value is mapped, it is preserved and the
    calculated value is logged as a debugging cross-check instead.
    """
    upload_data = dict(data)
    temp = upload_data.get("temperature")
    humidity = upload_data.get("humidity")

    if temp is not None and humidity is not None:
        calculated = calculate_dew_point(temp, humidity)
        if calculated is not None:
            supplied = upload_data.get("dewpoint")
            if supplied is None:
                upload_data["dewpoint"] = calculated
                _LOGGER.debug(
                    "%s: automatic Dew Point %.1f C from T=%.1f C, RH=%.1f%%",
                    self.name,
                    calculated,
                    temp,
                    humidity,
                )
            else:
                difference = supplied - calculated
                _LOGGER.debug(
                    "%s: Dew Point cross-check: supplied=%.1f C, "
                    "calculated=%.1f C, difference=%+.1f C",
                    self.name,
                    supplied,
                    calculated,
                    difference,
                )

    return await _original_send(self, upload_data)


# Keep the existing uploader classes unchanged while applying the fork's
# upload-time calculation consistently to every supported network.
BaseUploader.send = _send_with_automatic_dewpoint
