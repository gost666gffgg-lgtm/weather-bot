
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Загрузка переменных окружения
load_dotenv()

# Получение токенов из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
CITY = os.getenv('CITY', 'Moscow')

# Проверка наличия всех необходимых переменных
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен! Добавьте его в файл .env")
if not CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID не установлен! Добавьте его в файл .env")
if not WEATHER_API_KEY:
    raise ValueError("OPENWEATHER_API_KEY не установлен! Добавьте его в файл .env")

# Создание приложения Telegram
application = Application.builder().token(TELEGRAM_TOKEN).build()

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = """
🤖 Добро пожаловать в Погодный Бот!

Я предоставляю актуальную информацию о погоде.

📋 Доступные команды:
/start - показать это сообщение
/weather - получить текущую погоду

📍 Автоматическая отправка прогноза каждый день в 08:00
    """
    await update.message.reply_text(welcome_message.strip())

async def weather_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /weather"""
    try:
        weather_data = get_weather(CITY)
        
        if weather_data:
            message = format_weather_message(weather_data)
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Не удалось получить данные о погоде. Попробуйте позже.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

def get_weather(city: str) -> dict:
    """
    Получает данные о погоде из OpenWeatherMap API
    """
    url = "http://api.openweathermap.org/data/2.5/weather"
    
    params = {
        'q': city,
        'appid': WEATHER_API_KEY,
        'units': 'metric',
        'lang': 'ru'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных о погоде: {e}")
        return None

def format_weather_message(weather_data: dict) -> str:
    """
    Форматирует данные о погоде в читаемое сообщение
    """
    if not weather_data:
        return "❌ Не удалось получить данные о погоде."

    city_name = weather_data['name']
    temp = round(weather_data['main']['temp'])
    feels_like = round(weather_data['main']['feels_like'])
    description = weather_data['weather'][0]['description'].capitalize()
    humidity = weather_data['main']['humidity']
    wind_speed = weather_data['wind']['speed']

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
    Автоматическая отправка прогноза погоды
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Получение прогноза погоды...")

    weather_data = get_weather(CITY)
    message = format_weather_message(weather_data)

    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Сообщение успешно отправлено!")

    except TelegramError as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")

async def main():
    """
    Основная функция запуска бота
    """
    print("🤖 Погодный бот запущен!")
    print(f"📍 Город: {CITY}")
    print(f"⏰ Прогноз будет отправляться ежедневно в 08:00")
    print("-" * 50)

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("weather", weather_handler))

    # Инициализация и запуск приложения
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Настройка планировщика для ежедневной отправки
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_weather_update,
        trigger=CronTrigger(hour=8, minute=0),
        id='weather_update',
        name='Ежедневная отправка прогноза погоды',
        replace_existing=True
    )
    scheduler.start()

    print("✅ Планировщик запущен. Ожидание следующей отправки...")
    print("✅ Обработчик команд /start и /weather активен!")
    print("Нажмите Ctrl+C для остановки бота")

    try:
        # Бесконечный цикл для поддержания работы бота
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Остановка бота...")
        scheduler.shutdown()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        print("✅ Бот успешно остановлен")

if __name__ == "__main__":
    asyncio.run(main())