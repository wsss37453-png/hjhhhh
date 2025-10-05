import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import json
import os

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

class DataManager:
    """Класс для управления данными с сохранением в файлы"""
    
    @staticmethod
    def load_data(filename):
        """Загрузка данных из файла"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки {filename}: {e}")
        return {}
    
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

# Загрузка данных при старте
orders = DataManager.load_data(ORDERS_FILE)
reviews = DataManager.load_data(REVIEWS_FILE)
active_chats = DataManager.load_data(ACTIVE_CHATS_FILE)

def save_all_data():
    """Сохранение всех данных"""
    DataManager.save_data(ORDERS_FILE, orders)
    DataManager.save_data(REVIEWS_FILE, reviews)
    DataManager.save_data(ACTIVE_CHATS_FILE, active_chats)

async def periodic_save():
    """Периодическое сохранение данных"""
    while True:
        await asyncio.sleep(300)  # Сохраняем каждые 5 минут
        save_all_data()
        logger.info("Данные сохранены")

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
        [InlineKeyboardButton("🔙 Назад", callback_data="buy_stars")]
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
        if data == "help":
            await help_command(query, context)
        elif data == "buy_stars":
            await buy_stars_menu(query, context)
        elif data == "create_order":
            await create_order(query, context)
        elif data == "back_to_main":
            await back_to_main(query, context)
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

# Создание заказа
async def create_order(query, context: ContextTypes.DEFAULT_TYPE):
    order_id = str(query.from_user.id) + "_" + str(int(datetime.now().timestamp()))
    order_display_id = len(orders) + 1
    
    orders[order_id] = {
        'user_id': query.from_user.id,
        'username': query.from_user.username,
        'first_name': query.from_user.first_name,
        'stars_amount': MIN_STARS,
        'status': 'creating',
        'confirmed_username': None,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'order_display_id': order_display_id
    }
    
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
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    if order['user_id'] != query.from_user.id:
        await query.edit_message_text("❌ У вас нет прав для отмены этого заказа!")
        return
    
    orders[order_id]['status'] = 'cancelled'
    
    await query.edit_message_text(
        "❌ *Заказ отменен*\n\n"
        "Вы можете создать новый заказ в любое время!",
        reply_markup=buy_stars_keyboard(),
        parse_mode='Markdown'
    )

# Изменение количества звезд
async def change_amount(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    await query.edit_message_text(
        "🔢 *Введите новое количество звезд:*\n\n"
        f"⚠️ Минимальное количество: {MIN_STARS} звезд\n"
        "💫 Пример: 100, 250, 500\n\n"
        f"💰 *Расчет будет:* ваше число × {RATE} руб.",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_stars_amount'] = order_id

# Показать заказ с обновленными данными
async def show_order_with_updated_amount(update, context, order_id, stars_amount):
    if order_id not in orders:
        await update.message.reply_text("❌ Заказ не найден!")
        return
    
    orders[order_id]['stars_amount'] = stars_amount
    cost = stars_amount * RATE
    
    text = f"""
📋 *Создание заказа #{orders[order_id].get('order_display_id', 'N/A')}*

⭐ Количество звезд: {stars_amount}
💰 Стоимость: {cost:.1f} рублей

💡 *Курс:* 1 звезда = {RATE} рубля
🧮 *Расчет:* {stars_amount} × {RATE} = {cost:.1f} руб.

⚠️ *Внимание:* Покупка строго от {MIN_STARS} звезд!

Вы можете изменить количество звезд или отправить заказ.
    """
    
    await update.message.reply_text(
        text,
        reply_markup=order_creation_keyboard(order_id),
        parse_mode='Markdown'
    )

# Отправка заказа продавцу
async def submit_order(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    
    if order['stars_amount'] < MIN_STARS:
        cost = order['stars_amount'] * RATE
        await query.edit_message_text(
            f"❌ *Ошибка!*\n\n"
            f"Покупка строго от {MIN_STARS} звезд!\n"
            f"Ваш заказ: {order['stars_amount']} звезд = {cost:.1f} руб.\n\n"
            f"Измените количество звезд.",
            reply_markup=order_creation_keyboard(order_id),
            parse_mode='Markdown'
        )
        return
    
    # Просим подтвердить username
    await query.edit_message_text(
        "👤 *Подтвердите ваш username:*\n\n"
        f"Наш бот определил ваш username как: @{order['username'] if order['username'] else 'не указан'}\n\n"
        "📝 Пожалуйста, напишите ваш username еще раз для подтверждения:",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_username_confirmation'] = order_id

# Подтверждение username
async def confirm_username(update, context, order_id, username_input):
    order = orders[order_id]
    original_username = order['username']
    
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
        order['confirmed_username'] = cleaned_input
        order['status'] = 'waiting_payment'
        
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
                reply_markup=seller_payment_keyboard(order_id),
                parse_mode='Markdown'
            )
            logger.info(f"Уведомление отправлено продавцу {SELLER_ID} о заказе {order_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления продавцу: {e}")
            await update.message.reply_text(
                "⚠️ *Не удалось уведомить продавца. Пожалуйста, свяжитесь с ним напрямую.*",
                parse_mode='Markdown'
            )
        
        return True

# Информация о заказе для продавца
async def order_info(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    cost = order['stars_amount'] * RATE
    
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
        reply_markup=seller_payment_keyboard(order_id),
        parse_mode='Markdown'
    )

# Подтверждение оплаты продавцом
async def payment_confirmed(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    order['status'] = 'completed'
    order['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
            reply_markup=rating_keyboard(order_id),
            parse_mode='Markdown'
        )
        
        # Обновляем сообщение продавца
        await query.edit_message_text(
            f"✅ *Оплата подтверждена!*\n\n"
            f"Покупатель @{order['confirmed_username']} уведомлен о подтверждении оплаты.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Оплата подтверждена для заказа {order_id}")
        
    except Exception as e:
        logger.error(f"Ошибка уведомления покупателя: {e}")
        await query.edit_message_text(
            f"✅ *Оплата подтверждена, но не удалось уведомить покупателя:* {e}",
            parse_mode='Markdown'
        )

# Отклонение оплаты продавцом
async def payment_not_received(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    
    # Уведомление покупателю
    user_text = f"""
❌ *Проблема с оплатой* 😔

💸 *Продавец не получил вашу оплату.*

⚠️ *Возможные причины:*
• Деньги еще не поступили на счет
• Неправильно указаны реквизиты
• Предоставлена неверная квитанция

📸 *Пожалуйста, проверьте и отправьте правильную квитанцию об оплате.*

🔄 Если вы уверены, что оплатили правильно, свяжитесь с продавцом.
    """
    
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=user_text,
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            f"❌ *Оплата не подтверждена*\n\n"
            f"Покупатель @{order['confirmed_username']} уведомлен о проблеме с оплатой.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка уведомления покупателя: {e}")
        await query.edit_message_text(
            f"❌ *Оплата не подтверждена, но не удалось уведомить покупателя:* {e}",
            parse_mode='Markdown'
        )

# Открытие чата с покупателем
async def open_chat(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    
    # Сохраняем информацию о активном чате
    active_chats[str(query.from_user.id)] = {
        'customer_id': order['user_id'],
        'customer_username': order['confirmed_username'],
        'customer_name': order['first_name'],
        'order_id': order_id
    }
    
    DataManager.save_data(ACTIVE_CHATS_FILE, active_chats)
    
    chat_info = f"""
💬 *Чат с покупателем*

👤 *Имя:* {order['first_name']}
📛 *Username:* @{order['confirmed_username']}
🆔 *ID:* {order['user_id']}

⭐ *Заказано звезд:* {order['stars_amount']}
💰 *Сумма:* {order['stars_amount'] * RATE:.1f} руб.

📝 *Теперь вы можете написать сообщение покупателю.* 
Просто введите текст и он будет отправлен.

⚠️ *Внимание:* Не передавайте личные данные через бота.
    """
    
    await query.edit_message_text(
        chat_info,
        reply_markup=back_to_seller_menu_keyboard(order_id),
        parse_mode='Markdown'
    )

# Возврат к заказу из чата
async def back_to_order(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    
    # Очищаем активный чат
    if str(query.from_user.id) in active_chats:
        del active_chats[str(query.from_user.id)]
        DataManager.save_data(ACTIVE_CHATS_FILE, active_chats)
    
    cost = order['stars_amount'] * RATE
    order_text = f"""
📋 *Заказ #{order.get('order_display_id', 'N/A')}*

👤 *Покупатель:* {order['first_name']}
📛 *Username:* @{order['confirmed_username']}
🆔 *ID:* {order['user_id']}

⭐ *Количество звезд:* {order['stars_amount']}
💰 *Сумма:* {cost:.1f} рублей

📊 *Статус:* {order['status']}
    """
    
    await query.edit_message_text(
        order_text,
        reply_markup=seller_payment_keyboard(order_id),
        parse_mode='Markdown'
    )

# Обработка оценки
async def handle_rating(query, context: ContextTypes.DEFAULT_TYPE, order_id, rating):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    
    # Сохраняем оценку
    order['rating'] = rating
    
    await query.edit_message_text(
        f"⭐ *Спасибо за оценку {rating} звезд!*\n\n"
        f"📝 *Напишите ваш отзыв о работе бота и качестве обслуживания:*\n\n"
        f"💬 Ваш отзыв поможет нам стать лучше!",
        parse_mode='Markdown'
    )
    
    # Сохраняем order_id в user_data для обработки отзыва
    context.user_data['awaiting_review'] = order_id

# Пропуск оценки
async def skip_rating(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    
    await query.edit_message_text(
        "🙏 *Спасибо за покупку!*\n\n"
        "✨ *Желаем вам удачного дня и ждем снова!*",
        parse_mode='Markdown'
    )
    
    # Очищаем данные заказа
    if order_id in orders:
        del orders[order_id]
        DataManager.save_data(ORDERS_FILE, orders)

# Обработка отзыва
async def handle_review(update, context, order_id, review_text):
    try:
        if order_id not in orders:
            await update.message.reply_text("❌ Заказ не найден!")
            return
        
        order = orders[order_id]
        
        # Сохраняем отзыв
        reviews[order_id] = {
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

🆔 *ID заказа:* {order_id}
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
        
        # Успешное сообщение покупателю
        success_text = f"""
✅ *Отзыв успешно отправлен!* 🎉

⭐ *Ваша оценка:* {order.get('rating', 0)} звезд
💬 *Ваш отзыв:* {review_text}

🙏 *Спасибо за ваше мнение!* 
Ваш отзыв очень важен для нас и поможет стать лучше!

✨ *Желаем вам удачного дня и ждем снова!*
        """
        
        await update.message.reply_text(
            success_text,
            parse_mode='Markdown'
        )
        
        # Очищаем данные заказа
        if order_id in orders:
            del orders[order_id]
            DataManager.save_data(ORDERS_FILE, orders)
            
        logger.info(f"Отзыв отправлен от пользователя {order['user_id']}")
            
    except Exception as e:
        logger.error(f"Ошибка отправки отзыва: {e}")
        # В случае ошибки все равно показываем успешное сообщение пользователю
        await update.message.reply_text(
            "✅ *Отзыв успешно отправлен!*\n\nСпасибо за ваше мнение!",
            parse_mode='Markdown'
        )
        
        # Очищаем данные заказа
        if order_id in orders:
            del orders[order_id]
            DataManager.save_data(ORDERS_FILE, orders)
            
    except Exception as e:
        logger.error(f"Ошибка обработки отзыва: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при отправке отзыва. Попробуйте еще раз.",
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

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Проверяем, ожидаем ли мы подтверждение username
    if 'awaiting_username_confirmation' in context.user_data:
        order_id = context.user_data['awaiting_username_confirmation']
        success = await confirm_username(update, context, order_id, message_text)
        if success:
            del context.user_data['awaiting_username_confirmation']
        return
    
    # Проверяем, ожидаем ли мы количество звезд
    elif 'awaiting_stars_amount' in context.user_data:
        order_id = context.user_data['awaiting_stars_amount']
        try:
            stars_amount = int(message_text)
            if stars_amount >= MIN_STARS:
                await show_order_with_updated_amount(update, context, order_id, stars_amount)
                del context.user_data['awaiting_stars_amount']
            else:
                await update.message.reply_text(
                    f"❌ *Минимальное количество звезд: {MIN_STARS}*\n\n"
                    f"Пожалуйста, введите число больше или равное {MIN_STARS}:",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ *Пожалуйста, введите корректное число*\n\n"
                f"Пример: 100, 250, 500 (минимум {MIN_STARS})",
                parse_mode='Markdown'
            )
        return
    
    # Проверяем, ожидаем ли мы отзыв
    elif 'awaiting_review' in context.user_data:
        order_id = context.user_data['awaiting_review']
        await handle_review(update, context, order_id, message_text)
        del context.user_data['awaiting_review']
        return
    
    # Проверяем, является ли отправитель продавцом в активном чате
    elif str(user_id) in active_chats and user_id == SELLER_ID:
        chat_info = active_chats[str(user_id)]
        customer_id = chat_info['customer_id']
        
        try:
            # Отправляем сообщение покупателю
            seller_message = f"""
💬 *Сообщение от продавца:*

{message_text}

---
📦 *Заказ #{orders[chat_info['order_id']].get('order_display_id', 'N/A')}*
            """
            
            await context.bot.send_message(
                chat_id=customer_id,
                text=seller_message,
                parse_mode='Markdown'
            )
            
            # Подтверждаем продавцу
            await update.message.reply_text(
                f"✅ *Сообщение отправлено покупателю*\n\n"
                f"👤 {chat_info['customer_name']} (@{chat_info['customer_username']})",
                parse_mode='Markdown'
            )
            
            logger.info(f"Сообщение от продавца {user_id} отправлено покупателю {customer_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения покупателю: {e}")
            await update.message.reply_text(
                f"❌ *Не удалось отправить сообщение:* {e}",
                parse_mode='Markdown'
            )
        return
    
    # Обычное сообщение - показываем главное меню
    await update.message.reply_text(
        "🤖 *Бот по покупке звезд*\n\n"
        "Выберите действие в меню ниже:",
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    
    try:
        # Пытаемся уведомить пользователя об ошибке
        if update and update.effective_user:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="❌ Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз."
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

# Основная функция
def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем периодическое сохранение данных
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_save())
    
    # Запускаем бота
    logger.info("Бот запущен")
    print("🤖 Бот запущен! Для остановки нажмите Ctrl+C")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
        print("\n👋 Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")
    finally:
        # Сохраняем данные при завершении
        save_all_data()
        logger.info("Данные сохранены при завершении работы")
