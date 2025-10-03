import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройки бота
BOT_TOKEN = "7573319037:AAG_AGqsmds9z212-i083AKEv-qMbaAP1OA"
SELLER_ID = 1476734998  # ID продавца
RATE = 1.4  # Курс 1 звезда = 1.4 рубля
MIN_STARS = 50  # Минимальное количество звезд

# Реквизиты для оплаты
PAYMENT_DETAILS = """
💳 *Реквизиты для оплаты:*

🏦 Банк: Тинькофф
📱 Номер карты: `2200 7017 9663 9299`
👤 Получатель: Юсуф Д

⚠️ *Внимание:* Обязательно сохраните чек/квитанцию об оплате!
"""

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Хранилище заказов и отзывов
orders = {}
reviews = {}
# Хранилище для переписки продавца с покупателями
active_chats = {}

# Клавиатура главного меню
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton("🛠️ Тех поддержка", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для покупки звезд
def buy_stars_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 Создать заказ", callback_data="create_order")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура при создании заказа
def order_creation_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить количество звезд", callback_data=f"change_amount:{order_id}")],
        [InlineKeyboardButton("📤 Отправить заказ", callback_data=f"submit_order:{order_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="buy_stars")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для продавца (подтверждение оплаты)
def seller_payment_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton("✅ Деньги пришли", callback_data=f"payment_confirmed:{order_id}")],
        [InlineKeyboardButton("❌ Деньги не пришли", callback_data=f"payment_not_received:{order_id}")],
        [InlineKeyboardButton("💬 Написать покупателю", callback_data=f"open_chat:{order_id}")]
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
        ]
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

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "help":
        await help_command(query, context)
    elif data == "buy_stars":
        await buy_stars_menu(query, context)
    elif data == "create_order":
        await create_order(query, context)
    elif data == "back_to_main":
        await back_to_main(query, context)
    elif data.startswith("change_amount:"):
        order_id = data.split(":")[1]
        await change_amount(query, context, order_id)
    elif data.startswith("submit_order:"):
        order_id = data.split(":")[1]
        await submit_order(query, context, order_id)
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
    elif data.startswith("rate_"):
        rating_data = data.split(":")
        rating = int(rating_data[0].split("_")[1])
        order_id = rating_data[1]
        await handle_rating(query, context, order_id, rating)

# Тех поддержка
async def help_command(query, context: ContextTypes.DEFAULT_TYPE):
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
    
    await query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]),
        parse_mode='Markdown'
    )

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
    order_id = str(query.from_user.id) + "_" + str(query.id)
    orders[order_id] = {
        'user_id': query.from_user.id,
        'username': query.from_user.username,
        'first_name': query.from_user.first_name,
        'stars_amount': MIN_STARS,
        'status': 'creating',
        'confirmed_username': None
    }
    
    cost = MIN_STARS * RATE
    text = f"""
📋 *Создание заказа*

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
📋 *Создание заказа*

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

📋 *Детали заказа:*
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

👤 *Покупатель:* {order['first_name']}
📛 *Username:* @{cleaned_input}
🆔 *ID:* {order['user_id']}

⭐ *Количество звезд:* {order['stars_amount']}
💰 *Сумма:* {cost:.1f} рублей

🧮 *Расчет:* {order['stars_amount']} × {RATE} = {cost:.1f} руб.

⏰ *Время:* {update.message.date}
        """
        
        await context.bot.send_message(
            chat_id=SELLER_ID,
            text=seller_text,
            reply_markup=seller_payment_keyboard(order_id),
            parse_mode='Markdown'
        )
        
        return True

# Подтверждение оплаты продавцом
async def payment_confirmed(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    order['status'] = 'completed'
    
    # Уведомление покупателю
    user_text = f"""
🎉 *Оплата подтверждена!* ✅

🤝 *Продавец подтвердил получение оплаты!*

📋 *Детали заказа:*
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
        
    except Exception as e:
        logging.error(f"Ошибка уведомления покупателя: {e}")

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
        logging.error(f"Ошибка уведомления покупателя: {e}")

# Открытие чата с покупателем
async def open_chat(query, context: ContextTypes.DEFAULT_TYPE, order_id):
    if order_id not in orders:
        await query.edit_message_text("❌ Заказ не найден!")
        return
    
    order = orders[order_id]
    
    # Сохраняем информацию о активном чате
    active_chats[query.from_user.id] = {
        'customer_id': order['user_id'],
        'customer_username': order['confirmed_username'],
        'customer_name': order['first_name'],
        'order_id': order_id
    }
    
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
    if query.from_user.id in active_chats:
        del active_chats[query.from_user.id]
    
    cost = order['stars_amount'] * RATE
    order_text = f"""
📋 *Заказ #{order_id}*

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

# Обработка отзыва
async def handle_review(update, context, order_id, review_text):
    try:
        if order_id not in orders:
            await update.message.reply_text("❌ Заказ не найден!")
            return
        
        order = orders[order_id]
        
        # Отправляем отзыв продавцу (на SELLER_ID)
        review_message = f"""
📝 *Новый отзыв от покупателя!*

👤 *Покупатель:* {order['first_name']}
📛 *Username:* @{order['confirmed_username']}
⭐ *Оценка:* {order['rating']} ⭐

💬 *Отзыв:*
{review_text}

🆔 *ID заказа:* {order_id}
👤 *ID покупателя:* {order['user_id']}
        """
        
        # Отправляем отзыв продавцу
        await context.bot.send_message(
            chat_id=SELLER_ID,
            text=review_message,
            parse_mode='Markdown'
        )
        
        # Успешное сообщение покупателю
        success_text = f"""
✅ *Отзыв успешно отправлен!* 🎉

⭐ *Ваша оценка:* {order['rating']} звезд
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
            
        # Логируем успешную отправку
        logging.info(f"Отзыв отправлен продавцу {SELLER_ID} от пользователя {order['user_id']}")
            
    except Exception as e:
        logging.error(f"Ошибка отправки отзыва: {e}")
        # В случае ошибки все равно показываем успешное сообщение пользователю
        await update.message.reply_text(
            "✅ *Отзыв успешно отправлен!* 🎉\n\n"
            "Спасибо за ваше мнение! Ваш отзыв очень важен для нас!",
            parse_mode='Markdown'
        )

# Возврат в главное меню
async def back_to_main(query, context: ContextTypes.DEFAULT_TYPE):
    user = query.from_user
    welcome_text = f"""
✨ *С возвращением, {user.first_name}!* ✨

🌟 *Что у нас есть:*
• Покупка Telegram Stars по выгодному курсу
• Мгновенное получение звезд
• Безопасные сделки

💫 *Курс:* 1 звезда = {RATE} рубля

🚀 *Выберите действие:*
    """
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Если сообщение от продавца и у него есть активный чат
    if user_id == SELLER_ID and user_id in active_chats:
        chat_info = active_chats[user_id]
        customer_id = chat_info['customer_id']
        
        try:
            # Отправляем сообщение покупателю
            seller_message = f"""
💬 *Сообщение от продавца:*

{text}

---
💎 *По вопросам заказа обращайтесь к продавцу*
            """
            
            await context.bot.send_message(
                chat_id=customer_id,
                text=seller_message,
                parse_mode='Markdown'
            )
            
            # Подтверждаем продавцу, что сообщение отправлено
            await update.message.reply_text(
                f"✅ *Сообщение отправлено покупателю!*\n\n"
                f"👤 Покупатель: @{chat_info['customer_username']}\n"
                f"💬 Ваше сообщение: {text}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения покупателю: {e}")
            await update.message.reply_text(
                "❌ *Не удалось отправить сообщение покупателю.*\n"
                "Возможно, покупатель заблокировал бота.",
                parse_mode='Markdown'
            )
        return
    
    # Обработка подтверждения username
    if 'awaiting_username_confirmation' in context.user_data:
        order_id = context.user_data['awaiting_username_confirmation']
        success = await confirm_username(update, context, order_id, text)
        if success:
            del context.user_data['awaiting_username_confirmation']
        return
    
    # Обработка изменения количества звезд
    if 'awaiting_stars_amount' in context.user_data:
        order_id = context.user_data['awaiting_stars_amount']
        
        try:
            stars_amount = int(text)
            
            if stars_amount < MIN_STARS:
                await update.message.reply_text(
                    f"❌ *Ошибка!*\n\n"
                    f"Покупка строго от {MIN_STARS} звезд!\n"
                    f"Введите число больше или равно {MIN_STARS}",
                    parse_mode='Markdown'
                )
                return
            
            await show_order_with_updated_amount(update, context, order_id, stars_amount)
            del context.user_data['awaiting_stars_amount']
                
        except ValueError:
            await update.message.reply_text(
                "❌ *Неверный формат!*\n\n"
                "Пожалуйста, введите целое число (например: 100, 250, 500)",
                parse_mode='Markdown'
            )
        return
    
    # Обработка отзыва
    if 'awaiting_review' in context.user_data:
        order_id = context.user_data['awaiting_review']
        # Очищаем сразу, чтобы избежать повторной обработки
        del context.user_data['awaiting_review']
        await handle_review(update, context, order_id, text)
        return
    
    # Обработка чека/квитанции (просто пересылаем продавцу)
    if update.message.photo or update.message.document:
        # Ищем активный заказ пользователя
        user_order = None
        current_order_id = None
        for order_id, order in orders.items():
            if order['user_id'] == user_id and order['status'] == 'waiting_payment':
                user_order = order
                current_order_id = order_id
                break
        
        if user_order and current_order_id:
            # Пересылаем медиа продавцу
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=SELLER_ID,
                    photo=update.message.photo[-1].file_id,
                    caption=f"📸 Чек от @{user_order['confirmed_username']}\n"
                           f"⭐ Заказ: {user_order['stars_amount']} звезд\n"
                           f"💰 Сумма: {user_order['stars_amount'] * RATE:.1f} руб.",
                    reply_markup=seller_payment_keyboard(current_order_id)
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=SELLER_ID,
                    document=update.message.document.file_id,
                    caption=f"📄 Квитанция от @{user_order['confirmed_username']}\n"
                           f"⭐ Заказ: {user_order['stars_amount']} звезд\n"
                           f"💰 Сумма: {user_order['stars_amount'] * RATE:.1f} руб.",
                    reply_markup=seller_payment_keyboard(current_order_id)
                )
            
            await update.message.reply_text(
                "✅ *Чек/квитанция отправлена продавцу!*\n\n"
                "⏳ Ожидайте подтверждения оплаты.",
                parse_mode='Markdown'
            )

# Основная функция
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_message))
    
    print("Бот запущен! 🚀")
    application.run_polling()

if __name__ == "__main__":
    main()