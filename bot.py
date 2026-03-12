#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'bot_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== ЗАГРУЗКА КОНФИГУРАЦИИ ====================
# Загружаем переменные из .env (для локальной разработки)
load_dotenv()

# Приоритет: сначала переменные окружения (Amvera), потом .env файл
TOKEN = os.environ.get('BOT_TOKEN') or os.getenv('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID') or os.getenv('ADMIN_ID')

# Проверка токена
if not TOKEN:
    logger.error("Токен не найден! Проверьте переменные окружения (Amvera) или файл .env")
    sys.exit(1)

# Проверка и преобразование ADMIN_ID
if not ADMIN_ID:
    logger.error("ADMIN_ID не найден! Проверьте переменные окружения (Amvera) или файл .env")
    sys.exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    logger.error(f"ADMIN_ID должен быть числом! Получено: {ADMIN_ID}")
    sys.exit(1)

logger.info(f"Бот запускается. ADMIN_ID: {ADMIN_ID}")

# ==================== РАБОТА С ФАЙЛАМИ ====================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
VOTES_FILE = DATA_DIR / "votes.json"


def load_users():
    """Загружает список пользователей из файла"""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            logger.error("Ошибка загрузки users.json")
            return [ADMIN_ID]
    return [ADMIN_ID]


def save_users(users_list):
    """Сохраняет список пользователей в файл"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_list, f, ensure_ascii=False, indent=2)


def load_votes():
    """Загружает голосования из файла"""
    if VOTES_FILE.exists():
        try:
            with open(VOTES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            logger.error("Ошибка загрузки votes.json")
            return {}
    return {}


def save_votes(votes_dict):
    """Сохраняет голосования в файл"""
    with open(VOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(votes_dict, f, ensure_ascii=False, indent=2)


# Загружаем данные
users = load_users()
votes = load_votes()

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ==================== ХЭНДЛЕРЫ (ОБРАБОТЧИКИ КОМАНД) ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "без username"

    logger.info(f"Команда /start от пользователя {user_id} (@{username})")

    if user_id not in users:
        await message.answer(
            f"👋 Здравствуйте!\n\n"
            f"Ваш ID: <code>{user_id}</code>\n"
            f"Ваш username: @{username}\n\n"
            f"Для доступа к боту сообщите ваш ID администратору."
        )
        return

    await message.answer(
        f"👋 <b>Бот голосований кафедры</b>\n\n"
        f"<b>Доступные команды:</b>\n"
        f"📊 /newvote [вопрос] - создать голосование (админ)\n"
        f"👥 /adduser [id] - добавить пользователя (админ)\n"
        f"📋 /users - список пользователей (админ)\n"
        f"📈 /stats - статистика голосований"
    )


@dp.message(Command("adduser"))
async def cmd_add_user(message: Message):
    """Добавление нового пользователя"""
    user_id = message.from_user.id
    logger.info(f"Команда /adduser от пользователя {user_id}")

    if user_id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав на эту команду.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Формат: /adduser [ID_пользователя]\n\nПример: /adduser 123456789")
            return

        new_user_id = int(parts[1])

        if new_user_id in users:
            await message.answer(f"⚠️ Пользователь {new_user_id} уже есть в списке.")
            return

        users.append(new_user_id)
        save_users(users)

        logger.info(f"Пользователь {new_user_id} добавлен администратором {user_id}")
        await message.answer(f"✅ Пользователь {new_user_id} добавлен в список доступа.")

        # Отправляем уведомление новому пользователю
        try:
            await bot.send_message(
                new_user_id,
                "🎉 Вам открыт доступ к боту голосований кафедры!\n\nНажмите /start для начала работы."
            )
        except:
            logger.warning(f"Не удалось отправить уведомление пользователю {new_user_id}")

    except ValueError:
        await message.answer("❌ Ошибка: ID должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка в adduser: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("users"))
async def cmd_users(message: Message):
    """Список пользователей"""
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        await message.answer("⛔ Нет прав.")
        return

    user_list = []
    for uid in users:
        try:
            chat = await bot.get_chat(uid)
            name = chat.full_name or "без имени"
            user_list.append(f"• <code>{uid}</code> - {name}")
        except:
            user_list.append(f"• <code>{uid}</code> - (недоступен)")

    text = f"📋 <b>Список пользователей ({len(users)}):</b>\n\n" + "\n".join(user_list)
    await message.answer(text)


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика голосований"""
    user_id = message.from_user.id

    if user_id not in users:
        await message.answer("⛔ Нет доступа.")
        return

    total_votes = len(votes)
    active_votes = len([v for v in votes.values() if v.get('active', False)])
    completed_votes = total_votes - active_votes

    total_participations = 0
    for v in votes.values():
        total_participations += len(v.get('voted_users', []))

    await message.answer(
        f"📊 <b>Статистика голосований</b>\n\n"
        f"• Всего создано: {total_votes}\n"
        f"• Активных: {active_votes}\n"
        f"• Завершённых: {completed_votes}\n"
        f"• Всего голосов отдано: {total_participations}"
    )


@dp.message(Command("newvote"))
async def cmd_new_vote(message: Message):
    """Создание нового голосования"""
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        await message.answer("⛔ Нет прав.")
        return

    # Получаем вопрос голосования
    vote_text = message.text.replace('/newvote', '').strip()
    if not vote_text:
        await message.answer(
            "❌ Напишите вопрос после команды.\n\n"
            "Пример: /newvote Переносим пару на завтра?"
        )
        return

    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ ЗА", callback_data="vote_yes")
    builder.button(text="❌ ПРОТИВ", callback_data="vote_no")
    builder.button(text="🤷 ВОЗДЕРЖУСЬ", callback_data="vote_abstain")
    builder.adjust(3)

    # Уникальный ID голосования
    vote_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    votes[vote_id] = {
        'id': vote_id,
        'question': vote_text,
        'yes': 0,
        'no': 0,
        'abstain': 0,
        'voted_users': [],
        'creator_id': user_id,
        'created_at': datetime.now().isoformat(),
        'active': True
    }

    save_votes(votes)
    logger.info(f"Создано голосование {vote_id}: {vote_text}")

    # Рассылаем всем пользователям
    success_count = 0
    fail_count = 0

    for uid in users:
        try:
            await bot.send_message(
                uid,
                f"📢 <b>НОВОЕ ГОЛОСОВАНИЕ</b>\n\n"
                f"❓ <b>Вопрос:</b> {vote_text}\n\n"
                f"Выберите вариант ответа:",
                reply_markup=builder.as_markup()
            )
            success_count += 1
            await asyncio.sleep(0.05)  # Небольшая задержка чтобы не флудить
        except Exception as e:
            logger.warning(f"Не удалось отправить пользователю {uid}: {e}")
            fail_count += 1

    await message.answer(
        f"✅ <b>Голосование создано!</b>\n\n"
        f"📨 Отправлено: {success_count}\n"
        f"❌ Не доставлено: {fail_count}\n"
        f"🆔 ID: {vote_id}"
    )


@dp.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: CallbackQuery):
    """Обработка голосования"""
    user_id = callback.from_user.id

    logger.info(f"Голосование от пользователя {user_id}")

    # Проверка доступа
    if user_id not in users:
        await callback.answer("⛔ У вас нет доступа к голосованию.", show_alert=True)
        return

    # Находим активные голосования
    active_votes = {vid: vdata for vid, vdata in votes.items() if vdata.get('active', False)}

    if not active_votes:
        await callback.answer("📭 Сейчас нет активных голосований.", show_alert=True)
        return

    # Берем последнее активное голосование
    vote_id = list(active_votes.keys())[-1]
    vote_data = votes[vote_id]

    # Проверка на повторное голосование
    if user_id in vote_data['voted_users']:
        await callback.answer("⚠️ Вы уже голосовали!", show_alert=True)
        return

    # Определяем голос
    vote_value = callback.data.split('_')[1]

    if vote_value == 'yes':
        vote_data['yes'] += 1
        result_text = "ЗА"
    elif vote_value == 'no':
        vote_data['no'] += 1
        result_text = "ПРОТИВ"
    else:
        vote_data['abstain'] += 1
        result_text = "ВОЗДЕРЖАЛСЯ"

    vote_data['voted_users'].append(user_id)
    save_votes(votes)

    # Подтверждение
    await callback.answer(f"✅ Ваш голос '{result_text}' принят!")

    # Редактируем сообщение
    try:
        await callback.message.edit_text(
            f"📊 <b>Голосование:</b> {vote_data['question']}\n\n"
            f"✅ Ваш голос: <b>{result_text}</b>\n"
            f"🙏 Спасибо за участие!",
            reply_markup=None
        )
    except:
        pass  # Сообщение могло быть уже изменено

    logger.info(f"Пользователь {user_id} проголосовал {result_text} в {vote_id}")

    # Проверка на завершение (если все проголосовали)
    if len(vote_data['voted_users']) >= len(users):
        await finish_vote(vote_id)


async def finish_vote(vote_id):
    """Завершение голосования"""
    if vote_id not in votes:
        return

    vote_data = votes[vote_id]
    if not vote_data.get('active', False):
        return

    vote_data['active'] = False
    vote_data['finished_at'] = datetime.now().isoformat()
    save_votes(votes)

    total_voted = len(vote_data['voted_users'])

    # Определяем результат
    if vote_data['yes'] > vote_data['no']:
        winner = "✅ РЕШЕНИЕ ПРИНЯТО (победило 'ЗА')"
    elif vote_data['no'] > vote_data['yes']:
        winner = "❌ РЕШЕНИЕ ОТКЛОНЕНО (победило 'ПРОТИВ')"
    else:
        winner = "🤷 РЕШЕНИЕ НЕ ПРИНЯТО (равное количество голосов)"

    result_text = (
        f"📊 <b>ГОЛОСОВАНИЕ ЗАВЕРШЕНО</b>\n\n"
        f"<b>Вопрос:</b> {vote_data['question']}\n\n"
        f"✅ <b>За:</b> {vote_data['yes']}\n"
        f"❌ <b>Против:</b> {vote_data['no']}\n"
        f"🤷 <b>Воздержались:</b> {vote_data['abstain']}\n"
        f"👥 <b>Проголосовало:</b> {total_voted} из {len(users)}\n\n"
        f"<b>Итог:</b> {winner}"
    )

    # Рассылаем результаты
    for uid in users:
        try:
            await bot.send_message(uid, result_text)
            await asyncio.sleep(0.05)
        except:
            pass

    logger.info(f"Голосование {vote_id} завершено")


# ==================== ЗАПУСК БОТА ====================

async def main():
    """Постоянный запуск бота для Amvera"""
    logger.info("Запуск бота в режиме long polling")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("ЗАПУСК БОТА (постоянная работа)")
    logger.info("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
