"""Tests for the fork's automatic Dew Point calculation."""

from custom_components.weather_uploader.dewpoint import (
    calculate_dew_point,
    prepare_upload_data,
)


def test_ecowitt_dew_point_formula() -> None:
    """The calculation matches the Ecowitt-style formula and 1-decimal rounding."""
    assert calculate_dew_point(28.3, 75.1) == 23.5


def test_automatic_dew_point_uses_same_snapshot() -> None:
    """Temperature and humidity are combined without a separate HA sensor."""
    data = {"temperature": 28.3, "humidity": 75.1}
    result = prepare_upload_data(data)
    assert result["temperature"] == 28.3
    assert result["humidity"] == 75.1
    assert result["dewpoint"] == 23.5


def test_explicit_dew_point_is_not_overwritten() -> None:
    """A mapped Dew Point remains authoritative for cross-checking."""
    data = {"temperature": 28.3, "humidity": 75.1, "dewpoint": 23.4}
    assert prepare_upload_data(data) == data


def test_invalid_humidity_does_not_create_dew_point() -> None:
    """Invalid humidity values cannot produce an automatic Dew Point."""
    assert prepare_upload_data({"temperature": 28.3, "humidity": 0.0}) == {
        "temperature": 28.3,
        "humidity": 0.0,
    }
