import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import json
import os
import pickle

# Настройки бота
BOT_TOKEN = "7573319037:AAG_AGqsmds9z212-i083AKEv-qMbaAP1OA"
SELLER_ID = 1476734998  # ID продавца
RATE = 1.4  # Курс 1 звезда = 1.4 рубля
MIN_STARS = 50  # Минимальное количество звезд

# Реквизиты для оплаты
PAYMENT_DETAILS = """
💳 *Реквизиты для оплаты:*

🏦 Банк: Тинькофф
📱 Номер карты: `2200 7001 2345 6789`
👤 Получатель: Иван Иванов

⚠️ *Внимание:* Обязательно сохраните чек/квитанцию об оплате!
"""

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Файлы для хранения данных
ORDERS_FILE = 'orders.json'
REVIEWS_FILE = 'reviews.json'
ACTIVE_CHATS_FILE = 'active_chats.json'
USER_DATA_FILE = 'user_data.pkl'

class DataManager:
    """Класс для управления данными с сохранением в файлы"""
    
    @staticmethod
    def load_data(filename, default_type=dict):
        """Загрузка данных из файла"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки {filename}: {e}")
        return default_type()
    
    @staticmethod
    def save_data(filename, data):
        """Сохранение данных в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения {filename}: {e}")
            return False
    
    @staticmethod
    def load_user_data():
        """Загрузка user_data"""
        try:
            if os.path.exists(USER_DATA_FILE):
                with open(USER_DATA_FILE, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки user_data: {e}")
        return {}
    
    @staticmethod
    def save_user_data(user_data):
        """Сохранение user_data"""
        try:
            with open(USER_DATA_FILE, 'wb') as f:
                pickle.dump(user_data, f)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения user_data: {e}")
            return False

# Загрузка данных при старте
orders = DataManager.load_data(ORDERS_FILE)
reviews = DataManager.load_data(REVIEWS_FILE)
active_chats = DataManager.load_data(ACTIVE_CHATS_FILE)
persistent_user_data = DataManager.load_user_data()

def save_all_data():
    """Сохранение всех данных"""
    DataManager.save_data(ORDERS_FILE, orders)
    DataManager.save_data(REVIEWS_FILE, reviews)
    DataManager.save_data(ACTIVE_CHATS_FILE, active_chats)
    logger.info("Все данные сохранены")

async def periodic_save():
    """Периодическое сохранение данных"""
    while True:
        await asyncio.sleep(60)  # Сохраняем каждую минуту
        save_all_data()

def get_order_by_id(order_id):
    """Безопасное получение заказа по ID"""
    if order_id in orders:
        return orders[order_id]
    
    # Попробуем найти заказ по display_id
    for oid, order in orders.items():
        if order.get('order_display_id') == int(order_id):
            return order
        if str(order.get('order_display_id')) == order_id:
            return order
    
    return None

def get_order_id_by_display_id(display_id):
    """Получить order_id по display_id"""
    for order_id, order in orders.items():
        if order.get('order_display_id') == display_id:
            return order_id
    return None

# Клавиатура главного меню
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton("🛠️ Тех поддержка", callback_data="help")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для покупки звезд
def buy_stars_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 Создать заказ", callback_data="create_order")],
        [InlineKeyboardButton("📋 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура при создании заказа
def order_creation_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить количество звезд", callback_data=f"change_amount:{order_id}")],
        [InlineKeyboardButton("📤 Отправить заказ", callback_data=f"submit_order:{order_id}")],
        [InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_order:{order_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_buy_stars")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для продавца (подтверждение оплаты)
def seller_payment_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton("✅ Деньги пришли", callback_data=f"payment_confirmed:{order_id}")],
        [InlineKeyboardButton("❌ Деньги не пришли", callback_data=f"payment_not_received:{order_id}")],
        [InlineKeyboardButton("💬 Написать покупателю", callback_data=f"open_chat:{order_id}")],
        [InlineKeyboardButton("📊 Инфо о заказе", callback_data=f"order_info:{order_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для оценки бота
def rating_keyboard(order_id):
    keyboard = [
        [
            InlineKeyboardButton("1 ⭐", callback_data=f"rate_1:{order_id}"),
            InlineKeyboardButton("2 ⭐", callback_data=f"rate_2:{order_id}"),
            InlineKeyboardButton("3 ⭐", callback_data=f"rate_3:{order_id}"),
            InlineKeyboardButton("4 ⭐", callback_data=f"rate_4:{order_id}"),
            InlineKeyboardButton("5 ⭐", callback_data=f"rate_5:{order_id}")
        ],
        [InlineKeyboardButton("🚫 Пропустить оценку", callback_data=f"skip_rating:{order_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для возврата в меню продавца
def back_to_seller_menu_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к заказу", callback_data=f"back_to_order:{order_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Восстанавливаем user_data из persistent storage
    if str(user.id) in persistent_user_data:
        context.user_data.update(persistent_user_data[str(user.id)])
    
    welcome_text = f"""
✨ *Добро пожаловать в бот по покупке звезд!* ✨

Привет, {user.first_name}! 🎉

🌟 *Что у нас есть:*
• Покупка Telegram Stars по выгодному курсу
• Мгновенное получение звезд
• Безопасные сделки
• Поддержка 24/7

💫 *Курс:* 1 звезда = {RATE} рубля

🚀 *Начните покупку звезд прямо сейчас!*
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )
    logger.info(f"Пользователь {user.id} запустил бота")

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
🛠️ *Техническая поддержка*

⚠️ *Если у вас возникли проблемы или вы нашли баг:*

👨‍💻 *Кодер бота:* @steddyrevival
🤝 *Продавец:* @cemper0

📞 *Обращайтесь по любым вопросам:*
• Технические неполадки
• Проблемы с покупкой звезд
• Баги и ошибки в боте
• Вопросы по оплате

⏰ *Время ответа:* в течение 24 часов
    """
    
    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]),
            parse_mode='Markdown'
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    user_id = update.effective_user.id
    
    # Статистика для продавца
    if user_id == SELLER_ID:
        total_orders = len(orders)
        completed_orders = sum(1 for order in orders.values() if order.get('status') == 'completed')
        pending_orders = sum(1 for order in orders.values() if order.get('status') == 'waiting_payment')
        
        total_revenue = sum(order['stars_amount'] * RATE for order in orders.values() if order.get('status') == 'completed')
        
        stats_text = f"""
📊 *Статистика продавца*

📦 Всего заказов: {total_orders}
✅ Выполнено: {completed_orders}
⏳ Ожидают оплаты: {pending_orders}

💰 Общая выручка: {total_revenue:.2f} руб.
⭐ Всего звезд продано: {sum(order['stars_amount'] for order in orders.values() if order.get('status') == 'completed')}

📈 Средний чек: {total_revenue/completed_orders if completed_orders > 0 else 0:.2f} руб.
        """
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(stats_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(stats_text, parse_mode='Markdown')
    else:
        # Статистика для обычного пользователя
        user_orders = [order for order in orders.values() if order['user_id'] == user_id]
        completed_user_orders = [order for order in user_orders if order.get('status') == 'completed']
        
        stats_text = f"""
📊 *Ваша статистика*

📦 Всего заказов: {len(user_orders)}
✅ Выполнено: {len(completed_user_orders)}

💰 Всего потрачено: {sum(order['stars_amount'] * RATE for order in completed_user_orders):.2f} руб.
⭐ Всего звезд куплено: {sum(order['stars_amount'] for order in completed_user_orders)}
        """
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(stats_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(stats_text, parse_mode='Markdown')

async def my_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заказы пользователя"""
    user_id = update.effective_user.id
    user_orders = [order for order_id, order in orders.items() if order['user_id'] == user_id]
    
    if not user_orders:
        await update.callback_query.edit_message_text(
            "📦 У вас пока нет заказов.\n\nСоздайте первый заказ!",
            reply_markup=buy_stars_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    orders_text = "📦 *Ваши заказы:*\n\n"
    
    for i, order in enumerate(user_orders[-5:], 1):  # Показываем последние 5 заказов
        status_emoji = {
            'creating': '🔄',
            'waiting_payment': '⏳', 
            'completed': '✅',
            'cancelled': '❌'
        }.get(order.get('status', 'creating'), '❓')
        
        orders_text += f"""
{i}. {status_emoji} Заказ #{order.get('order_display_id', 'N/A')}
   ⭐ Звезд: {order['stars_amount']}
   💰 Сумма: {order['stars_amount'] * RATE:.2f} руб.
   📊 Статус: {order.get('status', 'creating')}
   🕐 Создан: {order.get('created_at', 'N/A')}
"""
    
    await update.callback_query.edit_message_text(
        orders_text,
        reply_markup=buy_stars_keyboard(),
        parse_mode='Markdown'
    )

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    try:
        # Сохраняем user_data перед обработкой
        persistent_user_data[str(user_id)] = dict(context.user_data)
        DataManager.save_user_data(persistent_user_data)
        
        if data == "help":
            await help_command(query, context)
        elif data == "buy_stars":
            await buy_stars_menu(query, context)
        elif data == "create_order":
            await create_order(query, context)
        elif data == "back_to_main":
            await back_to_main(query, context)
        elif data == "back_to_buy_stars":
            await buy_stars_menu(query, context)
        elif data == "stats":
            await stats_command(update, context)
        elif data == "my_orders":
            await my_orders_command(update, context)
        elif data.startswith("change_amount:"):
            order_id = data.split(":")[1]
            await change_amount(query, context, order_id)
        elif data.startswith("submit_order:"):
            order_id = data.split(":")[1]
            await submit_order(query, context, order_id)
        elif data.startswith("cancel_order:"):
            order_id = data.split(":")[1]
            await cancel_order(query, context, order_id)
        elif data.startswith("payment_confirmed:"):
            order_id = data.split(":")[1]
            await payment_confirmed(query, context, order_id)
        elif data.startswith("payment_not_received:"):
            order_id = data.split(":")[1]
            await payment_not_received(query, context, order_id)
        elif data.startswith("open_chat:"):
            order_id = data.split(":")[1]
            await open_chat(query, context, order_id)
        elif data.startswith("back_to_order:"):
            order_id = data.split(":")[1]
            await back_to_order(query, context, order_id)
        elif data.startswith("order_info:"):
            order_id = data.split(":")[1]
            await order_info(query, context, order_id)
        elif data.startswith("rate_"):
            rating_data = data.split(":")
            rating = int(rating_data[0].split("_")[1])
            order_id = rating_data[1]
            await handle_rating(query, context, order_id, rating)
        elif data.startswith("skip_rating:"):
            order_id = data.split(":")[1]
            await skip_rating(query, context, order_id)
            
        # Сохраняем данные после важных действий
        save_all_data()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике кнопок: {e}")
        await query.edit_message_text("❌ Произошла ошибка. Попробуйте еще раз.")

# Меню покупки звезд
async def buy_stars_menu(query, context: ContextTypes.DEFAULT_TYPE):
    text = """
🛒 *Покупка звезд*

💫 *Текущий курс:* 1 звезда = 1.4 рубля
⭐ *Минимальный заказ:* 50 звезд

💰 *Пример расчета:*
• 50 звезд = 70 рублей
• 100 звезд = 140 рублей
• 500 звезд = 700 рублей

🎯 Для начала покупки нажмите "Создать заказ"
    """
    
    await query.edit_message_text(
        text,
        reply_markup=buy_stars_keyboard(),
        parse_mode='Markdown'
    )

# Возврат в главное меню
async def back_to_main(query, context: ContextTypes.DEFAULT_TYPE):
    user = query.from_user
    welcome_text = f"""
✨ *Добро пожаловать в бот по покупке звезд!* ✨

Привет, {user.first_name}! 🎉

🌟 *Что у нас есть:*
• Покупка Telegram Stars по выгодному курсу
• Мгновенное получение звезд
• Безопасные сделки
• Поддержка 24/7

💫 *Курс:* 1 звезда = {RATE} рубля

🚀 *Начните покупку звезд прямо сейчас!*
    """
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )

# Создание заказа
async def create_order(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    order_id = f"{user_id}_{int(datetime.now().timestamp())}"
    order_display_id = len(orders) + 1
    
    # Сохраняем order_id в контексте пользователя
    context.user_data['current_order_id'] = order_id
    persistent_user_data[str(user_id)] = dict(context.user_data)
    DataManager.save_user_data(persistent_user_data)
    
    orders[order_id] = {
        'user_id': user_id,
        'username': query.from_user.username or "",
        'first_name': query.from_user.first_name,
        'stars_amount': MIN_STARS,
        'status': 'creating',
        'confirmed_username': None,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'order_display_id': order_display_id
    }
    
    save_all_data()
    
    cost = MIN_STARS * RATE
    text = f"""
📋 *Создание заказа #{order_display_id}*

⭐ Количество звезд: {MIN_STARS}
💰 Стоимость: {cost:.1f} рублей

💡 *Курс:* 1 звезда = {RATE} рубля
🧮 *Расчет:* {MIN_STARS} × {RATE} = {cost:.1f} руб.

⚠️ *Внимание:* Покупка строго от {MIN_STARS} звезд!

Вы можете изменить количество звезд или отправить заказ.
    """
    
    await query.edit_message_text(
        text,
        reply_markup=order_creation_keyboard(order_id),
        parse_mode='Markdown'
    )

# Отмена заказа
async def cancel_order(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    if order['user_id'] != query.from_user.id:
        await query.edit_message_text("❌ У вас нет прав для отмены этого заказа!")
        return
    
    # Находим правильный order_id
    actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
    orders[actual_order_id]['status'] = 'cancelled'
    
    await query.edit_message_text(
        "❌ *Заказ отменен*\n\n"
        "Вы можете создать новый заказ в любое время!",
        reply_markup=buy_stars_keyboard(),
        parse_mode='Markdown'
    )
    save_all_data()

# Изменение количества звезд
async def change_amount(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    # Сохраняем order_id в контексте
    context.user_data['awaiting_stars_amount'] = order_id
    persistent_user_data[str(query.from_user.id)] = dict(context.user_data)
    DataManager.save_user_data(persistent_user_data)
    
    await query.edit_message_text(
        "🔢 *Введите новое количество звезд:*\n\n"
        f"⚠️ Минимальное количество: {MIN_STARS} звезд\n"
        "💫 Пример: 100, 250, 500\n\n"
        f"💰 *Расчет будет:* ваше число × {RATE} руб.",
        parse_mode='Markdown'
    )

# Показать заказ с обновленными данными
async def show_order_with_updated_amount(update, context, order_id, stars_amount):
    order = get_order_by_id(order_id)
    if not order:
        await update.message.reply_text("❌ Заказ не найден!")
        return
    
    # Находим правильный order_id
    actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
    orders[actual_order_id]['stars_amount'] = stars_amount
    cost = stars_amount * RATE
    
    text = f"""
📋 *Создание заказа #{orders[actual_order_id].get('order_display_id', 'N/A')}*

⭐ Количество звезд: {stars_amount}
💰 Стоимость: {cost:.1f} рублей

💡 *Курс:* 1 звезда = {RATE} рубля
🧮 *Расчет:* {stars_amount} × {RATE} = {cost:.1f} руб.

⚠️ *Внимание:* Покупка строго от {MIN_STARS} звезд!

Вы можете изменить количество звезд или отправить заказ.
    """
    
    await update.message.reply_text(
        text,
        reply_markup=order_creation_keyboard(actual_order_id),
        parse_mode='Markdown'
    )
    save_all_data()

# Отправка заказа продавцу
async def submit_order(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    if order['stars_amount'] < MIN_STARS:
        cost = order['stars_amount'] * RATE
        actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
        await query.edit_message_text(
            f"❌ *Ошибка!*\n\n"
            f"Покупка строго от {MIN_STARS} звезд!\n"
            f"Ваш заказ: {order['stars_amount']} звезд = {cost:.1f} руб.\n\n"
            f"Измените количество звезд.",
            reply_markup=order_creation_keyboard(actual_order_id),
            parse_mode='Markdown'
        )
        return
    
    # Сохраняем order_id в контексте для подтверждения username
    context.user_data['awaiting_username_confirmation'] = order_id
    persistent_user_data[str(query.from_user.id)] = dict(context.user_data)
    DataManager.save_user_data(persistent_user_data)
    
    # Просим подтвердить username
    await query.edit_message_text(
        "👤 *Подтвердите ваш username:*\n\n"
        f"Наш бот определил ваш username как: @{order['username'] if order['username'] else 'не указан'}\n\n"
        "📝 Пожалуйста, напишите ваш username еще раз для подтверждения:",
        parse_mode='Markdown'
    )

# Подтверждение username
async def confirm_username(update, context, order_id, username_input):
    order = get_order_by_id(order_id)
    if not order:
        await update.message.reply_text("❌ Заказ не найден!")
        return False
        
    original_username = order['username'] or ""
    
    # Убираем @ если пользователь его ввел
    cleaned_input = username_input.replace('@', '').strip()
    original_cleaned = original_username.replace('@', '').strip() if original_username else ''
    
    if cleaned_input.lower() != original_cleaned.lower():
        await update.message.reply_text(
            f"❌ *Username не совпадает!*\n\n"
            f"Бот определил: @{original_username if original_username else 'не указан'}\n"
            f"Вы ввели: @{cleaned_input}\n\n"
            "📝 Пожалуйста, введите username точно как в вашем профиле:",
            parse_mode='Markdown'
        )
        return False
    else:
        # Находим правильный order_id
        actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
        orders[actual_order_id]['confirmed_username'] = cleaned_input
        orders[actual_order_id]['status'] = 'waiting_payment'
        
        cost = order['stars_amount'] * RATE
        
        # Инструкция по оплате для покупателя
        user_text = f"""
✅ *Заказ создан!* 🎉

📋 *Детали заказа #{order.get('order_display_id', 'N/A')}:*
⭐ Звезд: {order['stars_amount']}
💰 Сумма: {cost:.1f} руб.
👤 Ваш username: @{cleaned_input}

{PAYMENT_DETAILS}

📸 *После оплаты:* 
Пришлите скриншот чека/квитанции об оплате в этот чат.

⏳ *Статус:* Ожидание оплаты
        """
        
        await update.message.reply_text(
            user_text,
            parse_mode='Markdown'
        )
        
        # Уведомление продавцу
        seller_text = f"""
🎯 *Новый заказ на покупку!* 🎯

🆔 *Заказ #*{order.get('order_display_id', 'N/A')}
👤 *Покупатель:* {order['first_name']}
📛 *Username:* @{cleaned_input}
🆔 *ID:* {order['user_id']}

⭐ *Количество звезд:* {order['stars_amount']}
💰 *Сумма:* {cost:.1f} рублей

🧮 *Расчет:* {order['stars_amount']} × {RATE} = {cost:.1f} руб.

⏰ *Время:* {update.message.date}
        """
        
        try:
            await context.bot.send_message(
                chat_id=SELLER_ID,
                text=seller_text,
                reply_markup=seller_payment_keyboard(actual_order_id),
                parse_mode='Markdown'
            )
            logger.info(f"Уведомление отправлено продавцу {SELLER_ID} о заказе {actual_order_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления продавцу: {e}")
            await update.message.reply_text(
                "⚠️ *Не удалось уведомить продавца. Пожалуйста, свяжитесь с ним напрямую.*",
                parse_mode='Markdown'
            )
        
        save_all_data()
        return True

# Информация о заказе для продавца
async def order_info(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    cost = order['stars_amount'] * RATE
    actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
    
    info_text = f"""
📋 *Информация о заказе #{order.get('order_display_id', 'N/A')}*

👤 *Покупатель:* {order['first_name']}
📛 *Username:* @{order['confirmed_username']}
🆔 *ID:* {order['user_id']}

⭐ *Количество звезд:* {order['stars_amount']}
💰 *Сумма:* {cost:.1f} руб.

📊 *Статус:* {order['status']}
🕐 *Создан:* {order.get('created_at', 'N/A')}

💬 *Действия:*
    """
    
    await query.edit_message_text(
        info_text,
        reply_markup=seller_payment_keyboard(actual_order_id),
        parse_mode='Markdown'
    )

# Подтверждение оплаты продавцом
async def payment_confirmed(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    # Находим правильный order_id
    actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
    orders[actual_order_id]['status'] = 'completed'
    orders[actual_order_id]['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Уведомление покупателю
    user_text = f"""
🎉 *Оплата подтверждена!* ✅

🤝 *Продавец подтвердил получение оплаты!*

📋 *Детали заказа #{order.get('order_display_id', 'N/A')}:*
⭐ Звезд: {order['stars_amount']}
💰 Сумма: {order['stars_amount'] * RATE:.1f} руб.

💫 *Ожидайте зачисления звезд на ваш аккаунт в течение 5-10 минут!*

⭐ *Пожалуйста, оцените нашу работу:*
    """
    
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=user_text,
            reply_markup=rating_keyboard(actual_order_id),
            parse_mode='Markdown'
        )
        
        # Обновляем сообщение продавца
        await query.edit_message_text(
            f"✅ *Оплата подтверждена!*\n\n"
            f"Покупатель @{order['confirmed_username']} уведомлен о подтверждении оплаты.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Оплата подтверждена для заказа {actual_order_id}")
        
    except Exception as e:
        logger.error(f"Ошибка уведомления покупателя: {e}")
        await query.edit_message_text(
            f"✅ *Оплата подтверждена, но не удалось уведомить покупателя:* {e}",
            parse_mode='Markdown'
        )
    
    save_all_data()

# Обработка оценки
async def handle_rating(query, context: ContextTypes.DEFAULT_TYPE, order_id, rating):
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    # Находим правильный order_id
    actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
    
    # Сохраняем оценку
    orders[actual_order_id]['rating'] = rating
    
    await query.edit_message_text(
        f"⭐ *Спасибо за оценку {rating} звезд!*\n\n"
        f"📝 *Напишите ваш отзыв о работе бота и качестве обслуживания:*\n\n"
        f"💬 Ваш отзыв поможет нам стать лучше!",
        parse_mode='Markdown'
    )
    
    # Сохраняем order_id в user_data для обработки отзыва
    context.user_data['awaiting_review'] = actual_order_id
    persistent_user_data[str(query.from_user.id)] = dict(context.user_data)
    DataManager.save_user_data(persistent_user_data)
    
    save_all_data()

# Пропуск оценки
async def skip_rating(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    # Находим правильный order_id
    actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
    
    await query.edit_message_text(
        "🙏 *Спасибо за покупку!*\n\n"
        "✨ *Желаем вам удачного дня и ждем снова!*",
        parse_mode='Markdown'
    )
    
    # Очищаем данные заказа
    if actual_order_id in orders:
        del orders[actual_order_id]
        save_all_data()

# Обработка отзыва
async def handle_review(update, context, order_id, review_text):
    try:
        order = get_order_by_id(order_id)
        if not order:
            await update.message.reply_text("❌ Заказ не найден!")
            return
        
        # Находим правильный order_id
        actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
        
        # Сохраняем отзыв
        reviews[actual_order_id] = {
            'user_id': order['user_id'],
            'username': order['confirmed_username'],
            'rating': order.get('rating', 0),
            'review': review_text,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        DataManager.save_data(REVIEWS_FILE, reviews)
        
        # Отправляем отзыв продавцу
        review_message = f"""
📝 *Новый отзыв от покупателя!*

👤 *Покупатель:* {order['first_name']}
📛 *Username:* @{order['confirmed_username']}
⭐ *Оценка:* {order.get('rating', 0)} ⭐

💬 *Отзыв:*
{review_text}

🆔 *ID заказа:* {actual_order_id}
👤 *ID покупателя:* {order['user_id']}
        """
        
        # Отправляем отзыв продавцу
        try:
            await context.bot.send_message(
                chat_id=SELLER_ID,
                text=review_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка отправки отзыва продавцу: {e}")

        await update.message.reply_text(
            "📝 *Спасибо за ваш отзыв!*\n\n"
            "💫 Ваше мнение очень важно для нас!\n"
            "✨ Ждем вас снова!",
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
        
        # Очищаем данные заказа после завершения
        if actual_order_id in orders:
            del orders[actual_order_id]
            save_all_data()
            
    except Exception as e:
        logger.error(f"Ошибка обработки отзыва: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении отзыва.",
            reply_markup=main_menu_keyboard()
        )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # Восстанавливаем user_data из persistent storage
    if str(user_id) in persistent_user_data:
        context.user_data.update(persistent_user_data[str(user_id)])
    
    try:
        # Обработка ввода количества звезд
        if 'awaiting_stars_amount' in context.user_data:
            order_id = context.user_data['awaiting_stars_amount']
            
            try:
                stars_amount = int(message_text)
                if stars_amount < MIN_STARS:
                    await update.message.reply_text(
                        f"❌ Минимальное количество звезд: {MIN_STARS}\n"
                        f"Пожалуйста, введите число больше или равное {MIN_STARS}:"
                    )
                    return
                
                # Очищаем состояние
                del context.user_data['awaiting_stars_amount']
                persistent_user_data[str(user_id)] = dict(context.user_data)
                DataManager.save_user_data(persistent_user_data)
                
                await show_order_with_updated_amount(update, context, order_id, stars_amount)
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Пожалуйста, введите корректное число:\n"
                    "Пример: 100, 250, 500"
                )
            return
        
        # Обработка подтверждения username
        elif 'awaiting_username_confirmation' in context.user_data:
            order_id = context.user_data['awaiting_username_confirmation']
            
            # Очищаем состояние независимо от результата
            del context.user_data['awaiting_username_confirmation']
            persistent_user_data[str(user_id)] = dict(context.user_data)
            DataManager.save_user_data(persistent_user_data)
            
            success = await confirm_username(update, context, order_id, message_text)
            if success:
                # После успешного подтверждения username, ждем скриншот оплаты
                context.user_data['awaiting_payment_screenshot'] = order_id
                persistent_user_data[str(user_id)] = dict(context.user_data)
                DataManager.save_user_data(persistent_user_data)
            return
        
        # Обработка отзыва
        elif 'awaiting_review' in context.user_data:
            order_id = context.user_data['awaiting_review']
            
            # Очищаем состояние
            del context.user_data['awaiting_review']
            persistent_user_data[str(user_id)] = dict(context.user_data)
            DataManager.save_user_data(persistent_user_data)
            
            await handle_review(update, context, order_id, message_text)
            return
        
        # Обработка скриншотов оплаты
        elif 'awaiting_payment_screenshot' in context.user_data:
            order_id = context.user_data['awaiting_payment_screenshot']
            order = get_order_by_id(order_id)
            
            if order and update.message.photo:
                # Пересылаем скриншот продавцу
                try:
                    # Отправляем уведомление продавцу о скриншоте
                    screenshot_notification = f"""
📸 *Покупатель отправил скриншот оплаты!*

🆔 *Заказ #*{order.get('order_display_id', 'N/A')}
👤 *Покупатель:* {order['first_name']} (@{order['confirmed_username']})

💬 *Сообщение покупателя:* {message_text if message_text else 'Без текста'}
                    """
                    
                    # Пересылаем фото продавцу
                    await context.bot.send_photo(
                        chat_id=SELLER_ID,
                        photo=update.message.photo[-1].file_id,
                        caption=screenshot_notification,
                        parse_mode='Markdown',
                        reply_markup=seller_payment_keyboard(order_id)
                    )
                    
                    await update.message.reply_text(
                        "✅ *Скриншот отправлен продавцу!*\n\n"
                        "⏳ Ожидайте подтверждения оплаты.\n"
                        "Обычно это занимает 5-15 минут.",
                        parse_mode='Markdown'
                    )
                    
                    # Очищаем состояние
                    del context.user_data['awaiting_payment_screenshot']
                    persistent_user_data[str(user_id)] = dict(context.user_data)
                    DataManager.save_user_data(persistent_user_data)
                    
                except Exception as e:
                    logger.error(f"Ошибка отправки скриншота продавцу: {e}")
                    await update.message.reply_text(
                        "❌ Не удалось отправить скриншот продавцу. Попробуйте еще раз или свяжитесь напрямую."
                    )
            return
        
        # Обработка сообщений в активных чатах
        elif str(user_id) in active_chats:
            target_user_id = active_chats[str(user_id)]
            try:
                # Пересылаем сообщение
                if update.message.text:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=f"💬 *Сообщение от {'продавца' if user_id == SELLER_ID else 'покупателя'}:*\n\n{message_text}",
                        parse_mode='Markdown'
                    )
                    await update.message.reply_text("✅ Сообщение отправлено!")
                elif update.message.photo:
                    await context.bot.send_photo(
                        chat_id=target_user_id,
                        photo=update.message.photo[-1].file_id,
                        caption=f"📸 *Фото от {'продавца' if user_id == SELLER_ID else 'покупателя'}:*\n\n{message_text}" if message_text else f"📸 Фото от {'продавца' if user_id == SELLER_ID else 'покупателя'}",
                        parse_mode='Markdown'
                    )
                    await update.message.reply_text("✅ Фото отправлено!")
            except Exception as e:
                logger.error(f"Ошибка пересылки сообщения: {e}")
                await update.message.reply_text("❌ Не удалось отправить сообщение.")
            return
        
        # Если ни одно условие не выполнено, показываем главное меню
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике сообщений: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте еще раз.",
            reply_markup=main_menu_keyboard()
        )

# Открытие чата с покупателем (для продавца)
async def open_chat(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if query.from_user.id != SELLER_ID:
        await query.answer("❌ Эта функция только для продавца!", show_alert=True)
        return
    
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    user_id = order['user_id']
    
    # Сохраняем активный чат
    active_chats[str(SELLER_ID)] = user_id
    active_chats[str(user_id)] = SELLER_ID
    
    DataManager.save_data(ACTIVE_CHATS_FILE, active_chats)
    
    await query.edit_message_text(
        f"💬 *Чат открыт с покупателем:*\n\n"
        f"👤 {order['first_name']} (@{order['confirmed_username']})\n"
        f"🆔 ID: {user_id}\n\n"
        f"📋 *Заказ #*{order.get('order_display_id', 'N/A')}\n"
        f"⭐ Звезд: {order['stars_amount']}\n\n"
        f"✉️ *Теперь вы можете обмениваться сообщениями.*\n"
        f"❌ *Чтобы закрыть чат, отправьте /close_chat*",
        parse_mode='Markdown'
    )
    
    # Уведомляем покупателя
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💬 *Продавец открыл чат с вами!*\n\n"
                 f"✉️ Теперь вы можете общаться напрямую.\n"
                 f"❌ Чтобы закрыть чат, отправьте /close_chat",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления покупателя об открытии чата: {e}")

# Команда для закрытия чата
async def close_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if str(user_id) in active_chats:
        target_user_id = active_chats[str(user_id)]
        
        # Удаляем из активных чатов
        del active_chats[str(user_id)]
        if str(target_user_id) in active_chats:
            del active_chats[str(target_user_id)]
        
        DataManager.save_data(ACTIVE_CHATS_FILE, active_chats)
        
        await update.message.reply_text("❌ Чат закрыт.")
        
        # Уведомляем второго участника
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="❌ Чат закрыт второй стороной."
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления о закрытии чата: {e}")
    else:
        await update.message.reply_text("У вас нет активных чатов.")

# Возврат к заказу (для продавца)
async def back_to_order(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if query.from_user.id != SELLER_ID:
        await query.answer("❌ Эта функция только для продавца!", show_alert=True)
        return
    
    order = get_order_by_id(order_id)
    if not order:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    cost = order['stars_amount'] * RATE
    actual_order_id = get_order_id_by_display_id(order['order_display_id']) or order_id
    
    order_text = f"""
🎯 *Заказ #{order.get('order_display_id', 'N/A')}*

👤 *Покупатель:* {order['first_name']}
📛 *Username:* @{order['confirmed_username']}
🆔 *ID:* {order['user_id']}

⭐ *Количество звезд:* {order['stars_amount']}
💰 *Сумма:* {cost:.1f} рублей

📊 *Статус:* {order.get('status', 'unknown')}
🕐 *Создан:* {order.get('created_at', 'N/A')}
    """
    
    await query.edit_message_text(
        order_text,
        reply_markup=seller_payment_keyboard(actual_order_id),
        parse_mode='Markdown'
    )

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Сохраняем все данные при ошибке
    save_all_data()

# Функция для безопасного завершения
async def shutdown():
    """Функция для безопасного завершения работы"""
    logger.info("Бот завершает работу...")
    save_all_data()
    logger.info("Все данные сохранены. Бот отключен.")

# Основная функция
def main():
    """Запуск бота"""
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("close_chat", close_chat))
    application.add_handler(CommandHandler("stats", stats_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем периодическое сохранение данных
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_save())
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling()
    
    # При завершении работы сохраняем данные
    loop.run_until_complete(shutdown())

if __name__ == "__main__":
    main()
