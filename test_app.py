import json
import pytest
import pandas as pd
from types import SimpleNamespace

# Импортирую функции из моего приложения
from app import (
    get_location_from_ip,
    geocode,
    fetch_weather,
    deg_to_compass,
    nice_time,
)

# Простой MockResponse для подмены requests.get
class MockResponse:
    def __init__(self, json_data=None, status_code=200, raise_exc=False):
        self._json = json_data or {}
        self.status_code = status_code
        self._raise_exc = raise_exc

    def json(self):
        return self._json

    def raise_for_status(self):
        if self._raise_exc or not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

# ---------------------------
# get_location_from_ip тесты
# ---------------------------
def test_get_location_from_ip_success(monkeypatch):
    sample = {
        "city": "Moscow",
        "country_name": "Russia",
        "latitude": 55.75,
        "longitude": 37.6167,
    }
    def fake_get(url, timeout):
        return MockResponse(json_data=sample, status_code=200)
    monkeypatch.setattr("app.requests.get", fake_get)

    loc = get_location_from_ip()
    assert loc["city"] == "Moscow"
    assert loc["country"] == "Russia"
    assert abs(loc["lat"] - 55.75) < 1e-6
    assert abs(loc["lon"] - 37.6167) < 1e-6

def test_get_location_from_ip_error(monkeypatch):
    def fake_get(url, timeout):
        raise Exception("network error")
    monkeypatch.setattr("app.requests.get", fake_get)

    loc = get_location_from_ip()
    assert loc is None

# ---------------------------
# geocode тесты
# ---------------------------
def test_geocode_parsing(monkeypatch):
    # Подготовим ответ API geocoding
    payload = {
        "results": [
            {
                "name": "Moscow",
                "admin1": "Moskva",
                "country": "Russia",
                "latitude": 55.75,
                "longitude": 37.6167,
                "timezone": "Europe/Moscow",
            }
        ]
    }
    def fake_get(url, params, timeout):
        # проверим, что query передан
        assert "name" in params
        return MockResponse(json_data=payload, status_code=200)

    monkeypatch.setattr("app.requests.get", fake_get)
    places = geocode("Moscow", "ru")
    assert isinstance(places, list)

def test_geocode_empty_query():
    assert geocode("", "en") == []

# ---------------------------
# fetch_weather тесты
# ---------------------------
def test_fetch_weather_success(monkeypatch):
    sample_weather = {"timezone": "UTC", "current": {"temperature_2m": 10}}
    captured = {}
    def fake_get(url, params, timeout):
        # проверим, что параметры содержат latitude/longitude
        assert "latitude" in params
        assert "longitude" in params
        captured['params'] = params
        return MockResponse(json_data=sample_weather, status_code=200)
    monkeypatch.setattr("app.requests.get", fake_get)

    res = fetch_weather(55.75, 37.61, "Celsius")
    assert res["current"]["temperature_2m"] == 10
    assert captured['params']["temperature_unit"] in ("celsius", "fahrenheit")

def test_fetch_weather_http_error(monkeypatch):
    def fake_get(url, params, timeout):
        return MockResponse(json_data={}, status_code=500, raise_exc=True)
    monkeypatch.setattr("app.requests.get", fake_get)
    with pytest.raises(Exception):
        fetch_weather(0, 0, "Celsius")

# ---------------------------
# deg_to_compass тесты
# ---------------------------
@pytest.mark.parametrize(
    "deg, expected",
    [
        (0, "N"),
        (44, "NE"),
        (90, "E"),
        (135, "SE"),
        (180, "S"),
        (225, "SW"),
        (270, "W"),
        (315, "NW"),
        (359, "N"),
    ],
)
def test_deg_to_compass(deg, expected):
    assert deg_to_compass(deg) == expected

# ---------------------------
# nice_time тесты
# ---------------------------
def test_nice_time_utc_en():
    s = nice_time("2025-11-12T12:00:00Z", "UTC", "en")
    assert s == "2025-11-12 12:00"

def test_nice_time_utc_ru():
    s = nice_time("2025-11-12T12:00:00Z", "UTC", "ru")
    assert s == "12.11 12:00"

# ---------------------------
# hourly DataFrame фильтр
# ---------------------------
def test_hourly_dataframe_filtering():
    # создадим hourly и daily похожие на API
    hourly = {
        "time": [
            "2025-11-12T00:00:00Z",
            "2025-11-12T01:00:00Z",
            "2025-11-13T00:00:00Z",
        ],
        "temperature_2m": [1.0, 2.0, 3.0],
        "apparent_temperature": [0.5, 1.5, 2.5],
        "relative_humidity_2m": [50, 60, 70],
        "precipitation": [0, 0.1, 0],
    }
    daily = {"time": ["2025-11-12", "2025-11-13"]}
    # воспроизведу фрагмент кода, который фильтрует по today_date
    hdf = pd.DataFrame(
        {
            "time": hourly["time"],
            "temp": hourly["temperature_2m"],
            "feels_like": hourly["apparent_temperature"],
            "humidity": hourly["relative_humidity_2m"],
            "precip": hourly["precipitation"],
        }
    )
    today_date = daily.get("time", [None])[0]
    assert today_date == "2025-11-12"
    hdf_filtered = hdf[hdf["time"].str.startswith(today_date)]
    assert len(hdf_filtered) == 2
    assert list(hdf_filtered["temp"]) == [1.0, 2.0]