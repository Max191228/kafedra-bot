import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения!")
    sys.exit(1)

# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Хранилище состояния (можно заменить на Redis/BД)
user_states = {}


# === Обработчики команд ===

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = message.from_user
    logger.info(f"Пользователь {user.id} (@{user.username}) запустил бота")

    await message.answer(
        f"👋 Привет, {user.first_name}!\n"
        f"Я бот, работающий в постоянном режиме.\n\n"
        f"Доступные команды:\n"
        f"/help - помощь\n"
        f"/status - статус бота\n"
        f"/info - информация"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "🆘 <b>Помощь</b>\n\n"
        "Я работаю в режиме реального времени и всегда онлайн.\n\n"
        "Команды:\n"
        "• /start - начать работу\n"
        "• /help - это сообщение\n"
        "• /status - проверить статус\n"
        "• /info - информация о боте\n"
        "• /time - текущее время сервера"
    )


@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Проверка статуса бота"""
    uptime = datetime.now() - start_time if 'start_time' in globals() else "неизвестно"
    await message.answer(
        f"✅ <b>Бот работает</b>\n\n"
        f"Режим: постоянный (long polling)\n"
        f"Время работы: {uptime}\n"
        f"Пользователей в памяти: {len(user_states)}"
    )


@dp.message(Command("info"))
async def cmd_info(message: Message):
    """Информация о боте"""
    await message.answer(
        "🤖 <b>Информация о боте</b>\n\n"
        "Версия: 1.0.0\n"
        "Библиотека: aiogram 3.x\n"
        "Тип: Long-polling бот\n"
        "Статус: 🟢 Онлайн"
    )


@dp.message(Command("time"))
async def cmd_time(message: Message):
    """Текущее время сервера"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await message.answer(f"🕐 Серверное время: {current_time}")


@dp.message()
async def echo_message(message: Message):
    """Обработчик всех остальных сообщений"""
    if message.text:
        await message.answer(
            f"Вы написали: {message.text}\n\n"
            f"Используйте /help для списка команд."
        )
    else:
        await message.answer("Я понимаю только текстовые сообщения.")


# === Обработка ошибок ===

@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления {update}: {exception}", exc_info=True)
    return True


# === Запуск бота ===

async def on_startup():
    """Действия при запуске бота"""
    logger.info("=" * 50)
    logger.info("Бот запускается...")
    logger.info(f"ADMIN_ID: {ADMIN_ID}")
    logger.info(f"Время запуска: {datetime.now()}")
    logger.info("=" * 50)

    # Отправка уведомления админу
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🚀 <b>Бот запущен!</b>\n"
                f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Режим: постоянная работа"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Бот останавливается...")

    # Закрытие всех соединений
    await bot.session.close()

    # Очистка ресурсов
    user_states.clear()

    # Отправка уведомления админу
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🛑 <b>Бот остановлен</b>\n"
                f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except:
            pass

    logger.info("Бот остановлен")


async def main():
    """Главная функция запуска"""
    # Регистрация хуков запуска/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запоминаем время старта
    global start_time
    start_time = datetime.now()

    try:
        # Запуск поллинга (постоянная работа)
        logger.info("Старт polling (постоянный режим)...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            skip_updates=True  # Пропустить накопившиеся обновления
        )
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}", exc_info=True)
        sys.exit(1)
