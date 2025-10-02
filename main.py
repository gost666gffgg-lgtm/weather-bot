import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем токены и ключи из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
CITY = os.getenv('CITY', 'Moscow')  # Город по умолчанию - Москва

# Проверяем, что все необходимые переменные загружены
if not all([TELEGRAM_TOKEN, CHAT_ID, WEATHER_API_KEY]):
    raise ValueError("Не все переменные окружения установлены! Проверьте файл .env")


def get_weather(city: str) -> dict:
    """
    Получает данные о погоде из OpenWeatherMap API.
    
    Args:
        city: Название города
        
    Returns:
        Словарь с данными о погоде или None в случае ошибки
    """
    # URL для запроса к API OpenWeatherMap
    url = "http://api.openweathermap.org/data/2.5/weather"
    
    # Параметры запроса
    params = {
        'q': city,  # Название города
        'appid': WEATHER_API_KEY,  # API-ключ
        'units': 'metric',  # Температура в градусах Цельсия
        'lang': 'ru'  # Описание погоды на русском языке
    }
    
    try:
        # Выполняем GET-запрос к API
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Проверяем успешность запроса
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных о погоде: {e}")
        return None


def format_weather_message(weather_data: dict) -> str:
    """
    Форматирует данные о погоде в читаемое сообщение.
    
    Args:
        weather_data: Словарь с данными о погоде из API
        
    Returns:
        Отформатированное сообщение
    """
    if not weather_data:
        return "❌ Не удалось получить данные о погоде."
    
    # Извлекаем необходимые данные
    city_name = weather_data['name']
    temp = weather_data['main']['temp']
    feels_like = weather_data['main']['feels_like']
    description = weather_data['weather'][0]['description'].capitalize()
    humidity = weather_data['main']['humidity']
    wind_speed = weather_data['wind']['speed']
    
    # Формируем красивое сообщение с эмодзи
    message = f"""
🌤 Прогноз погоды для города {city_name}

🌡 Температура: {temp}°C
🤔 Ощущается как: {feels_like}°C
☁️ Описание: {description}
💧 Влажность: {humidity}%
💨 Скорость ветра: {wind_speed} м/с

📅 Дата: {datetime.now().strftime('%d.%m.%Y')}
⏰ Время: {datetime.now().strftime('%H:%M')}
    """
    
    return message.strip()


async def send_weather_update():
    """
    Получает данные о погоде и отправляет их в Telegram.
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Получение прогноза погоды...")
    
    # Получаем данные о погоде
    weather_data = get_weather(CITY)
    
    # Форматируем сообщение
    message = format_weather_message(weather_data)
    
    try:
        # Создаем объект бота
        bot = Bot(token=TELEGRAM_TOKEN)
        
        # Отправляем сообщение
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Сообщение успешно отправлено!")
        
    except TelegramError as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")


async def main():
    """
    Основная функция программы.
    Создает планировщик и запускает отправку прогноза каждый день в 8:00.
    """
    print("🤖 Бот запущен!")
    print(f"📍 Город: {CITY}")
    print(f"⏰ Прогноз будет отправляться ежедневно в 08:00")
    print("-" * 50)
    
    # Создаем асинхронный планировщик
    scheduler = AsyncIOScheduler()
    
    # Добавляем задачу: отправка прогноза каждый день в 8:00
    scheduler.add_job(
        send_weather_update,
        trigger=CronTrigger(hour=8, minute=0),
        id='weather_update',
        name='Отправка прогноза погоды',
        replace_existing=True
    )
    
    # Опционально: отправить прогноз сразу при запуске (для тестирования)
    # Раскомментируйте следующую строку, если хотите получить прогноз сразу
    # await send_weather_update()
    
    # Запускаем планировщик
    scheduler.start()
    
    print("✅ Планировщик запущен. Ожидание следующей отправки...")
    print("Нажмите Ctrl+C для остановки бота")
    
    try:
        # Держим программу запущенной
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Бот остановлен")
        scheduler.shutdown()


if __name__ == "__main__":
    # Запускаем основную функцию
    asyncio.run(main())