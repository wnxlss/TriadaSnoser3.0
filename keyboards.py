from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config
from datetime import datetime


def main_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💎 Функционал", callback_data='report'),
        InlineKeyboardButton(text="👤 Профиль", callback_data='profile'),
        InlineKeyboardButton(text="🏪 Магазин", callback_data='shop'),
        InlineKeyboardButton(text="⚡ Рефералы", callback_data='referral'),
        InlineKeyboardButton(text="📜 История", callback_data='report_history'),
        InlineKeyboardButton(text="❓ Информация", callback_data='info'),
        InlineKeyboardButton(text="🎁 Промокоды", callback_data='promo'),
        InlineKeyboardButton(text="🔍 Узнать дату регистрации", callback_data='reganah') 
    )
    builder.adjust(1, 2, 2, 2, 1)  
    return builder.as_markup()


def history_keyboard(current_page, total_pages):
    builder = InlineKeyboardBuilder()
    
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="Назад", callback_data=f"history_page_{current_page - 1}"))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Далее", callback_data=f"history_page_{current_page + 1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="back"))
    return builder.as_markup()

def ai_back_button():
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data="exit_ai")
    return builder.as_markup()

def report_library_menu():
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="Telethon", 
        callback_data='report_link_telethon'
    ))
    
    builder.add(InlineKeyboardButton(
        text="Pyrogram", 
        callback_data='report_link_pyrogram'
    ))
    
    builder.row(InlineKeyboardButton(
        text="Что выбрать?", 
        callback_data='library_info'
    ))
    
    builder.row(InlineKeyboardButton(
        text="Назад", 
        callback_data='report'
    ))
    
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def library_info_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Telethon", callback_data='report_link_telethon'),
        InlineKeyboardButton(text="Pyrogram", callback_data='report_link_pyrogram'),
        InlineKeyboardButton(text="Назад", callback_data='report_link')
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def miniapp_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Зеркала", url="https://triada-snos.vercel.app/")
    return builder.as_markup()

def email_attachment_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Прикрепить", callback_data='email_with_attachment'),
        InlineKeyboardButton(text="❌ Пропустить", callback_data='email_without_attachment'),
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def telegraph_reason_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Спам", callback_data='telegraph_reason_spam'),
        InlineKeyboardButton(text="Нарушение авторских прав", callback_data='telegraph_reason_copyright'),
        InlineKeyboardButton(text="Порнография", callback_data='telegraph_reason_pornography'),
        InlineKeyboardButton(text="Насилие", callback_data='telegraph_reason_violence'),
        InlineKeyboardButton(text="Другое", callback_data='telegraph_reason_other'),
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(1, 1, 1, 1, 1, 1)
    return builder.as_markup()

def back_button():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Назад", callback_data='back'))
    return builder.as_markup()

def channel_subscribe():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="1️⃣ Подпишись", url=config.bot_channel_link),
        InlineKeyboardButton(text="2️⃣ Подпишись", url=config.bot_channel_link2),
        InlineKeyboardButton(text="🔍 Проверить", callback_data='check_subscription'),
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def email_target_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="abuse@telegram.org", callback_data='email_abuse'),
        InlineKeyboardButton(text="dmca@telegram.org", callback_data='email_dmca'),
        InlineKeyboardButton(text="security@telegram.org", callback_data='email_security'),
        InlineKeyboardButton(text="support@telegram.org", callback_data='email_support'),
        InlineKeyboardButton(text="recovery@telegram.org", callback_data='email_recovery'),
        InlineKeyboardButton(text="stopCA@telegram.org", callback_data='email_stopca'), 
        InlineKeyboardButton(text="Все адреса", callback_data='all_mail'), 
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(1, 1, 1, 1, 1, 1)
    return builder.as_markup()

def promo_check_prof():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Проверить", callback_data='check_promo_bio'),
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(1, 1)
    return builder.as_markup()

def shop_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🪙 Crypto Bot (USD)", callback_data='shop_usd'),
        InlineKeyboardButton(text="⭐ Telegram Stars", callback_data='shop_stars'), 
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(1)
    return builder.as_markup()

def shop_usd_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=f"⚡ 1 день | {config.subscribe_1_day_usd}$", callback_data='buy_sub_usd_1'),
        InlineKeyboardButton(text=f"⚡ 7 дней | {config.subscribe_7_days_usd}$", callback_data='buy_sub_usd_2'),
        InlineKeyboardButton(text=f"💎 Премиум | {config.subscribe_premium}$ [-35%]", callback_data='buy_sub_usd_8'),
        InlineKeyboardButton(text=f"⚡ 30 дней | {config.subscribe_30_days_usd}$", callback_data='buy_sub_usd_4'),
        InlineKeyboardButton(text=f"⚡ Навсегда | {config.subscribe_infinity_days_usd}$", callback_data='buy_sub_usd_6'),
        InlineKeyboardButton(text="Назад", callback_data='shop')
    )
    builder.adjust(2, 1, 2, 1)
    return builder.as_markup()

def shop_stars_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="1 день | 100 ⭐", callback_data='buy_sub_XTR_1'),
        InlineKeyboardButton(text="7 дней | 300 ⭐", callback_data='buy_sub_XTR_2'),
        InlineKeyboardButton(text="🔥 Премиум | 1550 ⭐ [-35%]", callback_data='buy_sub_XTR_8'),
        InlineKeyboardButton(text="30 дней | 600 ⭐", callback_data='buy_sub_XTR_4'),
        InlineKeyboardButton(text="Навсегда | 1000 ⭐", callback_data='buy_sub_XTR_6'),
        InlineKeyboardButton(text="Назад", callback_data='shop')
    )
    builder.adjust(2, 1, 2, 1)
    return builder.as_markup()

def payment_menu(invoice_url, invoice_id, amount, currency='USD', method='crypto'):
    builder = InlineKeyboardBuilder()
    currency_symbol = '$' if currency == 'USD' else '₽'
    
    builder.add(
        InlineKeyboardButton(text="💳 Оплатить", url=invoice_url),
        InlineKeyboardButton(text="🔄 Проверить", callback_data=f'check_payment_{invoice_id}_{method}'),
        InlineKeyboardButton(text="❌ Отмена", callback_data='cancel_payment')
    )
    builder.adjust(2, 1)
    
    return builder.as_markup()

def get_auth_sessions_kb():
    from report_service.session_manager import list_sessions
    
    builder = InlineKeyboardBuilder()
    
    try:
        sessions = list_sessions()
        
        if sessions:
            for s in sessions[:20]:  
                display_name = s
                if len(s) > 10:  
                    display_name = s[-0:] 
                
                builder.add(InlineKeyboardButton(
                    text=f"{display_name}", 
                    callback_data=f"auth_info_{s}"
                ))
            builder.adjust(1)
        else:
            builder.add(InlineKeyboardButton(
                text="❌ Нет сессий", 
                callback_data="no_sessions"
            ))
    except Exception as e:
        builder.add(InlineKeyboardButton(
            text="❌ Ошибка загрузки", 
            callback_data="no_sessions"
        ))
    
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="auth_refresh_phones"))
    builder.row(InlineKeyboardButton(text="➕ Добавить сессию", callback_data="admin_add_session"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data='back_admin'))
    
    return builder.as_markup()

def info_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Канал", url=config.bot_channel_link),
        InlineKeyboardButton(text="Чат", url=config.chat),
        InlineKeyboardButton(text="Поддержка", url=f"tg://user?id={config.idd}"),
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def no_sub_key():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🏪 Магазин", callback_data='shop'),
        InlineKeyboardButton(text="Назад", callback_data='back')
    )
    builder.adjust(1, 1)
    return builder.as_markup()


def admin_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Выдать подписку", callback_data="add_subscribe"),
        InlineKeyboardButton(text="Снять подписку", callback_data="clear_subscribe"),
        InlineKeyboardButton(text="Выдать премиум", callback_data="add_premium"),
        InlineKeyboardButton(text="Снять премиум", callback_data="remove_premium"),
        InlineKeyboardButton(text="Рассылка", callback_data="send_all"),
        InlineKeyboardButton(text="Промокод", callback_data="create_promo"),
        InlineKeyboardButton(text="Сессия", callback_data="admin_add_session"), 
        InlineKeyboardButton(text="Зайти", callback_data='admin_auth_list'),
        InlineKeyboardButton(text="Проверить сессии", callback_data="check_sessions"),
        InlineKeyboardButton(text="Проверить почты", callback_data="check_emails"),
        )
    builder.adjust(2, 2, 1, 1, 2, 2) 
    return builder.as_markup()


def email_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить отправку", callback_data='confirm_email_send'),
        InlineKeyboardButton(text="⚡ Улучшить через ИИ", callback_data='improve_text_groq'), 
        InlineKeyboardButton(text="✏️ Редактировать текст", callback_data='edit_email_text'),
        InlineKeyboardButton(text="❌ Отменить", callback_data='cancel_email_send')
    )
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def broadcast_type_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📝 Просто текст", callback_data='broadcast_text'),
        InlineKeyboardButton(text="📝 Текст + кнопка", callback_data='broadcast_button'),
        InlineKeyboardButton(text="Назад", callback_data='back_admin')
    )
    builder.adjust(1)
    return builder.as_markup()

def report_method_menu():
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="👥 Метод Группа", 
        callback_data='report_link'
    ))
    
    builder.add(InlineKeyboardButton(
        text="📧 Метод Email", 
        callback_data='report_email'
    ))
    
    builder.add(InlineKeyboardButton(
        text="📄 Метод Telegra.ph", 
        callback_data='report_telegraph'
    ))
    
    builder.add(InlineKeyboardButton(text="Назад", callback_data='back'))
    builder.adjust(2, 1, 1)  
    
    return builder.as_markup()

def mirror_menu():    
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="Создать зеркало", callback_data="mirror_create"))
    builder.add(InlineKeyboardButton(text="Назад", callback_data="back"))
    
    builder.adjust(1, 1)
    return builder.as_markup()

def no_subscription_message(method_type='regular'):
    builder = InlineKeyboardBuilder()
    
    if method_type == 'premium':
        builder.add(InlineKeyboardButton(
            text="💎 Купить Premium", 
            callback_data='buy_sub_usd_8'
        ))
    else:
        builder.add(InlineKeyboardButton(
            text="🏪 Перейти в магазин", 
            callback_data='shop'
        ))
    
    builder.add(InlineKeyboardButton(text="Назад к методам", callback_data='report'))
    builder.adjust(1)
    
    return builder.as_markup()