import requests
import pandas as pd
import pytz
from datetime import datetime
import streamlit as st
import pydeck as pdk

st.set_page_config(page_title="Weather", page_icon="⛅", layout="centered")

# ----------------------- Определение локации по IP -----------------------
def get_location_from_ip():
    """Определяем локацию пользователя по IP. Неточно, но работает как разумный дефолт"""
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return {
            "city": data.get("city"),
            "country": data.get("country_name"),
            "lat": data.get("latitude"),
            "lon": data.get("longitude"),
        }
    except Exception:
        return None


# ----------------------- Боковая панель -----------------------
with st.sidebar:
    # Переключатель языка
    lang_label = st.radio("Language / Язык", options=["Русский", "English"], index=0)
    lang = "ru" if lang_label == "Русский" else "en"

auto_loc = get_location_from_ip()
if auto_loc and auto_loc["city"]:
    default_city = f"{auto_loc['city']}, {auto_loc.get('country', '')}".strip().strip(", ")
else:
    default_city = 'Moscow'

with st.sidebar:
    st.title("⛅ Погода" if lang == "ru" else "⛅ Weather")
    city_query = st.text_input(
        "Город или место" if lang == "ru" else "City or place",
        value=default_city,
    )
    if lang == "ru":
        units_label = st.radio(
            "Единицы измерения температуры",
            options=["Цельсий", "Фаренгейт"],
            horizontal=True,
            index=0,
        )
    else:
        units_label = st.radio(
            "Temperature unit",
            options=["Celsius", "Fahrenheit"],
            horizontal=True,
            index=0,
        )

    show_hourly = st.toggle(
        "Показать почасовой прогноз" if lang == "ru" else "Show hourly forecast",
        value=True,
    )

# Для API задаю единицы измерения температуры
if lang == "ru":
    temp_system = "Fahrenheit" if units_label == "Фаренгейт" else "Celsius"
else:
    temp_system = "Fahrenheit" if units_label == "Fahrenheit" else "Celsius"

# ----------------------- Заголовок страницы -----------------------
if lang == "ru":
    st.title("Прогноз погоды")
    st.caption("Источник данных: Open-Meteo")
else:
    st.title("Weather forecast")
    st.caption("Data source: Open-Meteo")


# ----------------------- Вспомогательные функции -----------------------
# Функция нужна для корректной работы всплывающего списка
@st.cache_data(ttl=3600)
def geocode(query: str, lang_code: str):
    """Возвращает список совпадений с координатами по названию места"""
    if not query:
        return []
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(
        url,
        params={"name": query, "count": 5, "language": lang_code, "format": "json"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json().get("results", []) or []
    places = []
    for p in data:
        label_parts = [p.get("name")]
        if p.get("admin1"):
            label_parts.append(p["admin1"])
        if p.get("country"):
            label_parts.append(p["country"])
        label = ", ".join([x for x in label_parts if x])
        places.append(
            {
                "label": label,
                "lat": p.get("latitude"),
                "lon": p.get("longitude"),
                "tz": p.get("timezone", "UTC"),
            }
        )
    return places


@st.cache_data(ttl=900)
def fetch_weather(lat: float, lon: float, temp_unit: str):
    """Получает текущую погоду, почасовой и недельный прогноз."""
    is_f = temp_unit == "Fahrenheit"
    temp_unit_param = "fahrenheit" if is_f else "celsius"
    wind_unit_param = "mph" if is_f else "kmh"

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "wind_direction_10m",
            "relative_humidity_2m",
            "weather_code",
        ],
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "precipitation",
            "relative_humidity_2m",
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "sunrise",
            "sunset",
            "precipitation_sum",
            "wind_speed_10m_max",
        ],
        "temperature_unit": temp_unit_param,
        "wind_speed_unit": wind_unit_param,
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


# Описания погодных кодов на двух языках, взято на основе данных API
WEATHER_DESCRIPTIONS_RU = {
    0: "Ясно",
    1: "Преимущественно ясно",
    2: "Переменная облачность",
    3: "Пасмурно",
    45: "Туман",
    48: "Туман с изморозью",
    51: "Слабая морось",
    53: "Умеренная морось",
    55: "Сильная морось",
    61: "Слабый дождь",
    63: "Умеренный дождь",
    65: "Сильный дождь",
    71: "Слабый снег",
    73: "Умеренный снег",
    75: "Сильный снег",
    80: "Кратковременные дожди",
    81: "Ливень",
    82: "Сильный ливень",
    95: "Гроза",
    96: "Гроза с небольшим градом",
    97: "Гроза с сильным градом",
}

WEATHER_DESCRIPTIONS_EN = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers (slight)",
    81: "Rain showers (moderate)",
    82: "Rain showers (violent)",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    97: "Thunderstorm with heavy hail",
}

WEATHER_EMOJI = {
    0: "☀️",
    1: "🌤️",
    2: "⛅",
    3: "☁️",
    45: "🌫️",
    48: "🌫️",
    51: "🌦️",
    53: "🌦️",
    55: "🌧️",
    61: "🌧️",
    63: "🌧️",
    65: "🌧️",
    71: "🌨️",
    73: "🌨️",
    75: "❄️",
    80: "🌧️",
    81: "🌧️",
    82: "⛈️",
    95: "⛈️",
    96: "⛈️",
    97: "⛈️",
}


def deg_to_compass(deg):
    # Для компаса
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = int((deg / 45) + 0.5) % 8
    return dirs[ix]


def nice_time(ts, tz_str, lang_code: str):
    """Функция, цель которой привести время в нормальный и понятный для человека формат"""
    try:
        tz = pytz.timezone(tz_str)
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(tz)
        if lang_code == "ru":
            return dt.strftime("%d.%m %H:%M")
        else:
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


# ----------------------- Основной код -----------------------
places = geocode(city_query, lang) # получаем список мест от пользователя
if not places:
    if lang == "ru":
        st.warning("Город не найден. Попробуйте другой запрос, например: «Париж, Франция».")
    else:
        st.warning("No places found. Try a different search, e.g. 'Paris, France'.")
    st.stop()

labels = [p["label"] for p in places]
choice_label = "Выберите местоположение" if lang == "ru" else "Choose a location"
choice = st.selectbox(choice_label, options=labels, index=0) # кладем список мест в окно выбора
place = places[labels.index(choice)]

try:
    data = fetch_weather(place["lat"], place["lon"], temp_system) # пробуем достать данные по погоде
except requests.HTTPError as e:
    if lang == "ru":
        st.error(f"Ошибка API погоды: {e}")
    else:
        st.error(f"Weather API error: {e}")
    st.stop()
except Exception as e:
    if lang == "ru":
        st.error(f"Произошла ошибка: {e}")
    else:
        st.error(f"Something went wrong: {e}")
    st.stop()

tz = data.get("timezone", place["tz"]) 
current = data.get("current", {})
daily = data.get("daily", {})
hourly = data.get("hourly", {})

desc_dict = WEATHER_DESCRIPTIONS_RU if lang == "ru" else WEATHER_DESCRIPTIONS_EN #словарь с описаниями погоды

# ----------------------- Текущие условия -----------------------
c_temp = current.get("temperature_2m")
c_feels = current.get("apparent_temperature")
c_ws = current.get("wind_speed_10m")
c_wd = current.get("wind_direction_10m")
c_rh = current.get("relative_humidity_2m")
c_code = current.get("weather_code", 0)
desc = desc_dict.get(c_code, "—")
emoji = WEATHER_EMOJI.get(c_code, "🌡️")
temp_unit_symbol = "°F" if temp_system == "Fahrenheit" else "°C"
wind_unit_symbol = "mph" if temp_system == "Fahrenheit" else ("км/ч" if lang == "ru" else "km/h")

if lang == "ru":
    st.subheader(f"{emoji} {desc}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Температура", f"{c_temp:.1f}{temp_unit_symbol}")
    col2.metric("Ощущается как", f"{c_feels:.1f}{temp_unit_symbol}")
    col3.metric("Ветер", f"{c_ws:.0f} {wind_unit_symbol} {deg_to_compass(c_wd)}")
    col4.metric("Влажность", f"{c_rh:.0f}%")
else:
    st.subheader(f"{emoji} {desc}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Temperature", f"{c_temp:.1f}{temp_unit_symbol}")
    col2.metric("Feels like", f"{c_feels:.1f}{temp_unit_symbol}")
    col3.metric("Wind", f"{c_ws:.0f} {wind_unit_symbol} {deg_to_compass(c_wd)}")
    col4.metric("Humidity", f"{c_rh:.0f}%")


# ----------------------- Почасовой прогноз -----------------------
if show_hourly and "time" in hourly:
    today_date = daily.get("time", [None])[0]
    hdf = pd.DataFrame(
        {
            "time": hourly.get("time", []),
            "temp": hourly.get("temperature_2m", []),
            "feels_like": hourly.get("apparent_temperature", []),
            "humidity": hourly.get("relative_humidity_2m", []),
            "precip": hourly.get("precipitation", []),
        }
    )
    if today_date:
        hdf = hdf[hdf["time"].str.startswith(today_date)]
    hdf["local_time"] = hdf["time"].apply(lambda x: nice_time(x, tz, lang))

    if lang == "ru":
        st.markdown("### Почасовой прогноз (сегодня)")
        table = hdf[["local_time", "temp", "feels_like", "humidity", "precip"]].rename(
            columns={
                "local_time": "Время",
                "temp": f"Темп. ({temp_unit_symbol})",
                "feels_like": f"Ощущается ({temp_unit_symbol})",
                "humidity": "Влажность (%)",
                "precip": "Осадки (мм)",
            }
        )
    else:
        st.markdown("### Hourly forecast (today)")
        table = hdf[["local_time", "temp", "feels_like", "humidity", "precip"]].rename(
            columns={
                "local_time": "Time",
                "temp": f"Temp ({temp_unit_symbol})",
                "feels_like": f"Feels ({temp_unit_symbol})",
                "humidity": "Humidity (%)",
                "precip": "Precip (mm)",
            }
        )

    st.dataframe(table, use_container_width=True)
    st.line_chart(hdf.set_index("local_time")[["temp"]], height=220)

# ----------------------- Карта осадков (сегодня) -----------------------
if "time" in daily and daily["time"]:
    precip_today = (daily.get("precipitation_sum") or [0])[0] or 0.0

    if lang == "ru":
        st.markdown("### Карта осадков (сегодня)")
        st.caption("Размер маркера отражает количество осадков (мм).")
    else:
        st.markdown("### Precipitation map (today)")
        st.caption("Marker size reflects today's total precipitation (mm).")

    df_map = pd.DataFrame(
        {
            "lat": [place["lat"]],
            "lon": [place["lon"]],
            "precip_today_mm": [precip_today],
            "label": [place["label"]],
        }
    )

    radius_base = 8000
    radius_scale = 4000

    layer = pdk.Layer(
        "ScatterplotLayer",
        df_map,
        get_position="[lon, lat]",
        get_radius=f"precip_today_mm * {radius_scale} + {radius_base}",
        get_fill_color="[30, 144, 255, 160]",
        pickable=True,
    )

    tooltip_text = (
        "{label}\nОсадки: {precip_today_mm} мм"
        if lang == "ru"
        else "{label}\nPrecipitation: {precip_today_mm} mm"
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(
                latitude=place["lat"],
                longitude=place["lon"],
                zoom=6,
                pitch=0,
            ),
            tooltip={"text": tooltip_text},
        )
    )

# ----------------------- 7-дневный прогноз -----------------------
if "time" in daily and daily["time"]:
    fdf = pd.DataFrame(
        {
            "date": daily["time"],
            "code": daily.get("weather_code", []),
            "tmax": daily.get("temperature_2m_max", []),
            "tmin": daily.get("temperature_2m_min", []),
            "precip": daily.get("precipitation_sum", []),
            "windmax": daily.get("wind_speed_10m_max", []),
            "sunrise": daily.get("sunrise", []),
            "sunset": daily.get("sunset", []),
        }
    )
    fdf["desc"] = fdf["code"].map(lambda c: desc_dict.get(c, "—"))
    fdf["emoji"] = fdf["code"].map(lambda c: WEATHER_EMOJI.get(c, "🌡️"))

    if lang == "ru":
        st.markdown("### Прогноз на 7 дней")
    else:
        st.markdown("### 7-day forecast")

    for _, row in fdf.iterrows():
        with st.container(border=True):
            date_str = row["date"]
            sunrise_str = nice_time(row["sunrise"], tz, lang)
            sunset_str = nice_time(row["sunset"], tz, lang)

            if lang == "ru":
                st.markdown(
                    f"**{date_str}**  {row['emoji']} {row['desc']}  "
                    f"| Макс: **{row['tmax']:.1f}{temp_unit_symbol}**  "
                    f"| Мин: **{row['tmin']:.1f}{temp_unit_symbol}**  "
                    f"| Осадки: **{row['precip']:.1f} мм**  "
                    f"| Ветер до: **{row['windmax']:.0f} {wind_unit_symbol}**"
                )
                st.caption(f"🌅 Восход: {sunrise_str} · 🌇 Закат: {sunset_str}")
            else:
                st.markdown(
                    f"**{date_str}**  {row['emoji']} {row['desc']}  "
                    f"| High: **{row['tmax']:.1f}{temp_unit_symbol}**  "
                    f"| Low: **{row['tmin']:.1f}{temp_unit_symbol}**  "
                    f"| Precip: **{row['precip']:.1f} mm**  "
                    f"| Max wind: **{row['windmax']:.0f} {wind_unit_symbol}**"
                )
                st.caption(f"🌅 Sunrise: {sunrise_str} · 🌇 Sunset: {sunset_str}")
else:
    if lang == "ru":
        st.info("Нет данных прогноза для этого местоположения.")
    else:
        st.info("No daily forecast available for this location.")

# ----------------------- Подсказка -----------------------
if lang == "ru":
    st.caption(
        "💡 Подсказка: используйте боковую панель, чтобы изменить город, язык и единицы измерения. "
        "Данные кэшируются для ускорения загрузки."
    )
else:
    st.caption(
        "💡 Tip: use the sidebar to change city, language and units. "
        "Results are cached for faster loading."
    )
