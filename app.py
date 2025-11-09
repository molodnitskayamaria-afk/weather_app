import requests
import pandas as pd
import pytz
from datetime import datetime
import streamlit as st

st.set_page_config(page_title="Weather", page_icon="⛅", layout="centered")

# ----------------------- UI: Sidebar Controls -----------------------
with st.sidebar:
    st.title("⛅ Погода")
    city_query = st.text_input("Город или место", value="Saint-Petersburg")
    units = st.radio("Единица измерения", options=["Цельсий", "Фаренгейт"], horizontal=True, index=0)
    show_hourly = st.toggle("Показать почасовую динамику", value=True)

st.title("Weather")
st.caption("Powered by Open-Meteo")

# ----------------------- Helpers -----------------------
@st.cache_data(ttl=3600)  # храним кэшированные данные 1 час
def geocode(query: str):
    """Return a list of matching places with lat/lon using Open-Meteo geocoding."""
    if not query:
        return []
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": query, "count": 5, "language": "en", "format": "json"}, timeout=15)
    r.raise_for_status()
    data = r.json().get("results", []) or []
    # Normalize
    places = []
    for p in data:
        label_parts = [p.get("name")]
        if p.get("admin1"): label_parts.append(p["admin1"])
        if p.get("country"): label_parts.append(p["country"])
        label = ", ".join([x for x in label_parts if x])
        places.append({
            "label": label,
            "lat": p.get("latitude"),
            "lon": p.get("longitude"),
            "tz": p.get("timezone", "UTC"),
        })
    return places

@st.cache_data(ttl=900)  # 15 minutes
def fetch_weather(lat: float, lon: float, temp_unit: str):
    """Fetch current, hourly (today), and 7-day forecast."""
    # Units
    is_f = temp_unit == "Fahrenheit"
    temp_unit_param = "fahrenheit" if is_f else "celsius"
    wind_unit_param = "mph" if is_f else "kmh"

    # Request both hourly and daily in one call
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "apparent_temperature", "wind_speed_10m", "wind_direction_10m", "relative_humidity_2m", "weather_code"],
        "hourly": ["temperature_2m", "apparent_temperature", "precipitation", "relative_humidity_2m"],
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset", "precipitation_sum", "wind_speed_10m_max"],
        "temperature_unit": temp_unit_param,
        "wind_speed_unit": wind_unit_param,
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

WEATHER_DESCRIPTIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle (light)", 57: "Freezing drizzle (dense)",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Freezing rain (light)", 67: "Freezing rain (heavy)",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers (slight)", 81: "Rain showers (moderate)", 82: "Rain showers (violent)",
    85: "Snow showers (slight)", 86: "Snow showers (heavy)",
    95: "Thunderstorm", 96: "Thunderstorm w/ slight hail", 97: "Thunderstorm w/ heavy hail"
}
WEATHER_EMOJI = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    77: "🌨️",
    80: "🌧️", 81: "🌧️", 82: "⛈️",
    85: "🌨️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 97: "⛈️"
}

def deg_to_compass(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    ix = int((deg/22.5)+0.5) % 16
    return dirs[ix]

def nice_time(ts, tz_str):
    try:
        tz = pytz.timezone(tz_str)
        dt = datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(tz)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts

# ----------------------- Flow -----------------------
places = geocode(city_query)

if not places:
    st.warning("No places found. Try a different search (e.g., 'Paris, France').")
    st.stop()

# Pick the first match, let user change
labels = [p["label"] for p in places]
choice = st.selectbox("Choose a location", options=labels, index=0)
place = places[labels.index(choice)]

try:
    data = fetch_weather(place["lat"], place["lon"], units)
except requests.HTTPError as e:
    st.error(f"Weather API error: {e}")
    st.stop()
except Exception as e:
    st.error(f"Something went wrong: {e}")
    st.stop()

tz = data.get("timezone", place["tz"])
current = data.get("current", {})
daily = data.get("daily", {})
hourly = data.get("hourly", {})

# ----------------------- Current Conditions Card -----------------------
c_temp = current.get("temperature_2m")
c_feels = current.get("apparent_temperature")
c_ws = current.get("wind_speed_10m")
c_wd = current.get("wind_direction_10m")
c_rh = current.get("relative_humidity_2m")
c_code = current.get("weather_code", 0)
desc = WEATHER_DESCRIPTIONS.get(c_code, "—")
emoji = WEATHER_EMOJI.get(c_code, "🌡️")
temp_unit_symbol = "°F" if units == "Fahrenheit" else "°C"
wind_unit_symbol = "mph" if units == "Fahrenheit" else "km/h"

st.subheader(f"{emoji} {desc}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Temperature", f"{c_temp:.1f}{temp_unit_symbol}")
col2.metric("Feels like", f"{c_feels:.1f}{temp_unit_symbol}")
col3.metric("Wind", f"{c_ws:.0f} {wind_unit_symbol} {deg_to_compass(c_wd) if c_wd is not None else ''}")
col4.metric("Humidity", f"{c_rh:.0f}%")

# ----------------------- Hourly Today (optional) -----------------------
if show_hourly and "time" in hourly:
    # Build a pandas df for today only (same date as first daily entry)
    today_date = daily.get("time", [None])[0]
    hdf = pd.DataFrame({
        "time": hourly.get("time", []),
        "temp": hourly.get("temperature_2m", []),
        "feels_like": hourly.get("apparent_temperature", []),
        "humidity": hourly.get("relative_humidity_2m", []),
        "precip": hourly.get("precipitation", []),
    })
    if today_date:
        hdf = hdf[hdf["time"].str.startswith(today_date)]
    hdf_display = hdf.copy()
    # Convert time to local
    hdf_display["local_time"] = hdf_display["time"].apply(lambda x: nice_time(x, tz))
    hdf_display = hdf_display[["local_time", "temp", "feels_like", "humidity", "precip"]].rename(columns={
        "local_time": "Time",
        "temp": f"Temp ({temp_unit_symbol})",
        "feels_like": f"Feels ({temp_unit_symbol})",
        "humidity": "Humidity (%)",
        "precip": "Precip (mm)"
    })
    st.markdown("### Hourly (today)")
    st.dataframe(hdf_display, use_container_width=True)
    st.line_chart(hdf.set_index("time")[["temp"]], height=220)

# ----------------------- 7-Day Forecast -----------------------
if "time" in daily and daily["time"]:
    fdf = pd.DataFrame({
        "date": daily["time"],
        "code": daily.get("weather_code", []),
        "tmax": daily.get("temperature_2m_max", []),
        "tmin": daily.get("temperature_2m_min", []),
        "precip": daily.get("precipitation_sum", []),
        "windmax": daily.get("wind_speed_10m_max", []),
        "sunrise": daily.get("sunrise", []),
        "sunset": daily.get("sunset", []),
    })
    fdf["desc"] = fdf["code"].map(lambda c: WEATHER_DESCRIPTIONS.get(c, "—"))
    fdf["emoji"] = fdf["code"].map(lambda c: WEATHER_EMOJI.get(c, "🌡️"))

    st.markdown("### 7-Day Forecast")
    for _, row in fdf.iterrows():
        with st.container(border=True):
            st.markdown(
                f"**{row['date']}**  {row['emoji']}  {row['desc']}  "
                f" | High: **{row['tmax']:.1f}{temp_unit_symbol}**  "
                f" | Low: **{row['tmin']:.1f}{temp_unit_symbol}**  "
                f" | Precip: **{row['precip']:.1f} mm**  "
                f" | Max wind: **{row['windmax']:.0f} {wind_unit_symbol}**"
            )
            st.caption(f"Sunrise: {nice_time(row['sunrise'], tz)}  ·  Sunset: {nice_time(row['sunset'], tz)}")
else:
    st.info("No daily forecast available for this location.")

st.caption("Tips: Use the sidebar to change city and units. Results are cached for speed (refreshes automatically).")


