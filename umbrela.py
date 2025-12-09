import os
import logging
import asyncio
import requests

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not API_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment variables")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)



def geocode_city(city: str):

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json",
    }
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    if "results" not in data or not data["results"]:
        return None
    first = data["results"][0]
    return first["latitude"], first["longitude"], first.get("name", city)


def get_rain_forecast(lat: float, lon: float):

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability",
        "forecast_days": 1,
        "timezone": "auto",
    }
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precip = hourly.get("precipitation", [])
    prob = hourly.get("precipitation_probability", [])

    return list(zip(times, precip, prob))


def need_umbrella(hourly_data, hours_ahead: int = 6):
    
    if not hourly_data:
        return None

    subset = hourly_data[:hours_ahead]
    for time_str, precipitation, probability in subset:
        if (probability is not None and probability >= 30) or (
            precipitation is not None and precipitation > 0
        ):
            return True
    return False



@router.message(F.text.startswith(("/start", "/help")))
async def send_welcome(message: Message):
    await message.answer(
        "Hi! I am your umbrella bot ☔\n"
        "Send me a city name and I’ll tell you if you should take an umbrella.\n\n"
        "Examples:\n"
        "  Tallinn\n"
        "  Riga\n"
        "  London"
    )


@router.message()
async def check_umbrella(message: Message):
    city = message.text.strip()

    geo = geocode_city(city)
    if not geo:
        await message.answer(
            "I can’t find this city 🤔\n"
            "Please check the spelling and try again."
        )
        return

    lat, lon, nice_name = geo

    try:
        hourly = get_rain_forecast(lat, lon)
    except Exception as e:
        logging.exception("Error fetching weather: %s", e)
        await message.answer("I couldn’t get the weather now 😢 Please try again later.")
        return

    decision = need_umbrella(hourly, hours_ahead=6)
    if decision is None:
        await message.answer("Something went wrong with the forecast 😕")
        return

    if decision:
        await message.answer(
            f"In {nice_name} there is a chance of rain in the next 6 hours 🌧\n"
            f"Better take an umbrella!"
        )
    else:
        await message.answer(
            f"In {nice_name} no rain is expected in the next 6 hours 🙂\n"
            f"You can go without an umbrella."
        )


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
