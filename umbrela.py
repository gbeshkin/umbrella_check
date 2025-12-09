import asyncio
import logging
import requests

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart

API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


def geocode_city(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json",
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    if "results" not in data or not data["results"]:
        return None
    first = data["results"][0]
    return first["latitude"], first["longitude"], first.get("name")


def get_rain_forecast(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability",
        "forecast_days": 1,
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    hourly = data.get("hourly", {})
    return list(
        zip(
            hourly.get("time", []),
            hourly.get("precipitation", []),
            hourly.get("precipitation_probability", []),
        )
    )


def need_umbrella(hourly_data, hours_ahead: int = 6):
    for _, precipitation, probability in hourly_data[:hours_ahead]:
        if (probability and probability >= 30) or (precipitation and precipitation > 0):
            return True
    return False


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Hi! ☂️\n"
        "Send me a city name and I’ll tell you whether you need an umbrella or not.\n"
        "Example: Tallinn"
    )


@dp.message()
async def umbrella_check(message: Message):
    city = message.text.strip()

    geo = geocode_city(city)
    if not geo:
        await message.answer("I can’t find this city 🤔")
        return

    lat, lon, name = geo
    hourly = get_rain_forecast(lat, lon)
    umbrella = need_umbrella(hourly)

    if umbrella:
        await message.answer(
            f"In {name}, rain is possible in the next few hours 🌧\n"
            f"Advice: take an umbrella!"
        )
    else:
        await message.answer(
            f"No rain expected in {name} 🙂\n"
            f"You can go out without an umbrella."
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
