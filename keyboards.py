from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎬 Хочу фильм/сериал")],
        [KeyboardButton(text="📚 Хочу книгу")],
        [KeyboardButton(text="⭐ Моё избранное"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

# Кнопки настроения
mood_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="😊 Весёлое", callback_data="mood_весёлое")],
    [InlineKeyboardButton(text="😌 Вдохновляющее", callback_data="mood_вдохновляющее")],
    [InlineKeyboardButton(text="🤔 Загадочное", callback_data="mood_загадочное")],
    [InlineKeyboardButton(text="⚡ Энергичное", callback_data="mood_энергичное")],
    [InlineKeyboardButton(text="💔 Романтическое", callback_data="mood_романтическое")],
    [InlineKeyboardButton(text="🏰 Приключенческое", callback_data="mood_приключенческое")],
    [InlineKeyboardButton(text="📖 Глубокое", callback_data="mood_глубокое")],
    [InlineKeyboardButton(text="🎲 Случайный выбор", callback_data="mood_random")]
])

# Кнопки для карточки рекомендации
def get_recommendation_buttons(content_id: int, user_id: int):
    from database import is_favorite
    fav_status = is_favorite(user_id, content_id)
    
    buttons = [
        [
            InlineKeyboardButton(text="❌ Не нравится", callback_data=f"skip_{content_id}"),
            InlineKeyboardButton(text="💾 Сохранить" if not fav_status else "❤️ В избранном", 
                                callback_data=f"save_{content_id}" if not fav_status else "already_fav")
        ],
        [InlineKeyboardButton(text="📖 Подробнее", callback_data=f"details_{content_id}")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Кнопки для избранного
def get_favorite_buttons(content_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Удалить из избранного", callback_data=f"remove_fav_{content_id}")],
        [InlineKeyboardButton(text="📖 Подробнее", callback_data=f"details_{content_id}")]
    ])

# Кнопка возврата
back_to_main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
])