import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest
import sqlite3
import os

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка базы данных
def setup_database():
    """Создание и настройка базы данных SQLite"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        profile TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hackathons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        prizes TEXT,
        registration TEXT,
        duration TEXT,
        link TEXT,
        telegram_chat TEXT,
        comments TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS participations (
        user_id INTEGER,
        hackathon_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (hackathon_id) REFERENCES hackathons (id),
        PRIMARY KEY (user_id, hackathon_id)
    )
    ''')
    
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    
    welcome_message = (
        f"Добро пожаловать, {user.mention_html()}!\n\n"
        "Я бот для поиска участников хакатонов. Чем могу помочь?\n\n"
        "Вот что я умею:\n"
        "• Помогу создать ваш профиль участника\n"
        "• Покажу список доступных хакатонов\n"
        "• Помогу найти участников для вашей команды\n\n"
        "Используйте кнопки меню для навигации.\n\n"
        "Присоединяйтесь к нашему сообществу, чтобы быть в курсе всех событий и находить единомышленников!"
    )
    keyboard = [
        [InlineKeyboardButton("Присоединиться к сообществу", url="https://t.me/+NFdlhMAaN3xmNWMy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(welcome_message, reply_markup=reply_markup)
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать главное меню"""
    keyboard = [
        [InlineKeyboardButton("Мой профиль", callback_data='view_profile')],
        [InlineKeyboardButton("Просмотр хакатонов", callback_data='view_hackathons')],
        [InlineKeyboardButton("Мои хакатоны", callback_data='my_hackathons')],
        [InlineKeyboardButton("Поиск участников", callback_data='search_participants')]  # Новая кнопка
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    menu_message = (
        "Главное меню:\n\n"
        "• Мой профиль - создайте или отредактируйте свой профиль участника\n"
        "• Просмотр хакатонов - узнайте о доступных хакатонах и присоединяйтесь к ним\n"
        "• Мои хакатоны - просмотрите хакатоны, в которых вы участвуете\n"
        "• Поиск участников - найдите участников для вашей команды"  # Новое описание
    )
    
    try:
        if update.message:
            await update.message.reply_text(menu_message, reply_markup=reply_markup)
        else:
            await update.callback_query.message.edit_text(menu_message, reply_markup=reply_markup)
    except BadRequest as e:
        if str(e) == "Message is not modified":
            pass
        else:
            raise

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()

    try:
        if query.data == 'prev_participant':
            context.user_data['current_participant'] = max(0, context.user_data['current_participant'] - 1)
            await show_participant(update, context)
        elif query.data == 'next_participant':
            context.user_data['current_participant'] += 1
            await show_participant(update, context)
        elif query.data == 'view_profile':
            await view_profile(update, context)
        elif query.data == 'edit_profile':
            await edit_profile(update, context)
        elif query.data == 'create_profile':
            await create_profile(update, context)
        elif query.data == 'view_hackathons':
            await view_hackathons(update, context)
        elif query.data == 'my_hackathons':
            await view_my_hackathons(update, context)
        elif query.data == 'prev_hackathon':
            context.user_data['current_hackathon'] = (context.user_data['current_hackathon'] - 1) % len(context.user_data['hackathons'])
            await show_hackathon(update, context)
        elif query.data == 'next_hackathon':
            context.user_data['current_hackathon'] = (context.user_data['current_hackathon'] + 1) % len(context.user_data['hackathons'])
            await show_hackathon(update, context)
        elif query.data.startswith('participate_'):
            hackathon_id = int(query.data.split('_')[1])
            await participate_hackathon(update, context, hackathon_id)
        elif query.data.startswith('look_for_members_'):
            hackathon_id = int(query.data.split('_')[3])
            await look_for_members(update, context, hackathon_id)
        elif query.data == 'main_menu':
            await show_main_menu(update, context)
        elif query.data == 'search_participants':
            await search_participants(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке нажатия кнопки: {e}")
        await query.message.edit_text("Произошла ошибка. Пожалуйста, попробуйте еще раз.")
        await show_main_menu(update, context)

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать профиль пользователя"""
    user_id = update.effective_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT profile FROM users WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    if profile:
        message = f"Ваш текущий профиль:\n\n{profile[0]}\n\nХотите отредактировать свой профиль?"
        keyboard = [[InlineKeyboardButton("Редактировать профиль", callback_data='edit_profile')]]
    else:
        message = "У вас еще нет профиля. Создайте его, чтобы другие участники могли узнать о ваших навыках и интересах."
        keyboard = [[InlineKeyboardButton("Создать профиль", callback_data='create_profile')]]

    keyboard.append([InlineKeyboardButton("Вернуться в меню", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(message, reply_markup=reply_markup)

async def create_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало роцесса создания профиля"""
    instructions = (
        "Пожалуйста, ведите информацию для вашего профиля. Включите следующее:\n\n"
        "1. Ваше имя\n"
        "2. Ваши навыки и опыт\n"
        "3. Интересующие с области в IT\n"
        "4. Любую дополнительную информацию, которую вы хотите сообщить\n\n"
        "Пример:\n"
        "Анна Иванова\n"
        "Навыки: Python, JavaScript, UI/UX дизайн\n"
        "Опыт: 2 года веб-разработки\n"
        "Интересы: Machine Learning, Blockchain\n"
        "Доп. инфо: Люблю работать в команде, открыта для новых идей"
    )
    await update.callback_query.message.edit_text(instructions)
    context.user_data['expecting_profile'] = True

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало процесса редактирования профиля"""
    user_id = update.effective_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT profile FROM users WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()

    instructions = (
        "Ваш текущий профиль:\n\n"
        f"{profile[0]}\n\n"
        "Пожалуйста, введите новую информацию для вашего профиля, сохраняя структуру:\n"
        "1. Ваше имя\n"
        "2. Ваши навыки и опыт\n"
        "3. Интересующие вас области в IT\n"
        "4. Любую дополнительную информацию\n\n"
        "Или нажмите 'Отмена', чтобы вернуться в меню."
    )
    keyboard = [[InlineKeyboardButton("Отмена", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(instructions, reply_markup=reply_markup)
    context.user_data['expecting_profile'] = True

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохранение профиля пользователя"""
    user_id = update.effective_user.id
    profile_text = update.message.text
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, username, profile) VALUES (?, ?, ?)",
                   (user_id, update.effective_user.username, profile_text))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("Ваш профиль был успешно сохранен! Теперь другие участники смогут узнать о ваших навыках и интересах.")
    context.user_data['expecting_profile'] = False
    await show_main_menu(update, context)

async def view_hackathons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получение списка хакатонов из базы данных"""
    user_id = update.effective_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.id, h.name, h.prizes, h.registration, h.duration, h.link, h.telegram_chat, h.comments, COUNT(p.user_id) as participant_count
        FROM hackathons h
        LEFT JOIN participations p ON h.id = p.hackathon_id
        WHERE h.id NOT IN (SELECT hackathon_id FROM participations WHERE user_id = ?)
        GROUP BY h.id
    """, (user_id,))
    hackathons = cursor.fetchall()
    conn.close()
    
    if not hackathons:
        await update.callback_query.message.edit_text(
            "На данный момент нет доступных хакатонов, в которых вы еще не участвуете. Проверьте позже или посмотрите свои текущие хакатоны.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Мои хакатоны", callback_data='my_hackathons')],
                                               [InlineKeyboardButton("Вернуться в меню", callback_data='main_menu')]])
        )
        return
    
    context.user_data['current_hackathon'] = 0
    context.user_data['hackathons'] = hackathons
    await show_hackathon(update, context)

async def view_my_hackathons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать хакатоны, в которых учствует пользователь"""
    user_id = update.effective_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.id, h.name, h.prizes, h.registration, h.duration, h.link, h.telegram_chat, h.comments, COUNT(p.user_id) as participant_count
        FROM hackathons h
        JOIN participations p ON h.id = p.hackathon_id
        WHERE p.user_id = ?
        GROUP BY h.id
    """, (user_id,))
    hackathons = cursor.fetchall()
    conn.close()
    
    if not hackathons:
        await update.callback_query.message.edit_text(
            "Вы еще не участвуете ни в одном хакатоне. Хотите просмотреть доступные хакатоны?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Просмотр хакатонов", callback_data='view_hackathons')],
                                               [InlineKeyboardButton("Вернуться в меню", callback_data='main_menu')]])
        )
        return
    
    context.user_data['current_hackathon'] = 0
    context.user_data['hackathons'] = hackathons
    await show_hackathon(update, context, is_my_hackathons=True)

async def show_hackathon(update: Update, context: ContextTypes.DEFAULT_TYPE, is_my_hackathons=False):
    """Показать информацию о конкретном хакатоне"""
    hackathons = context.user_data['hackathons']
    current_index = context.user_data['current_hackathon']
    hackathon = hackathons[current_index]
    
    hackathon_id, name, prizes, registration, duration, link, telegram_chat, comments, participant_count = hackathon
    
    message = (
        f"Хакатон: {name}\n\n"
        f"Призы: {prizes}\n"
        f"Регистрация: {registration}\n"
        f"Длительность: {duration}\n"
        f"Ссылка: {link}\n"
        f"Чат Telegram: {telegram_chat}\n"
        f"Комментарии: {comments}\n"
        f"Количество участников от сообщества: {participant_count}"
    )
    
    keyboard = [
        [InlineKeyboardButton("Предыдущий", callback_data='prev_hackathon'),
         InlineKeyboardButton("Следующий", callback_data='next_hackathon')],
        [InlineKeyboardButton("Посмотреть участников", callback_data=f'look_for_members_{hackathon_id}')],
        [InlineKeyboardButton("Вернуться в меню", callback_data='main_menu')]
    ]
    
    if not is_my_hackathons:
        keyboard.insert(1, [InlineKeyboardButton("Я хочу участвовать", callback_data=f'participate_{hackathon_id}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.message.edit_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
    except BadRequest as e:
        if str(e) == "Message is not modified":
            pass
        else:
            raise

async def participate_hackathon(update: Update, context: ContextTypes.DEFAULT_TYPE, hackathon_id: int) -> None:
    """Регистрация пользователя на участие в хакатоне"""
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO participations (user_id, hackathon_id) VALUES (?, ?)", (user_id, hackathon_id))
    conn.commit()
    conn.close()
    
    await update.callback_query.answer("Вы успешно зарегистрировались на участие в этом хакатоне!")
    
    # Обновляем список хакатонов и отображаем следующий доступный
    await view_hackathons(update, context)

async def look_for_members(update: Update, context: ContextTypes.DEFAULT_TYPE, hackathon_id: int) -> None:
    """Просмотр участников конкретного хакатона"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.username, u.profile 
        FROM users u 
        JOIN participations p ON u.user_id = p.user_id 
        WHERE p.hackathon_id = ?
    """, (hackathon_id,))
    participants = cursor.fetchall()
    conn.close()

    if participants:
        context.user_data['participants'] = participants
        context.user_data['current_participant'] = 0
        await show_participant(update, context)
    else:
        message = "Пока нет участников для этого хакатона. Вы можете стать первым!"
        keyboard = [
            [InlineKeyboardButton("Вернуться к хакатонам", callback_data='view_hackathons')],
            [InlineKeyboardButton("Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(message, reply_markup=reply_markup)

async def show_participant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать профиль участника"""
    participants = context.user_data.get('participants', [])
    if not participants:
        await update.callback_query.message.edit_text(
            "Извините, нет доступных участников для этого хакатона.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Главное меню", callback_data='main_menu')]])
        )
        return

    current_index = context.user_data['current_participant']
    
    if current_index >= len(participants):
        message = "Больше нет участников для отображения."
        keyboard = [
            [InlineKeyboardButton("⬅️ Предыдущий", callback_data='prev_participant')],
            [InlineKeyboardButton("Вернуться к хакатонам", callback_data='view_hackathons')],
            [InlineKeyboardButton("Главное меню", callback_data='main_menu')]
        ]
    else:
        username, profile = participants[current_index]
        message = f"Участник {current_index + 1} из {len(participants)}:\n\n@{username}:\n{profile}"
        keyboard = [
            [InlineKeyboardButton("⬅️ Предыдущий", callback_data='prev_participant'),
             InlineKeyboardButton("Следующий ➡️", callback_data='next_participant')],
            [InlineKeyboardButton("Вернуться к хакатонам", callback_data='view_hackathons')],
            [InlineKeyboardButton("Главное меню", callback_data='main_menu')]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(message, reply_markup=reply_markup)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирование ошибок"""
    logger.error(msg="Исключение при обработке обновления:", exc_info=context.error)
    
    # Проверяем тип ошибки
    if isinstance(context.error, BadRequest):
        # Игнорируем ошибки "Message is not modified" и "Message to edit not found"
        if "Message is not modified" in str(context.error) or "Message to edit not found" in str(context.error):
            return
    
    # Для других типов ошибок отправляем сообщение пользователю
    error_message = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или свяжитесь с администратором."
    if update.effective_message:
        try:
            await update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    if context.user_data.get('expecting_profile'):
        await save_profile(update, context)
    else:
        await update.message.reply_text(
            "Извините, я не понимаю этой команды. Пожалуйста, используйте кнопки меню для навигации.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Главное меню", callback_data='main_menu')]])
        )

async def search_participants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поиск участников"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM hackathons")
    hackathons = cursor.fetchall()
    conn.close()

    if not hackathons:
        await update.callback_query.message.edit_text(
            "В настоящее время нет доступных хакатонов для поиска участников.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Вернуться в меню", callback_data='main_menu')]])
        )
        return

    keyboard = [[InlineKeyboardButton(name, callback_data=f'look_for_members_{id}')] for id, name in hackathons]
    keyboard.append([InlineKeyboardButton("Вернуться в меню", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.edit_text(
        "Выберите хакатон, для которого вы хотите найти участников:",
        reply_markup=reply_markup
    )

def main() -> None:
    """Основная функция для запуска бота"""
    setup_database()
    
    token = 'your_token'
    if not token:
        logger.error("Не найден токен бота. Установите переменную окружения TELEGRAM_BOT_TOKEN.")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
