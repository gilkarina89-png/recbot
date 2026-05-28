import sqlite3
import logging
logging.basicConfig(level=logging.DEBUG)
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# Состояния
class RecommendationState(StatesGroup):
    waiting_for_mood = State()

# ========== КОМАНДЫ ==========

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    db.register_user(user_id, username)
    await state.clear()
    
    await message.answer(
        "🎬 *Добро пожаловать в RecommenderBot!*\n\n"
        "Я помогу выбрать фильм или книгу.\n\n"
        "Просто нажми на кнопку ниже!",
        parse_mode="Markdown",
        reply_markup=kb.main_menu
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ *Как работает бот:*\n\n"
        "1. Нажми «Хочу фильм/сериал» или «Хочу книгу»\n"
        "2. Выбери настроение\n"
        "3. Получи рекомендацию\n\n"
        "Кнопки под рекомендацией:\n"
        "• 💾 Сохранить — добавить в избранное\n"
        "• ❌ Не нравится — другой вариант\n"
        "• 📖 Подробнее — ссылка на источник\n\n"
        "⭐ «Моё избранное» — список сохранённого",
        parse_mode="Markdown"
    )

# ========== ГЛАВНЫЕ КНОПКИ МЕНЮ ==========

@router.message(F.text == "🎬 Хочу фильм/сериал")
async def want_movie(message: Message, state: FSMContext):
    await state.update_data(content_type="movie")
    await state.set_state(RecommendationState.waiting_for_mood)
    await message.answer(
        "🎭 *Какое у тебя настроение?*",
        parse_mode="Markdown",
        reply_markup=kb.mood_buttons
    )

@router.message(F.text == "📚 Хочу книгу")
async def want_book(message: Message, state: FSMContext):
    await state.update_data(content_type="book")
    await state.set_state(RecommendationState.waiting_for_mood)
    await message.answer(
        "📖 *Какое настроение хочешь от книги?*",
        parse_mode="Markdown",
        reply_markup=kb.mood_buttons
    )

@router.message(F.text == "⭐ Моё избранное")
async def show_favorites(message: Message):
    user_id = message.from_user.id
    favorites = db.get_favorites(user_id)
    
    if not favorites:
        await message.answer(
            "⭐ *Избранное пусто*\n\n"
            "Сохраняй понравившиеся рекомендации кнопкой «Сохранить»!",
            parse_mode="Markdown"
        )
        return
    
    await message.answer("⭐ *Твои сохранённые рекомендации:*", parse_mode="Markdown")
    
    for item in favorites:
        type_emoji = "🎬" if item["type"] == "movie" else "📚"
        text = (
            f"{type_emoji} *{item['title']}*\n"
            f"📁 Жанр: {item['genre']}\n\n"
            f"📝 {item['description']}"
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=kb.get_favorite_buttons(item["id"]))

@router.message(F.text == "❓ Помощь")
async def help_button(message: Message):
    await cmd_help(message)

# ========== ВЫБОР НАСТРОЕНИЯ ==========

@router.callback_query(RecommendationState.waiting_for_mood, F.data.startswith("mood_"))
async def process_mood(callback: CallbackQuery, state: FSMContext):
    mood = callback.data.replace("mood_", "")
    if mood == "random":
        mood = None
    
    user_data = await state.get_data()
    content_type = user_data.get("content_type", "movie")
    
    # Получаем рекомендацию
    recommendation = db.get_recommendation(content_type, mood)
    
    if not recommendation:
        await callback.message.edit_text(
            "😔 *Ничего не нашлось по твоим критериям.*\n\nПопробуй другое настроение!",
            parse_mode="Markdown",
            reply_markup=kb.mood_buttons
        )
        await callback.answer()
        return
    
    # Сохраняем данные в состояние
    await state.update_data(
        current_recommendation_id=recommendation["id"],
        current_recommendation=recommendation,
        current_mood=mood
    )
    
    # Увеличиваем счётчик
    db.increment_recommendations(callback.from_user.id)
    
    # Отправляем карточку
    await send_card(callback.message, recommendation, callback.from_user.id)
    await callback.answer()

# ========== КНОПКА "НЕ НРАВИТСЯ" (SKIP) ==========

@router.callback_query(F.data.startswith("skip_"))
async def skip_recommendation(callback: CallbackQuery, state: FSMContext):
    logger.info(f"SKIP button pressed! data={callback.data}")
    
    user_data = await state.get_data()
    content_type = user_data.get("content_type", "movie")
    mood = user_data.get("current_mood")
    
    logger.info(f"Looking for new: content_type={content_type}, mood={mood}")
    
    # Получаем новую рекомендацию
    recommendation = db.get_recommendation(content_type, mood)
    
    if not recommendation:
        await callback.message.edit_text(
            "😔 *Не удалось найти другую рекомендацию.*\n\nВыбери другое настроение!",
            parse_mode="Markdown",
            reply_markup=kb.mood_buttons
        )
        await callback.answer()
        return
    
    await state.update_data(
        current_recommendation_id=recommendation["id"],
        current_recommendation=recommendation
    )
    
    await send_card(callback.message, recommendation, callback.from_user.id)
    await callback.answer("🔄 Другая рекомендация")

# ========== КНОПКА "СОХРАНИТЬ" ==========

@router.callback_query(F.data.startswith("save_"))
async def save_recommendation(callback: CallbackQuery, state: FSMContext):
    content_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    success = db.save_to_favorites(user_id, content_id)
    
    if success:
        await callback.answer("✅ Сохранено в избранное!", show_alert=True)
        # Обновляем кнопки
        await update_card_buttons(callback.message, content_id, user_id)
    else:
        await callback.answer("❌ Не удалось сохранить", show_alert=True)

# ========== КНОПКА "ПОДРОБНЕЕ" ==========

@router.callback_query(F.data.startswith("details_"))
async def show_details(callback: CallbackQuery):
    content_id = int(callback.data.split("_")[1])
    
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, external_link FROM content WHERE id = ?", (content_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[1]:
        title, link = result
        await callback.answer()
        await callback.message.answer(
            f"🔗 *{title}*\n\nПодробнее: {link}",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await callback.answer("Ссылка не найдена", show_alert=True)

# ========== УДАЛЕНИЕ ИЗ ИЗБРАННОГО ==========

@router.callback_query(F.data.startswith("remove_fav_"))
async def remove_favorite(callback: CallbackQuery):
    content_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    db.remove_from_favorites(user_id, content_id)
    await callback.answer("🗑️ Удалено из избранного", show_alert=True)
    await callback.message.delete()

# ========== ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ==========

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("🏠 Главное меню:", reply_markup=kb.main_menu)
    await callback.answer()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def send_card(message: Message, recommendation: dict, user_id: int):
    type_emoji = "🎬" if recommendation["type"] == "movie" else "📚"
    type_text = "Фильм/Сериал" if recommendation["type"] == "movie" else "Книга"
    
    mood_emoji = {
        "весёлое": "😊", "вдохновляющее": "😌", "загадочное": "🤔",
        "энергичное": "⚡", "романтическое": "💔", "приключенческое": "🏰",
        "глубокое": "📖"
    }.get(recommendation.get("mood", ""), "🎭")
    
    card_text = (
        f"{type_emoji} *{recommendation['title']}*\n\n"
        f"📁 *Тип:* {type_text}\n"
        f"{mood_emoji} *Настроение:* {recommendation.get('mood', 'любое')}\n"
        f"🎭 *Жанр:* {recommendation['genre']}\n\n"
        f"📖 *О чём:*\n{recommendation['description']}"
    )
    
    # Проверяем, редактируем мы или отправляем новое
    try:
        await message.edit_text(
            card_text,
            parse_mode="Markdown",
            reply_markup=kb.get_recommendation_buttons(recommendation["id"], user_id)
        )
    except Exception as e:
        # Если не отредактировалось — отправляем новое
        await message.answer(
            card_text,
            parse_mode="Markdown",
            reply_markup=kb.get_recommendation_buttons(recommendation["id"], user_id)
        )

async def update_card_buttons(message: Message, content_id: int, user_id: int):
    try:
        await message.edit_reply_markup(
            reply_markup=kb.get_recommendation_buttons(content_id, user_id)
        )
    except Exception as e:
        logger.error(f"Не удалось обновить кнопки: {e}")
