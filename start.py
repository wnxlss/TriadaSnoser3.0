import os
import sys
import asyncio
import logging
import uuid
import socks
import random 
import string
import signal
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
import re
from aiogram.types import FSInputFile

import config
from keyboards import *
from referral import Referrals
from database import Database
from keyboards import miniapp_kb
from telethon import TelegramClient, errors

from payment.usd_payment import UsdPayment
from report_service.telethon_report import Reporter
from report_service.pyrogram_report import PyrogramReporter
from report_service.email_rep import Mailer
from report_service.link_parser import LinkParser
from report_service.telegraph_report import TelegraphReporter
from report_service import session_manager
from groq import Groq
groq_client = Groq(api_key=config.GROQ_API_KEY)

from report_service.session_manager import list_sessions, get_client, send_code, verify_code, verify_2fa
from mirror_database import mirror_db
from mirror import mirror_manager

bot = Bot(token=config.TOKEN)
mirror_manager.set_main_bot_token(config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()
payments = UsdPayment()
rep_msg = Reporter(api_list=config.API) 
pyro_rep = PyrogramReporter(api_list=config.API, groq_api_key=config.GROQ_API_KEY) 

referral_system = Referrals(db)
email_rep = Mailer()

telegraph_reporter = TelegraphReporter(
    email_rep=email_rep,
    groq_api_key=config.GROQ_API_KEY
)



referral_system = Referrals(db)
email_rep = Mailer()

telegraph_reporter = TelegraphReporter(
    email_rep=email_rep,
    groq_api_key=config.GROQ_API_KEY
)

def get_reg_date(user_id: int) -> str:
    data = [
        (50000000, "Январь 2013"),
        (100000000, "Январь 2014"),
        (150000000, "Май 2015"),
        (200000000, "Декабрь 2015"),
        (300000000, "Июль 2016"),
        (500000000, "Январь 2018"),
        (700000000, "Октябрь 2018"),
        (950000000, "Июль 2019"),
        (1200000000, "Март 2020"),
        (1450000000, "Октябрь 2020"),
        (1600000000, "Январь 2021"),
        (1850000000, "Май 2021"),
        (2100000000, "Сентябрь 2021"),
        (5000000000, "Июль 2022"),
        (5500000000, "Январь 2023"),
        (6300000000, "Март 2023"),
        (7000000000, "Декабрь 2023"),
        (7500000000, "Февраль 2024"),
        (8000000000, "Октябрь 2024"),
        (8500000000, "Январь 2025")
    ]
    
    for limit, date_str in data:
        if user_id < limit:
            return date_str
    return "2025+"

def generate_captcha():
   
    num1 = random.randint(1, 50)
    num2 = random.randint(1, 50)
    operation = random.choice(['+', '-'])
    
    if operation == '+':
        result = num1 + num2
    else:
        
        if num1 < num2:
            num1, num2 = num2, num1
        result = num1 - num2
    
    captcha_text = f"{num1} {operation} {num2}"
    return captcha_text, str(result)

class CaptchaStates(StatesGroup):
    waiting_for_captcha = State()

class MirrorStates(StatesGroup):
    waiting_for_token = State()

class ReganaStates(StatesGroup):
    waiting_for_id = State()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

banner = '<a href=\"https://i.ibb.co/nqyQSFvk/IMG-1223.jpg\">&#8203</a>'
magazin = '<a href=\"https://i.ibb.co/nqyQSFvk/IMG-1223.jpg\">&#8203</a>'
profilep = '<a href=\"https://i.ibb.co/nqyQSFvk/IMG-1223.jpg\">&#8203</a>'
information = '<a href=\"https://i.ibb.co/nqyQSFvk/IMG-1223.jpg\">&#8203</a>'
promocod = '<a href=\"https://i.ibb.co/nqyQSFvk/IMG-1223.jpg\">&#8203</a>'


kanal_url = "https://t.me/wbank_ru"
sozdatel_url = "https://t.me/Wbankmng"
site_url = "https://triada-snos.vercel.app/"

class States:
    def __init__(self):
        self.waiting_for_confirm = {}
        self.waiting_for_link = {}  
        self.waiting_for_user_id = {}  
        self.waiting_for_days = {}  
        self.user_currency = {}
        self.waiting_for_email_subject = {} 
        self.waiting_for_email_confirm = {}  
        self.email_data = {}
        self.waiting_for_email_body = {}
        self.waiting_for_email_target = {}
        self.waiting_for_broadcast_text = {}  
        self.admin_message_id = {}
        self.waiting_for_broadcast_button = {} 
        self.payment_invoices = {} 
        self.broadcast_text = None
        self.broadcast_type = None
        self.waiting_for_promo_code = {}
        self.waiting_for_promo_create = {}
        self.waiting_for_premium_user_id = {}  
        self.waiting_for_premium_days = {}   
        self.waiting_for_email_attachment = {} 
        self.email_attachments = {}  
        self.waiting_for_ai_question = {}     
        self.waiting_for_telegraph_link = {}
        self.telegraph_report_data = {}
        self.waiting_for_session_broadcast_text = {}
        self.waiting_for_account_info = {}  

states = States()

async def check_channel_subscription(user_id):
    try:
        
        member1 = await bot.get_chat_member(config.bot_channel_id, user_id)
        subscribed1 = member1.status in ['member', 'administrator', 'creator']
        
       
        member2 = await bot.get_chat_member(config.bot_channel_id2, user_id)
        subscribed2 = member2.status in ['member', 'administrator', 'creator']
        
        return subscribed1 and subscribed2
    except Exception as e:
        logging.error(f"Error checking subscription: {str(e)}")
        return False

async def check_subscription_wrapper(user_id, callback=None, message=None):
    is_subscribed = await check_channel_subscription(user_id)
    if not is_subscribed:
        if callback:
            await callback.message.edit_text(
                text=f"❌ <b>{banner}Для использования функции необходимо подписаться на канал!</b>",
                reply_markup=channel_subscribe(),
                parse_mode="HTML",
               link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
            )
        elif message:
            await message.answer_photo(
                photo=config.banner_url,
                text="❌ <b>Для использования функции необходимо подписаться на канал!</b>",
                reply_markup=channel_subscribe(),
                parse_mode="HTML"
            )
        return False
    return True


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "@нет"
    
   
    args = message.text.split()
    if len(args) > 1:
        payload = args[1]
        if payload.startswith('pay_'):
            parts = payload.split('_')
            if len(parts) == 3:
                sub_type = parts[1]
                original_user_id = int(parts[2])
                
                if original_user_id != user_id:
                    await message.answer("❌ Неверный идентификатор пользователя для оплаты")
                    return
                
                prices_map = {'100': 1, '2': 300, '4': 600, '6': 1000, '8': 1550}
                days_map = {'1': 1, '2': 7, '4': 30, '6': 9999, '8': 9999}
                
                amount = prices_map.get(sub_type, 100)
                days = days_map.get(sub_type, 1)
                
                await message.answer_invoice(
                    title=f"Подписка на {days} дн.",
                    description=f"Покупка подписки на {days} дней",
                    prices=[types.LabeledPrice(label="XTR", amount=amount)],
                    provider_token="", 
                    payload=f"sub_{sub_type}_{user_id}", 
                    currency="XTR",
                    reply_markup=None 
                )
                return
    
    if message.from_user.is_bot:
        await message.answer("❌ Боты не могут использовать этого бота!")
        return
    
    if db.needs_captcha(user_id):
        captcha_text, correct_answer = generate_captcha()
        
        await state.set_state(CaptchaStates.waiting_for_captcha)
        await state.update_data(captcha_answer=correct_answer, user_data={
            'user_id': user_id,
            'username': username,
            'is_new_user': not db.user_exists(user_id)
        })
        
        await message.answer(
            f"<b>🤖 Проверка на бота</b>\n\n"
            f"<b>Решите пример и отправьте ответ в чат:</b>\n"
            f"<code>{captcha_text} = ?</code>\n\n"
            f"<i>Введите только число (например: 7)</i>",
            parse_mode="HTML"
        )
        return
    
    await process_start_after_captcha(message, state, bot, user_id, username)

async def process_start_after_captcha(message: Message, state: FSMContext, bot: Bot, user_id: int, username: str):
   
    is_new_user = not db.user_exists(user_id)
    db.add_user(user_id)
    db.set_captcha_passed(user_id)
    
    if is_new_user:
        try:
            log_message = (
                f"⚡ <b>Новый пользователь</b>\n\n"
                f"<b>ID: {user_id}</b>\n"
                f"<b>Username: {username}</b>\n"
                f"<b>Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}</b>"
            )
            await bot.send_message(config.bot_logs, log_message, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка при отправке лога нового пользователя: {str(e)}")
    
    await referral_system.process_referral_start(message, bot)
    
    try:
        welcome_pinned = db.check_welcome_pinned(user_id)
        
        if not welcome_pinned:
            welcome_text = "<b>🌐 Если основной бот временно недоступен, воспользуйтесь одним из зеркал ниже.</b>"
            
            welcome_msg = await message.answer(
                text=welcome_text,
                reply_markup=miniapp_kb(),
                parse_mode="HTML"
            )
            
            try:
                await bot.pin_chat_message(
                    chat_id=message.chat.id,
                    message_id=welcome_msg.message_id,
                    disable_notification=True
                )
                db.set_welcome_pinned(user_id)
            except Exception as e:
                logging.error(f"Ошибка закрепления: {e}")
    
        
        banner = '<a href=\"https://i.ibb.co/nqyQSFvk/IMG-1223.jpg\">&#8203</a>'
        kanal_url = "https://t.me/wbank_ru"
        sozdatel_url = "https://t.me/Wbankmng"
        site_url = "https://triada-snos.vercel.app/"
        
        caption_text = (
            f"<blockquote><b>{banner}Главное меню</b></blockquote>\n\n"
            f"<b><a href='{kanal_url}'>Канал</a> | <a href='{sozdatel_url}'>Разработчик</a> | <a href='{site_url}'>Сайт</a></b>"
        )
  
        await message.answer(
            text=caption_text,
            reply_markup=main_menu(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            )
        )
        
       
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error in start command: {str(e)}")
        
        await message.answer(
            text="<b>Добро пожаловать!</b>",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
        await state.clear()

@dp.message(CaptchaStates.waiting_for_captcha)
async def process_captcha_answer(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    
    try:
        user_answer = message.text.strip()
        
        state_data = await state.get_data()
        correct_answer = state_data.get('captcha_answer')
        user_data = state_data.get('user_data', {})
        
        if not correct_answer:
            await message.answer(
                "❌ <b>Проверка истекла. Нажмите /start для повторной попытки.</b>",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        if user_answer == correct_answer:
         
            await state.clear()
            
           
            await message.reply(
                "✅ <b>Проверка пройдена!</b>",
                parse_mode="HTML"
            )
            
           
            user_id = user_data.get('user_id', user_id)
            username = user_data.get('username', f"@{message.from_user.username}")
            
          
            await process_start_after_captcha(
                message, 
                state, 
                bot, 
                user_id,
                username
            )
        else:
           
            captcha_text, new_answer = generate_captcha()
            await state.update_data(captcha_answer=new_answer)
            
            await message.reply(
                f"<b>❌ Неправильно!</b>\n\n"
                f"<b>Попробуйте еще раз:</b>\n"
                f"<code>{captcha_text} = ?</code>\n\n"
                f"<i>Введите только число (например: 7)</i>",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logging.error(f"Error in captcha processing: {e}")
        await message.reply(
            "❌ <b>Произошла ошибка. Нажмите /start для повторной попытки.</b>",
            parse_mode="HTML"
        )
        await state.clear()

@dp.callback_query(F.data == 'check_subscription')
async def check_subscription(callback: CallbackQuery):
    is_subscribed = await check_channel_subscription(callback.from_user.id)
    
    if is_subscribed:
        

        await callback.message.edit_text(
            text=(
                f"<blockquote><b>{banner}Главное меню</b></blockquote>\n\n"
                f"<b><a href='{kanal_url}'>Канал</a> | <a href='{sozdatel_url}'>Разработчик</a> | <a href='{site_url}'>Сайт</a></b>"
            ),
            reply_markup=main_menu(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
    else:
        
        await callback.message.edit_text(
            text=f"❌ <b>{banner}Вы  не подписаны на канал!</b>\n\n<b>Пожалуйста, подпишитесь на каналы ниже чтобы продолжить:</b>",
            reply_markup=channel_subscribe(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )

@dp.callback_query(F.data == 'profile')
async def profile(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    subscription = db.get_subscription(callback.from_user.id)
    premium_status = db.get_premium_status(callback.from_user.id)
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Нет"
    first = f"{callback.from_user.first_name}"
    id = f"{callback.from_user.id}"
    
    
    if subscription and subscription > datetime.now():
        days_left = (subscription - datetime.now()).days
        sub_status = f"{days_left} дней"
    else:
        sub_status = "Истекла"
    
    premium_text = "Да" if premium_status['is_premium'] else "Нет"
    
    await callback.message.edit_text(
        text=(
            f"<blockquote><b>{profilep}👤 Ваш профиль</b></blockquote>\n\n"
            f"<b>◾ Имя:</b> {first}\n"
            f"<b>◾ ID:</b> <code>{id}</code>\n"
            f"<b>◾ Username:</b> {username}\n"
            f"<b>◾ Премиум:</b> {premium_text}\n\n"
            f"<b>⏳ Подписка:</b> {sub_status}"),
        reply_markup=mirror_menu(), 
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'info')
async def info_handler(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await callback.message.edit_text(
        text=f"<blockquote>{information}❓ <b>Информация</b></blockquote>\n\n<blockquote><b>◾ Creator: @scambaseRF\n◾ Admin: @Wbankmng\n\n🌐 Version: <code>2.01f.26</code>\n🟢 Last update: <code>25.02.2026</code></b></blockquote>",
        reply_markup=info_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'mirror_create')
async def mirror_create_start(callback: CallbackQuery, state: FSMContext):
    mirrors_count = mirror_db.get_user_mirrors_count(callback.from_user.id)
    if mirrors_count >= config.MAX_MIRRORS_PER_USER:
        await callback.message.edit_text(
            f"❌ <b>{banner}Максимум {config.MAX_MIRRORS_PER_USER} зеркал</b>",
            parse_mode="HTML",
            reply_markup=back_button(),
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            )
        )
        return
    
    await state.update_data(
        edit_chat_id=callback.message.chat.id,
        edit_message_id=callback.message.message_id
    )
    
    await callback.message.edit_text(
        f"<blockquote><b>{banner}🔧 Создание зеркала</b></blockquote>\n\n"        
        f"<b>Лимит: {mirrors_count}/{config.MAX_MIRRORS_PER_USER}</b>\n\n"
        f"<b>Отправьте токен бота от @BotFather:</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )
    await state.set_state(MirrorStates.waiting_for_token)

@dp.message(MirrorStates.waiting_for_token)
async def process_mirror_token(message: Message, state: FSMContext):
    token = message.text.strip()
    await message.delete()
    
    data = await state.get_data()
    edit_chat_id = data.get('edit_chat_id')
    edit_message_id = data.get('edit_message_id')
    
    try:
        test_bot = Bot(token=token)
        me = await test_bot.get_me()
        await test_bot.session.close()
        
        mirror_id = mirror_db.create_mirror(
            user_id=message.from_user.id,
            bot_token=token,
            bot_username=me.username,
            bot_name=me.full_name
        )
        
        asyncio.create_task(mirror_manager.run_mirror_bot(mirror_id, token))
        
        if edit_chat_id and edit_message_id:
            await bot.edit_message_text(
                f"✅ <b>{banner}Зеркало создано!</b>\n\n"
                f"• Бот: @{me.username}\n"
                f"• ID: <code>{mirror_id}</code>\n"
                f"• Статус: 🟢 Активен",
                chat_id=edit_chat_id,
                message_id=edit_message_id,
                reply_markup=back_button(),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    show_above_text=True,
                    prefer_large_media=True
                )
            )
        else:
            await message.answer(
                f"✅ <b>Зеркало создано!</b>\n\n"
                f"• Бот: @{me.username}\n"
                f"• ID: <code>{mirror_id}</code>\n"
                f"• Статус: 🟢 Активен",
                reply_markup=back_button(),
                parse_mode="HTML"
            )
        
        mirror_db.add_log(mirror_id, "mirror_started", {
            "user_id": message.from_user.id,
            "username": message.from_user.username
        })
        
    except Exception as e:
        error_text = f"❌ Ошибка: {str(e)}"
        if edit_chat_id and edit_message_id:
            await bot.edit_message_text(
                error_text,
                chat_id=edit_chat_id,
                message_id=edit_message_id,
                reply_markup=back_button(),
                parse_mode="HTML"
            )
        else:
            await message.answer(error_text, reply_markup=back_button(), parse_mode="HTML")
    
    await state.clear()

@dp.callback_query(F.data == 'shop')
async def shop(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{magazin}🏪 Магазин</b></blockquote>\n\n<b>Выберите удобный способ оплаты\nДоступный способ: 🪙 CryptoBot | Stars ⭐</b>",
        reply_markup=shop_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'shop_usd')
async def shop_usd(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    states.user_currency[user_id] = 'USD'
    
    await callback.message.edit_text(
        text=(
           f"<blockquote><b>{magazin}🪙 Crypto Bot</b></blockquote>\n\n"
           "<blockquote><b>🔖 Цены:\n"
           f"└─ 1 день - {config.subscribe_1_day_usd}$\n"
           f"└─ 7 дней - {config.subscribe_7_days_usd}$\n"
           f"└─ 30 дней - {config.subscribe_30_days_usd}$\n"
           f"└─ Навсегда - {config.subscribe_infinity_days_usd}$\n\n"
           f"└─ 🔥 Премиум - {config.subscribe_premium}$ [-35%]</b></blockquote>\n\n"
            "<b>❓ Если возникли проблемы с оплатой, обратитесь в поддержку.</b>"),
        reply_markup=shop_usd_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )


@dp.callback_query(F.data == 'promo')
async def promo_handler(callback: CallbackQuery, bot: Bot):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    states.waiting_for_promo_code[callback.from_user.id] = {
        'message_id': callback.message.message_id,
        'chat_id': callback.message.chat.id,
        'step': 'input_code'
    }
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{promocod}🎁 Активация промокода</b></blockquote>\n\n<b>Введите промокод:</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_promo_code))
async def process_promo_code(message: Message, bot: Bot):
    user_id = message.from_user.id
    promo_data = states.waiting_for_promo_code.get(user_id)
    
    if not promo_data:
        return
    
    promo_code = message.text.strip().upper()
    
    try:
        await message.delete()
        
      
        promo_data['promo_code'] = promo_code
        promo_data['step'] = 'check_bio'
        
        await bot.edit_message_text(
            chat_id=promo_data['chat_id'],
            message_id=promo_data['message_id'],
            text=(
                f"<b>{promocod}🎁 Активация промокода: {promo_code}</b>\n\n"
                f"<b>Для активации необходимо добавить в описание профиля:</b>\n"
                f"<code>Лучший сн0сер - @triada_snoserbot</code>\n\n"
                f"<b>После добавления нажмите кнопку 'Проверить':</b>"
            ),
            reply_markup=promo_check_prof(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
            
    except Exception as e:
        logging.error(f"Error processing promo code: {str(e)}")
        await bot.edit_message_text(
            chat_id=promo_data['chat_id'],
            message_id=promo_data['message_id'],
            text="❌ <b>Произошла ошибка при обработке промокода</b>",
            reply_markup=back_button(),
            parse_mode="HTML"
        )

@dp.callback_query(F.data == 'check_promo_bio')
async def check_promo_bio_handler(callback: CallbackQuery, bot: Bot):
   
    user_id = callback.from_user.id
    promo_data = states.waiting_for_promo_code.get(user_id)
    
    if not promo_data or promo_data.get('step') != 'check_bio':
        await callback.message.edit_text(
            text=f"❌ <b>{promocod}Сначала введите промокод!</b>",
            reply_markup=back_button(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
        return
    
    activation_success = False  
   
    try:
     
        user = await bot.get_chat(user_id)
        bio = user.bio or ""
        
       
        required_texts = [
            "Лучший сн0сер - @triada_snoserbot",
            "Лучший сн0сер - @triada_snoserbot",
            "Лучший сносер - @triada_snoserbot",
            "Лучший сн0сер @triada_snoserbot",
            "Лучший сносер @triada_snoserbot",
        ]
        
        bio_has_required = any(req_text.lower() in bio.lower() for req_text in required_texts)
        
        if bio_has_required:
          
            promo_code = promo_data['promo_code']
            
            await callback.message.edit_text(
                text=f"🔄 <b>{promocod}Активируем промокод...</b>",
                parse_mode="HTML"
            )
            
            success, result = db.use_promocode(promo_code, user_id)
            
            if success:
                days = result
                new_expiry = db.update_subscription(user_id, days)
                expiry_date = new_expiry.strftime("%d.%m.%Y %H:%M")
                
                await callback.message.edit_text(
                    text=(
                        f"✅ <b>{promocod}Промокод активирован!</b>\n\n"
                        f"<b>• Промокод:</b> <code>{promo_code}</code>\n"
                        f"<b>• Дней подписки:</b> {days}\n"
                        f"<b>• Окончание подписки:</b> {expiry_date}"
                    ),
                    reply_markup=back_button(),
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
                )
                
                await bot.send_message(
                    config.bot_logs,
                    f"Пользователь {user_id} активировал промокод {promo_code}\n"
                    f"Получил подписку на {days} дней\n"
                    f"Окончание: {expiry_date}"
                )
                
                activation_success = True 
                
            else:
                await callback.message.edit_text(
                    text=f"❌ <b>{result}</b>",
                    reply_markup=back_button(),
                    parse_mode="HTML"
                )
            
        else:
            await callback.message.edit_text(
                text=(
                    f"❌ <b>{promocod}Текст не найден в описании профиля!</b>\n\n"
                    f"<b>Промокод:</b> <code>{promo_data['promo_code']}</code>\n\n"
                    f"<b>Требуемый текст:</b>\n"
                    f"<code>Лучший сн0сер - @triada_snoserbot</code>\n\n"
                    f"<b>Ваше описание:</b>\n"
                    f"<code>{bio if bio else 'Пусто'}</code>\n\n"
                    f"<b>Добавьте текст и нажмите 'Проверить' снова</b>"
                ),
                reply_markup=promo_check_prof(),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
            )
            
    except Exception as e:
        logging.error(f"Error checking user bio: {str(e)}")
        await callback.message.edit_text(
            text=f"❌ <b>{promocod}Не удалось проверить описание профиля. Попробуйте позже.</b>",
            reply_markup=back_button(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
    finally:
     
        if activation_success:
            states.waiting_for_promo_code.pop(user_id, None)

@dp.callback_query(F.data == 'shop_usd_8')
async def shop_premium_direct(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    
    await callback.message.edit_text(
        text=f"🔄 <b>{magazin}Создаем счет...</b>",
        parse_mode="HTML"
    )
    
    invoice = payments.crypto_payment.create_invoice(
        amount=config.subscribe_premium, 
        currency='USD'
    )
    
    if not invoice or not invoice.get('success', False):
        error_msg = invoice.get('error', 'Неизвестная ошибка') if invoice else 'Ошибка создания счета'
        await callback.message.edit_text(
            text=f"❌ <b>Ошибка:</b>\n{error_msg}",
            parse_mode="HTML",
            reply_markup=back_button()
        )
        return
    
    db.add_payment(
        invoice_id=invoice['invoice_id'],
        user_id=user_id,
        sub_type='premium',
        days=9999,
        price=config.subscribe_premium,
        currency='USD',
        method='crypto',
        message_chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    
    states.payment_invoices[invoice['invoice_id']] = {
        'user_id': user_id,
        'sub_type': 'premium',
        'days': 9999,
        'price': config.subscribe_premium,
        'currency': 'USD',
        'method': 'crypto',
        'created_at': datetime.now(),
        'paid': False,
        'message_chat_id': callback.message.chat.id,
        'message_id': callback.message.message_id
    }
    
    payment_text = (
        f"<b>{magazin}💎 Оплата премиум подписки</b>\n\n"
        f"<b>• Стоимость:</b> <code>{config.subscribe_premium}$</code>\n"
        f"<b>• Период:</b> Навсегда\n\n"
        f"<b>⚠️ Счет будет удален через 30 минут</b>"
    )
    
    await callback.message.edit_text(
        text=payment_text,
        reply_markup=payment_menu(
            invoice['pay_url'],
            invoice['invoice_id'],
            config.subscribe_premium,
            'USD',
            'crypto'
        ),
        parse_mode="HTML"
    )
    
    asyncio.create_task(delete_invoice_after_delay(invoice['invoice_id'], 1800))


@dp.callback_query(F.data == 'referral_refresh')
async def referral_refresh_handler(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
   
    await referral_system.show_referral_stats(callback)

@dp.callback_query(F.data == 'referral')
async def referral_menu_handler(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await referral_system.show_referral_stats(callback)


@dp.callback_query(F.data == 'shop_stars')
async def shop_stars(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    await callback.message.edit_text(
        text=(
           f"<blockquote><b>{magazin}⭐ Telegram Stars</b></blockquote>\n\n"
           "<blockquote><b>🔖 Цены:\n"
           f"└─ 1 день - 100 ⭐\n"
           f"└─ 7 дней - 300 ⭐\n"
           f"└─ 30 дней - 600 ⭐\n"
           f"└─ Навсегда - 1000 ⭐\n\n"
           f"└─ 🔥 Премиум - 1550 ⭐ [-35%]</b></blockquote>\n\n"
            "<b>❓ Если возникли проблемы с оплатой, обратитесь в поддержку.</b>"),
        reply_markup=shop_stars_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )


@dp.callback_query(F.data.startswith('buy_sub_XTR_'))
async def process_stars_payment(callback: CallbackQuery):
    parts = callback.data.split('_')
    sub_type = parts[3]
    
   
    prices_map = {'100': 1, '2': 300, '4': 600, '6': 1000, '8': 1550}
    days_map = {'1': 1, '2': 7, '4': 30, '6': 9999, '8': 9999}
    
    amount = prices_map.get(sub_type, 100)
    days = days_map.get(sub_type, 1)

   
    await callback.message.answer_invoice(
        title=f"Подписка на {days} дн.",
        description=f"Покупка подписки на {days} дней",
        prices=[types.LabeledPrice(label="XTR", amount=amount)],
        provider_token="", 
        payload=f"sub_{sub_type}_{callback.from_user.id}", 
        currency="XTR",
        reply_markup=None 
    )
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split('_')
    sub_type = parts[1] 
    user_id = int(parts[2])
    
    days_map = {'1': 1, '2': 7, '4': 30, '6': 9999, '8': 9999}
    days = days_map.get(sub_type, 1)
    
  
    if sub_type in ['6', '8']:
        db.set_premium_subscription(user_id, days) 
        text = (
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"💎 <b>Вам активирована Премиум подписка!</b>"
        )
    else:
      
        new_expiry = db.update_subscription(user_id, days)
        text = (
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"Ваша подписка продлена на {days} дн.\n"
            f"До: {new_expiry.strftime('%d.%m.%Y %H:%M')}"
        )
    
    await message.answer(
        text,
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )
    
 
    log_status = "ПРЕМИУМ" if sub_type in ['6', '8'] else f"{days} дн."
    await bot.send_message(config.bot_logs, f"⭐ Юзер {user_id} купил {log_status} за Звезды.")

@dp.callback_query(F.data.startswith('buy_sub_'))
async def process_subscription(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    parts = callback.data.split('_')
    currency = parts[2]  
    sub_type = parts[3]
    
    user_id = callback.from_user.id
    
    
    sub_prices = {
        '1': config.subscribe_1_day_usd,
        '2': config.subscribe_7_days_usd,
        '4': config.subscribe_30_days_usd,
        '6': config.subscribe_infinity_days_usd
    }
    currency_symbol = '$'
    payment_method = 'crypto'
    
    sub_days = {
        '1': 1,
        '2': 7,
        '4': 30,
        '6': 9999
    }
    
    price = sub_prices.get(sub_type, 0)
    days = sub_days.get(sub_type, 0)
    
    await callback.message.edit_text(
        text=f"🔄 <b>{magazin}Создаем счет...</b>",
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )
    
   
    invoice = payments.crypto_payment.create_invoice(amount=price, currency='USD')
    
    if not invoice or not invoice.get('success', False):
        error_msg = invoice.get('error', 'Неизвестная ошибка') if invoice else 'Ошибка создания счета'
        await callback.message.edit_text(
            text=f"❌ <b>Ошибка:</b>\n{error_msg}",
            parse_mode="HTML",
            reply_markup=back_button()
        )
        return
    
    
    db.add_payment(
        invoice_id=invoice['invoice_id'],
        user_id=user_id,
        sub_type=sub_type,
        days=days,
        price=price,
        currency=currency.upper(),
        method=payment_method,
        message_chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    
    
    states.payment_invoices[invoice['invoice_id']] = {
        'user_id': user_id,
        'sub_type': sub_type,
        'days': days,
        'price': price,
        'currency': currency.upper(),
        'method': payment_method,
        'created_at': datetime.now(),
        'paid': False,
        'message_chat_id': callback.message.chat.id,
        'message_id': callback.message.message_id
    }
    
    payment_text = (
        f"<b>{magazin}💳 Оплата подписки</b>\n\n"
        f"<b>• Стоимость:</b> <code>{price}{currency_symbol}</code>\n"
        f"<b>• Период:</b> {days} дней\n\n"
        f"<b>⚠️ Счет будет удален через 30 минут</b>\n\n"
        f"<b>Нажмите кнопку ниже для оплаты:</b>"
    )
    
    await callback.message.edit_text(
        text=payment_text,
        reply_markup=payment_menu(
            invoice['pay_url'],
            invoice['invoice_id'],
            price,
            currency.upper(),
            payment_method
        ),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )
    
   
    asyncio.create_task(delete_invoice_after_delay(invoice['invoice_id'], 1800))


async def delete_invoice_after_delay(invoice_id, delay_seconds):
   
    await asyncio.sleep(delay_seconds)
    
 
    if invoice_id in states.payment_invoices:
        invoice_data = states.payment_invoices[invoice_id]
        
        
        if not invoice_data.get('paid'):
            states.payment_invoices.pop(invoice_id, None)
            db.delete_payment(invoice_id)
            
            try:
                await bot.edit_message_text(
                    chat_id=invoice_data['message_chat_id'],
                    message_id=invoice_data['message_id'],
                    text=f"❌ <b>{magazin}Время оплаты истекло</b>\n\nСчет был удален. Создайте новый заказ.",
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        ),
                    reply_markup=back_button()
                )
            except Exception as e:
                logging.error(f"Error updating message after invoice expiration: {str(e)}")

@dp.callback_query(F.data.startswith('check_payment_'))
async def check_payment_status(callback: CallbackQuery):
    parts = callback.data.split('_')
    if len(parts) < 4:
        await callback.message.edit_text(
            text=f"❌ <b>{magazin}Ошибка в формате запроса</b>",
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        ),
            reply_markup=back_button()
        )
        return
        
    invoice_id = parts[2]
    method = parts[3]
    
    logging.info(f"Checking payment: invoice_id={invoice_id}, method={method}")
    
    invoice_data = states.payment_invoices.get(invoice_id)
    
    if not invoice_data:
        invoice_data = db.get_payment(invoice_id)
        if invoice_data:
            states.payment_invoices[invoice_id] = invoice_data
            logging.info(f"Restored payment from database: {invoice_id}")
    
    if not invoice_data:
        await callback.message.edit_text(
            text=f"❌ <b>Данные платежа не найдены</b>\n\nПопробуйте создать новый заказ.",
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        ),
            reply_markup=back_button()
        )
        return
    
    try:
        await callback.message.edit_text(
            text=f"{magazin}<b>🔄 Проверяем платеж...</b>",
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
        
        user_id = invoice_data['user_id']
        days = invoice_data['days']
        price = invoice_data['price']
        currency = invoice_data['currency']
        payment_method = invoice_data['method']
        
        logging.info(f"Processing payment for user {user_id}, days {days}, method {payment_method}")
        
        is_paid = False
        for attempt in range(3):
            logging.info(f"Payment check attempt {attempt + 1}")
            
            is_paid = payments.crypto_payment.check_payment(invoice_id)
            
            logging.info(f"Payment status: {is_paid}")
            
            if is_paid:
                break
            elif attempt < 2:
                await asyncio.sleep(5)
        
        if is_paid:
            if not db.user_exists(user_id):
                db.add_user(user_id)
            
            if invoice_data['sub_type'] == 'premium':
                db.set_premium_subscription(user_id, days)
                
                await callback.message.edit_text(
                    text=(
                        f"💎 <b>{magazin}Премиум подписка активирована!</b>\n\n"
                        f"<b>• Оплачено:</b> <code>{price}$</code>\n"
                        f"<b>• Статус:</b> Премиум пользователь"
                    ),
                    reply_markup=back_button(),
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
                )
            else:
                new_expiry = db.update_subscription(user_id, days)
                expiry_date = new_expiry.strftime("%d.%m.%Y %H:%M")
                
                db.update_payment_status(invoice_id, True)
                invoice_data['paid'] = True
                states.payment_invoices[invoice_id] = invoice_data
                
                currency_symbol = '$'
                
                await callback.message.edit_text(
                    text=(
                        f"✅ <b>{magazin}Подписка активирована!</b>\n\n"
                        f"<b>• Период:</b> {days} дней\n"
                        f"<b>• Оплачено:</b> <code>{price}{currency_symbol}</code>\n"
                        f"<b>• Окончание:</b> {expiry_date}"
                    ),
                    reply_markup=back_button(),
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
                )
            
            await bot.send_message(
                config.bot_logs,
                f"🛒 Пользователь {user_id} купил {'премиум ' if invoice_data['sub_type'] == 'premium' else ''}подписку на {days} дней за {price}{'$' if currency == 'USD' else '₽'}\n"
                f"📅 {'Статус: Премиум' if invoice_data['sub_type'] == 'premium' else f'Окончание: {expiry_date}'}"
            )
            
        else:
            currency_symbol = '$'
            payment_text = (
                f"<b>{magazin}💳 Оплата {'премиум ' if invoice_data['sub_type'] == 'premium' else ''}подписки</b>\n\n"
                f"<b>• Стоимость:</b> <code>{price}{currency_symbol}</code>\n"
                f"<b>• Период:</b> {days} дней\n\n"
                f"❌ <b>Оплата еще не поступила</b>"
            )
            
            await callback.message.edit_text(
                text=payment_text,
                reply_markup=back_button(),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
            )
            
    except Exception as e:
        logging.error(f"Error checking payment: {str(e)}")
        await callback.message.edit_text(
            text=f"❌ <b>Ошибка проверки:</b>\n{str(e)}",
            parse_mode="HTML",
            reply_markup=back_button()
        )

async def clean_paid_invoice_after_delay(invoice_id, delay_seconds):
    
    await asyncio.sleep(delay_seconds)
    states.payment_invoices.pop(invoice_id, None)

@dp.callback_query(F.data == 'cancel_payment')
async def cancel_payment(callback: CallbackQuery):
   
    invoice_id = None
    if callback.message.reply_markup and callback.message.reply_markup.inline_keyboard:
        for row in callback.message.reply_markup.inline_keyboard:
            for button in row:
                if button.callback_data and 'check_payment_' in button.callback_data:
                    try:
                        parts = button.callback_data.split('_')
                        if len(parts) >= 4:
                            invoice_id = parts[2]
                            break
                    except Exception as e:
                        logging.error(f"Error extracting invoice_id: {e}")
    
    if invoice_id and invoice_id in states.payment_invoices:
        states.payment_invoices.pop(invoice_id, None)
        logging.info(f"Cancelled payment: {invoice_id}")
    
    await callback.message.edit_text(
        text=f"❌ <b>{magazin}Оплата отменена</b>",
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        ),
        reply_markup=back_button()
    )

@dp.callback_query(F.data == 'report')
async def report_start(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
   
    subscription = db.get_subscription(callback.from_user.id)
    premium_status = db.get_premium_status(callback.from_user.id)
    
    has_regular_sub = subscription and subscription > datetime.now()
    has_premium = premium_status['is_premium']
    
  
    can_report, wait_time = await rep_msg.can_report(callback.from_user.id)
    wait_message = ""
    if not can_report:
        minutes = wait_time // 60
        seconds = wait_time % 60
        wait_message = f"\n\n<b>⏳ Таймер: {minutes} мин {seconds} сек</b>"
    
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{banner}💎 Функционал</b></blockquote>",
        reply_markup=report_method_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'premium_only')
async def premium_only_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        text=f"<blockquote><b>{banner}💎 Premium функция</b></blockquote>\n\n"
             f"<b>Метод Email доступен только для премиум подписки!</b>",
        reply_markup=premium_only_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'report_link')
async def report_link_start(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    subscription = db.get_subscription(callback.from_user.id)
    premium_status = db.get_premium_status(callback.from_user.id)
    
    has_regular_sub = subscription and subscription > datetime.now()
    has_premium = premium_status['is_premium']
    
    if not has_regular_sub and not has_premium:
        await callback.answer("🔒 Требуется подписка!", show_alert=True)
        return
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{banner}⚡ Выберите метод отправки</b></blockquote>\n\n"
        f"<b>📱 Telethon</b> — двухэтапная система с опциями, больше сессий\n"
        f"<b>🔥 Pyrogram</b> — альтернативный метод, обход блокировок",
        reply_markup=report_library_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )


@dp.callback_query(F.data == 'report_link_telethon')
async def report_link_telethon_start(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    states.waiting_for_link[user_id] = {
        'message_id': callback.message.message_id,
        'chat_id': callback.message.chat.id,
        'method': 'telethon',
        'step': 'waiting_for_link'
    }
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{banner}📱 Метод Telethon</b></blockquote>\n\n"
             f"<b>🔗 Отправьте ссылку на сообщение (https://t.me/…/123):</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )


@dp.callback_query(F.data == 'report_link_pyrogram')
async def report_link_pyrogram_start(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    states.waiting_for_link[user_id] = {
        'message_id': callback.message.message_id,
        'chat_id': callback.message.chat.id,
        'method': 'pyrogram',
        'step': 'waiting_for_link'
    }
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{banner}🔥 Метод Pyrogram</b></blockquote>\n\n"
             f"<b>🔗 Отправьте ссылку на сообщение (https://t.me/…/123):</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.message(F.text.startswith(('https://t.me/', 'http://t.me/')))
async def process_report_link_simple(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    if user_id not in states.waiting_for_link:
        return
    
    link_data = states.waiting_for_link[user_id]
    if link_data.get('step') != 'waiting_for_link':
        return
    
    try:
        await message.delete()
        
        link = message.text.strip()
        message_id = link_data['message_id']
        chat_id = link_data['chat_id']
        method = link_data.get('method', 'telethon')
        reason = 'spam'
        
        if '/c/' in link:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"<b>{banner}❌ Ошибка:</b>\nЭто ссылка на приватный чат! Репорты можно отправлять только в публичные группы.",
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    show_above_text=True,
                    prefer_large_media=True
                ),
                reply_markup=back_button()
            )
            if user_id in states.waiting_for_link:
                del states.waiting_for_link[user_id]
            return
        
        clean_url = link.split('?')[0]
        path_parts = clean_url[len('https://t.me/'):].split('/')
        
        if len(path_parts) < 2:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"<b>{banner}❌ Ошибка:</b>\nЭто ссылка на канал или пользователя! Нужна ссылка на конкретное сообщение.",
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    show_above_text=True,
                    prefer_large_media=True
                ),
                reply_markup=back_button()
            )
            if user_id in states.waiting_for_link:
                del states.waiting_for_link[user_id]
            return
        
        chat_username, msg_id = LinkParser.extract_username_and_message_id(link)
        
        subscription = db.get_subscription(user_id)
        premium_status = db.get_premium_status(user_id)
        
        has_regular_sub = subscription and subscription > datetime.now()
        has_premium = premium_status['is_premium']
        
        if not has_regular_sub and not has_premium:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"<b>❌ Требуется подписка!</b>",
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    show_above_text=True,
                    prefer_large_media=True
                ),
                reply_markup=back_button()
            )
            if user_id in states.waiting_for_link:
                del states.waiting_for_link[user_id]
            return
        
        if method == 'pyrogram':
            can_report, wait_time = await pyro_rep.can_report(user_id)
            reporter = pyro_rep
            method_name = "Pyrogram"
        else:
            can_report, wait_time = await rep_msg.can_report(user_id)
            reporter = rep_msg
            method_name = "Telethon"
        
        if not can_report:
            minutes = wait_time // 60
            seconds = wait_time % 60
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"<b>{banner}⏳ Подождите {minutes} мин {seconds} сек</b>",
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    is_disabled=False,
                    show_above_text=True,
                    prefer_large_media=True
                ),
                reply_markup=back_button()
            )
            if user_id in states.waiting_for_link:
                del states.waiting_for_link[user_id]
            return
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"<blockquote><b>{banner}👥 Запущен метод ({method_name})</b></blockquote>",
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            )
        )
        
        stats = await reporter.report_message(
            chat_username=chat_username,
            message_id=msg_id,
            user_id=user_id,
            username=message.from_user.username,
            reason_key=reason
        )
        
        if stats.get('error'):
            raise Exception(stats['error'])
        
        offender_info = stats.get('offender_info', {})
        message_link = f"https://t.me/{chat_username}/{msg_id}"
        
        
        if stats.get('log_file') and os.path.exists(stats['log_file']):
            try:
                from report_service.report_logger import ReportLogger
                
                logger = ReportLogger()
                html_report_path = logger.save_report(
                    user_id=user_id,
                    method=method_name,
                    stats=stats,
                    target_link=link,
                    username=message.from_user.username
                )
                
                if os.path.exists(html_report_path):
                    document = FSInputFile(html_report_path)
                    await bot.send_document(
                        chat_id=user_id,
                        document=document,
                        caption=f"<b>Отчет {method_name}</b>\n\nОткрывать в браузере!",
                        parse_mode="HTML"
                    )
            except Exception as e:
                logging.error(f"Ошибка при отправке отчета: {e}")
        
        result_text = (
            f"<blockquote><b>{banner}✅ Отправка завершена!\n\n"
            f"Метод: {method_name}\n\n"
            f"ID: {offender_info.get('id', 'N/A')}\n"
            f"Username: {offender_info.get('username', 'Нет')}\n\n"
            f"Сообщение: {message_link}\n\n"
            f"⚠️ Бот отправил запросы на блокировку. Далее решение принимает администрация Telegram.</b></blockquote>"
        )
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=result_text,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            ),
            reply_markup=back_button(),
            disable_web_page_preview=True
        )
        
        log_message = (
            f"<b>{banner}🚀 Завершена отправка ({method_name})</b>\n\n"
            f"<b>ID:</b> <code>{offender_info.get('id', 'N/A')}</code>\n"
            f"<b>Username:</b> {offender_info.get('username', 'Нет')}\n\n"
            f"<b>🔗 Сообщение:</b> <a href='{message_link}'>ссылка</a>\n\n"
            f"<b>🟢 Успешно: {stats.get('valid', 0)}</b>\n"
            f"<b>🔴 Ошибок: {stats.get('invalid', 0)}</b>\n\n"
            f"<b>👤 Отправитель:</b> {user_id} (@{message.from_user.username})"
        )
        
        await bot.send_message(
            config.bot_logs,
            log_message,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            ),
            disable_web_page_preview=True
        )
        
        db.add_report_history(
            user_id,
            message_link,
            reason,
            f"{method_name}"
        )
        
        if user_id in states.waiting_for_link:
            del states.waiting_for_link[user_id]
            
    except ValueError as e:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"<blockquote><b>✅ Бот успешно отправил запросы: {message_link}</b></blockquote>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_button()
        )
        if user_id in states.waiting_for_link:
            del states.waiting_for_link[user_id]
    except Exception as e:
        logging.error(f"Ошибка при отправке репортов: {str(e)}")
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"<blockquote><b>✅ Бот успешно отправил запросы: {message_link}</b></blockquote>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_button()
        )
        if user_id in states.waiting_for_link:
            del states.waiting_for_link[user_id]

@dp.callback_query(F.data == 'library_info')
async def library_info_handler(callback: CallbackQuery):
   
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    info_text = (
    f"<blockquote><b>{banner}📚 Информация о методах</b></blockquote>\n\n"
    f"<b>◾ Telethon (Новый механизм):</b>\n"
    f"<blockquote><b>• Использует двухэтапную систему ReportRequest с опциями\n"
    f"• Получает список причин от Telegram и автоматически выбирает нужную\n"
    f"• Поддерживает вложенные опции (подпричины)\n"
    f"• Официально работает с новым API жалоб\n"
    f"• Больше сессий в базе и стабильная работа</b></blockquote>\n\n"
    f"<b>◾ Pyrogram (Классический):</b>\n"
    f"<blockquote><b>• Использует стандартный Report с фиксированными причинами\n"
    f"• Работает через raw функции Telegram\n"
    f"• Другие дата-центры\n"
    f"• Может работать там, где Telethon недоступен</b></blockquote>\n\n"
    f"<b>💡 Рекомендация:</b>\n"
    f"Если один метод не работает, попробуйте другой"
)
    
    await callback.message.edit_text(
        text=info_text,
        reply_markup=library_info_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'report_email')
async def report_email_start(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    
    premium_status = db.get_premium_status(callback.from_user.id)
    if not premium_status['is_premium']:
        await callback.answer("💎 Требуется премиум подписка!", show_alert=True)
        return
    
    states.waiting_for_email_subject.pop(callback.from_user.id, None)
    states.waiting_for_email_body.pop(callback.from_user.id, None)
    states.email_data.pop(callback.from_user.id, None)
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{banner}📦 Выберите получателя</b></blockquote>",
        reply_markup=email_target_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

async def _process_email_target(callback: CallbackQuery, target_email: str, bot: Bot):
    user_id = callback.from_user.id
    states.email_data[user_id] = {
        'photo_message_id': callback.message.message_id,
        'chat_id': callback.message.chat.id,
        'target': target_email,
        'step': 'subject'
    }
    
    await callback.message.edit_text(
        text=f"<b>{banner}📝 Введите тему письма:</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'all_mail')
async def email_all_targets_handler(callback: CallbackQuery, bot: Bot):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await _process_email_target(callback, 'all', bot)

@dp.callback_query(F.data == 'email_abuse')
async def email_abuse_handler(callback: CallbackQuery, bot: Bot):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await _process_email_target(callback, 'abuse@telegram.org', bot)

@dp.callback_query(F.data == 'email_support')
async def email_support_handler(callback: CallbackQuery, bot: Bot):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await _process_email_target(callback, 'support@telegram.org', bot)

@dp.callback_query(F.data == 'email_dmca')
async def email_dmca_handler(callback: CallbackQuery, bot: Bot):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await _process_email_target(callback, 'dmca@telegram.org', bot)

@dp.callback_query(F.data == 'email_recovery')
async def email_sms_handler(callback: CallbackQuery, bot: Bot):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await _process_email_target(callback, 'recovery@telegram.org', bot)

@dp.callback_query(F.data == 'email_stopca')
async def email_sms_handler(callback: CallbackQuery, bot: Bot):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    await _process_email_target(callback, 'stopCA@telegram.org', bot)

@dp.message(F.text & (F.from_user.id.in_(states.email_data) & 
                     (F.from_user.id.not_in(states.waiting_for_broadcast_text) & 
                      F.from_user.id.not_in(states.waiting_for_broadcast_button))))
async def handle_email_report_steps(message: Message, bot: Bot):
    user_id = message.from_user.id
    email_data = states.email_data.get(user_id)
    
    if not email_data:
        return
    
    if email_data['step'] == 'subject':
        email_data['subject'] = message.text.strip()
        email_data['step'] = 'body'
        
        try:
            await message.delete()
            await bot.edit_message_text(
                chat_id=email_data['chat_id'],
                message_id=email_data['photo_message_id'],
                text=f"<b>{banner}📝 Введите текст письма:</b>",
                reply_markup=back_button(),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
            )
        except Exception as e:
            logging.error(f"Error editing photo text: {str(e)}")
            
    elif email_data['step'] == 'body':
        email_data['body'] = message.text.strip()
        email_data['step'] = 'attachment'  
        
        try:
            await message.delete()
            
            await bot.edit_message_text(
                chat_id=email_data['chat_id'],
                message_id=email_data['photo_message_id'],
                text=f"<b>{banner}📎 Хотите прикрепить скриншот к письму?</b>",
                reply_markup=email_attachment_menu(),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
            )
            
        except Exception as e:
            logging.error(f"Error showing attachment menu: {str(e)}")


@dp.callback_query(F.data == 'email_with_attachment')
async def email_with_attachment_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    email_data = states.email_data.get(user_id)
    
    if not email_data:
        await callback.answer("❌ Данные не найдены!", show_alert=True)
        return
    
    email_data['step'] = 'attachment_file'
    email_data['has_attachment'] = True
    
    await callback.message.edit_text(
        text=f"<b>{banner}📎 Прикрепите скриншот (изображение):</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'email_without_attachment')
async def email_without_attachment_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    email_data = states.email_data.get(user_id)
    
    if not email_data:
        await callback.answer("❌ Данные не найдены!", show_alert=True)
        return
    
    email_data['step'] = 'confirm'
    email_data['has_attachment'] = False
    email_data['attachment'] = None
    
    
    await show_email_confirmation(callback, email_data)


@dp.message(F.photo & F.from_user.id.in_(states.email_data))
async def process_email_attachment(message: Message):
    user_id = message.from_user.id
    email_data = states.email_data.get(user_id)
    
    if not email_data or email_data.get('step') != 'attachment_file':
        return
    
    try:
        
        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        
        email_data['attachment'] = {
            'file_id': file_id,
            'file_path': file_path
        }
        email_data['step'] = 'confirm'
        
        await message.delete()
        
      
        await show_email_confirmation(None, email_data)
        
    except Exception as e:
        logging.error(f"Error processing attachment: {str(e)}")
        await bot.edit_message_text(
            chat_id=email_data['chat_id'],
            message_id=email_data['photo_message_id'],
            text=f"❌ <b>{banner}Ошибка при обработке скриншота. Попробуйте снова.</b>",
            reply_markup=back_button(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )


async def show_email_confirmation(callback, email_data):
    user_id = callback.from_user.id if callback else None
    chat_id = email_data['chat_id']
    message_id = email_data['photo_message_id']
    
   
    if email_data['target'] == 'all':
        target_display = "все адреса"
    else:
        target_display = email_data['target']
        
    confirm_text = (
        f"<b>{banner}🔄 Подтверждение отправки</b>\n\n"
        f"<b>📬 Получатель:</b> {target_display}\n"
        f"<b>📎 Скриншот:</b> {'✅ Прикреплен' if email_data.get('has_attachment') else '❌ Нет'}\n\n"
        f"<b>◾ Тема:</b>\n<blockquote>{email_data['subject']}</blockquote>\n\n"
        f"<b>◾ Текст письма:</b>\n<blockquote>{email_data['body'][:500]}{'...' if len(email_data['body']) > 500 else ''}</blockquote>\n\n"
        "<b>✅ Подтвердите отправку или отредактируйте текст</b>"
    )
    
    if callback:
        await callback.message.edit_text(
            text=confirm_text,
            reply_markup=email_confirm_keyboard(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
    else:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=confirm_text,
            reply_markup=email_confirm_keyboard(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )


@dp.callback_query(F.data == 'confirm_email_send')
async def confirm_email_send(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    email_data = states.email_data.get(user_id)
    
    if not email_data or email_data['step'] != 'confirm':
        await callback.answer("❌ Данные не найдены!", show_alert=True)
        return
    
    try:
        start_time = datetime.now()
        
        await callback.message.edit_text(
            text=f"<blockquote><b>{banner}📧 Запущено метод (Email)</b></blockquote>\n\n<b>Пожалуйста ожидайте...</b>",
            reply_markup=None,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
        
        attachment_data = email_data.get('attachment') if email_data.get('has_attachment') else None
        
        stats = await email_rep.send_email_report(
            user_id=user_id,
            target_email=email_data['target'],
            subject=email_data['subject'],
            body=email_data['body'],
            attachment_data=attachment_data  
        ) 
        db.add_report_history(
            callback.from_user.id, 
            email_data['target'], 
            email_data['subject'], 
            "Email"
        )
        
        if stats.get('error'):
            result_text = f"<b>❌ Ошибка:</b>\n<b>└─ ⚠️ {stats['error']}</b>"
        else:
            result_text = (
                f"<blockquote><b>{banner}✅ Отправка завершена!</b></blockquote>\n\n"
                "<b>📂 Метод: Email</b>\n\n"
                f"<b>🟢 Успешно отправлено: {stats['success']}</b>\n"
                f"<b>🔴 Не удалось отправить: {stats['failed']}</b>\n\n"
                "<b>⚠️ Бот отправил запросы на блокировку. Далее решение принимает администрация Telegram.</b>"
            )
        
        await callback.message.edit_text(
            text=result_text,
            reply_markup=back_button(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )

        if stats.get('error'):
            log_message = f"❌ <b>Ошибка отправки почты</b>\n<b>└─ 📂 Метод: Mail</b>\n\n<b>👤 Отправитель: {user_id}</b>\n<b>❌ Ошибка: {stats['error']}</b>"
        else:
            log_message = (
                f"🚀 <b>{banner}Завершена отправка</b>\n"
                f"<b>└─ 📂 Метод: Mail</b>\n\n"
                f"<b>Отправитель: {user_id}</b>\n"
                f"<b>Аккаунтов: {stats['total']}</b>\n"
                f"<b>🟢 Успешно: {stats['success']}</b>\n"
                f"<b>🔴 Ошибок: {stats['failed']}</b>\n\n"
                f"<b>◾ Тема:</b>\n<blockquote>{email_data['subject']}</blockquote>\n\n"
                f"<b>◾ Текст письма:</b>\n"
                f"<blockquote expandable>{email_data['body'][:500]}{'...' if len(email_data['body']) > 500 else ''}</blockquote>"
            )
        
        await bot.send_message(
            config.bot_logs,
            log_message,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
        
    except Exception as e:
        logging.error(f"Error processing email report: {str(e)}")
        await callback.message.edit_text(
            text=f"<b>❌ Произошла ошибка:</b>\n{str(e)}",
            reply_markup=back_button(),
            parse_mode="HTML"
        )
    finally:
        states.email_data.pop(user_id, None)


@dp.callback_query(F.data == 'edit_email_text')
async def edit_email_text(callback: CallbackQuery):
    user_id = callback.from_user.id
    email_data = states.email_data.get(user_id)
    
    if not email_data:
        await callback.answer("❌ Данные не найдены!", show_alert=True)
        return
    
    email_data['step'] = 'body'
    
    await callback.message.edit_text(
        text=f"<b>{banner}📝 Введите новый текст письма:</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data == 'cancel_email_send')
async def cancel_email_send(callback: CallbackQuery):
    user_id = callback.from_user.id
    states.email_data.pop(user_id, None)
    
    await callback.message.edit_text(
        text=f"❌ <b>{banner}Отправка письма отменена</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )



@dp.callback_query(F.data == 'back')
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    current_state = await state.get_state()
    
    if current_state:
        await state.clear()
    
    try:
        session_manager.session_auth.cleanup_auth(user_id)
    except:
        pass

  
    states.waiting_for_email_target.pop(user_id, None)
    states.waiting_for_email_subject.pop(user_id, None)
    states.waiting_for_email_body.pop(user_id, None)
    states.email_data.pop(user_id, None)
    states.waiting_for_link.pop(user_id, None)
    states.waiting_for_user_id.pop(user_id, None)
    states.waiting_for_days.pop(user_id, None)
    states.waiting_for_broadcast_text.pop(user_id, None)
    states.waiting_for_broadcast_button.pop(user_id, None)
    states.waiting_for_confirm.pop(user_id, None)
    states.waiting_for_promo_code.pop(user_id, None)
    states.waiting_for_promo_create.pop(user_id, None)
    states.waiting_for_premium_user_id.pop(user_id, None)
    states.waiting_for_premium_days.pop(user_id, None)
    states.waiting_for_email_attachment.pop(user_id, None)
    states.waiting_for_account_info.pop(user_id, None)
    

   
    await callback.message.edit_text(
        text=(
            f"<blockquote><b>{banner}Главное меню</b></blockquote>\n\n"
            f"<b><a href='{kanal_url}'>Канал</a> | <a href='{sozdatel_url}'>Разработчик</a> | <a href='{site_url}'>Сайт</a></b>"
        ),
        reply_markup=main_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )



@dp.callback_query(F.data == 'reganah')
async def reganah_cmd(callback: CallbackQuery, state: FSMContext):
 
    await state.clear()
    
    await callback.message.edit_text(
        f"<blockquote><b>{banner}🔍 Узнать дату регистрации</b></blockquote>\n\n<b>Введите @username пользователя:</b>",
        reply_markup=back_button(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

    await state.set_state(ReganaStates.waiting_for_id)
    await state.update_data(message_id=callback.message.message_id)

@dp.message(ReganaStates.waiting_for_id)
async def process_reganah(message: Message, state: FSMContext):
    input_data = message.text.strip().replace("@", "").replace("https://t.me/", "")
    
    data = await state.get_data()
    original_message_id = data.get('message_id')
    
    try:
        await message.delete()
    except:
        pass
    
    try:
        search_query = int(input_data) if input_data.isdigit() else input_data
    except ValueError:
        search_query = input_data
    
    sessions = list_sessions()
    if not sessions:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=original_message_id,
            text="❌ <b>Временно недоступно</b>",
            reply_markup=back_button(),
            parse_mode="HTML"
        )
        await state.clear()
        return

    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=original_message_id,
            text=f"<blockquote><b>{banner}🔎 Начинаю поиск, ожидайте...</b></blockquote>",
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
        )
        
        client = await get_client(sessions[0])
        async with client:
            try:
                user = await client.get_entity(search_query)
                user_id = user.id
                first_name = user.first_name or "Удаленный аккаунт"
            except:
                from telethon.tl.functions.users import GetFullUserRequest
                full = await client(GetFullUserRequest(search_query))
                user = full.users[0]
                user_id = user.id
                first_name = user.first_name or "Удаленный аккаунт"

            username = f"@{user.username}" if hasattr(user, 'username') and user.username else "нет"
            phone = user.phone if hasattr(user, 'phone') and user.phone else "скрыт"
            premium = "Да" if hasattr(user, 'premium') and user.premium else "Нет"
            date_str = get_reg_date(user_id)
            
            result_text = (
                f"<blockquote><b>{banner}🔍 Результат:</b></blockquote>\n\n"
                f"<b>Имя:</b> {first_name}\n"
                f"<b>ID:</b> <code>{user_id}</code>\n"
                f"<b>Username:</b> {username}\n"
                f"<b>Телефон:</b> <code>{phone}</code>\n"
                f"<b>Premium:</b> {premium}\n\n"
                f"<b>Регистрация:</b> ~ {date_str}"
            )
            
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=original_message_id,
                text=result_text,
                reply_markup=back_button(),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
            )
            
    except Exception as e:
        logging.error(f"Regana error: {e}")
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=original_message_id,
            text="❌ <b>Пользователь не найден</b>",
            reply_markup=back_button(),
            parse_mode="HTML"
        )
    finally:
        await state.clear()

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id in config.ADMINS:
        db_stats = db.get_stats_data()
        
       
        telethon_sessions = len([f for f in os.listdir("tele_sessions") if f.endswith('.session')]) if os.path.exists("tele_sessions") else 0
        
       
        pyro_sessions_count = pyro_rep.get_sessions_count()
        
        text = (
            "<b>🎱 Админка</b>\n\n"
            f"<blockquote><b>• Пользователей: {db_stats['total_users']}\n"
            f"• Обычных подписок: {db_stats['active_regular']}\n"
            f"• Премиум подписок: {db_stats['active_premium']}\n"
            f"• Telethon сессий: {telethon_sessions}\n"
            f"• Pyrogram сессий: {pyro_sessions_count}\n"
            f"• Почт в боте: {db_stats['emails_count']}</b></blockquote>"
        )
        await message.answer(text, reply_markup=admin_menu(), parse_mode="HTML")

@dp.callback_query(F.data == 'add_subscribe')
async def add_subscribe_handler(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    states.waiting_for_user_id[callback.from_user.id] = 'add_sub'
    await callback.message.edit_text(
        text="Введите ID пользователя для выдачи подписки:"
    )

@dp.callback_query(F.data == 'clear_subscribe')
async def clear_subscribe_handler(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    states.waiting_for_user_id[callback.from_user.id] = 'clear_sub'
    await callback.message.edit_text(
        text="Введите ID пользователя для отмены подписки:"
    )

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_user_id))
async def process_user_id_for_subscription(message: Message):
    user_id = message.from_user.id
    action = states.waiting_for_user_id.get(user_id)
    
    if not action or user_id not in config.ADMINS:
        return
    
    try:
        target_user_id = int(message.text.strip())
        
        if action == 'add_sub':
            states.waiting_for_days[user_id] = target_user_id
            await message.answer(
                text="Введите количество дней для подписки:"
            )
            
        elif action == 'clear_sub':
            current_sub = db.get_subscription(target_user_id)
            
            db.clear_subscription(target_user_id)
            
            await message.answer(
                text="✅ Пользователю {user_id} отменена подписка".format(user_id=target_user_id)
            )
            
            try:
                await bot.send_message(
                    target_user_id,
                    "<b>❌ Ваша подписка была отменена администратором</b>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {str(e)}")
            
            log_text = "Админ {admin_id} отменил подписку пользователя {user_id}".format(
                admin_id=user_id,
                user_id=target_user_id
            )
            
            if current_sub and current_sub > datetime.now():
                days_left = (current_sub - datetime.now()).days
                log_text += f"\nОставалось дней: {days_left}"
            
            await bot.send_message(config.bot_logs, log_text)
            
        elif action == 'add_balance':
            states.waiting_for_balance_amount[user_id] = target_user_id
            await message.answer(
                text="Введите сумму для выдачи баланса ($):"
            )
            
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке: {str(e)}")
    finally:
        states.waiting_for_user_id.pop(user_id, None)

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_days))
async def process_days_for_subscription(message: Message):
    user_id = message.from_user.id
    target_user_id = states.waiting_for_days.get(user_id)
    
    if not target_user_id or user_id not in config.ADMINS:
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0:
            await message.answer("❌ Количество дней должно быть положительным!")
            return
        
       
        new_expiry = db.update_subscription(target_user_id, days)
        expiry_date = new_expiry.strftime("%d.%m.%Y %H:%M")
        
        await message.answer(
            text="✅ Пользователю {user_id} выдана подписка на {days} дней\nДата окончания: {expiry_date}".format(
                user_id=target_user_id, 
                days=days,
                expiry_date=expiry_date
            )
        )
        
        try:
            await bot.send_message(
                target_user_id,
                "<b>🎱 Вам выдана подписка на {days} дней\n\nДата окончания: {expiry_date}</b>".format(
                    days=days,
                    expiry_date=expiry_date),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {str(e)}")
        
        await bot.send_message(
            config.bot_logs,
            "Админ {admin_id} выдал подписку пользователю {user_id} на {days} дней\nДата окончания: {expiry_date}".format(
                admin_id=user_id,
                user_id=target_user_id,
                days=days,
                expiry_date=expiry_date
            )
        )
        
    except ValueError:
        await message.answer("❌ Некорректное количество дней!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выдаче подписки: {str(e)}")
    finally:
        states.waiting_for_days.pop(user_id, None)

@dp.callback_query(F.data == 'improve_text_groq')
async def improve_email_text(callback: CallbackQuery):
    user_id = callback.from_user.id
   
    email_data = states.email_data.get(user_id, {})
    current_body = email_data.get('body')
    subject = email_data.get('subject') 

    if not current_body:
        await callback.answer("Текст письма не найден!", show_alert=True)
        return

    await callback.message.edit_text("⏳ <b>(AI) Улучшает текст...</b>", parse_mode="HTML")

    try:
        
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system", 
                    "content": "Ты — помощник по написанию текстов. Твоя задача: улучшить текст письма, сделав его более профессиональным и убедительным. \nВАЖНО: Выведи ТОЛЬКО улучшенный текст. Не пиши 'Subject:', не пиши тему письма, не добавляй никаких вступлений или комментариев. Только само тело письма."
                },
                {"role": "user", "content": current_body}
            ],
        )
        
        improved_body = completion.choices[0].message.content.strip()

      
        states.email_data[user_id]['body'] = improved_body
        
       
        await callback.message.edit_text(
            f"🤖 <b>Текст улучшен через AI:</b>\n\n"
            f"<b>Тема:</b> <blockquote>{subject}</blockquote>\n"
            f"<b>Текст:</b>\n<blockquote>{improved_body}</blockquote>",
            reply_markup=email_confirm_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Groq Error: {e}")
        await callback.message.edit_text(
            "❌ Ошибка AI. Попробуйте позже или отправьте так.",
            reply_markup=email_confirm_keyboard()
        )


@dp.callback_query(F.data == 'report_telegraph')
async def report_telegraph_start(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    
    subscription = db.get_subscription(callback.from_user.id)
    premium_status = db.get_premium_status(callback.from_user.id)
    
    has_regular_sub = subscription and subscription > datetime.now()
    has_premium = premium_status['is_premium']
    
    if not has_regular_sub and not has_premium:
        await callback.answer("🔒 Требуется подписка!", show_alert=True)
        return
    
    can_report, wait_time = await telegraph_reporter.can_report(callback.from_user.id)
    if not can_report:
        minutes = wait_time // 60
        seconds = wait_time % 60
        await callback.message.edit_text(
            text=f"<b>{banner}⏳ Подождите {minutes} мин {seconds} сек</b>",
            reply_markup=back_button(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            )
        )
        return
    
    await callback.message.edit_text(
        text=f"<blockquote><b>{banner}⚠️ Выберите причину для репорта</b></blockquote>",
        reply_markup=telegraph_reason_menu(),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        )
    )

@dp.callback_query(F.data.startswith('telegraph_reason_'))
async def process_telegraph_reason(callback: CallbackQuery):
    if not await check_subscription_wrapper(callback.from_user.id, callback):
        return
    
    reason_map = {
        'telegraph_reason_spam': 'spam',
        'telegraph_reason_copyright': 'copyright',
        'telegraph_reason_pornography': 'pornography',
        'telegraph_reason_violence': 'violence',
        'telegraph_reason_other': 'other'
    }
    
    reason_key = reason_map.get(callback.data)
    if reason_key:
        states.waiting_for_telegraph_link[callback.from_user.id] = {
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id,
            'reason': reason_key
        }
        await callback.message.edit_text(
            text=f"<blockquote><b>{banner}📄 Метод: Telegra.ph</b></blockquote>\n\n<b>🔗 Отправьте ссылку на статью Telegra.ph:</b>\n\n<i>Пример: https://telegra.ph/Название-статьи-01-01</i>",
            reply_markup=back_button(),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            )
        )

@dp.message(F.text.startswith(('https://telegra.ph/', 'http://telegra.ph/')))
async def process_telegraph_report(message: Message, bot: Bot):
    if message.from_user.id not in states.waiting_for_telegraph_link:
        return
    
    try:
        await message.delete()
        url = message.text.strip()
        
        link_data = states.waiting_for_telegraph_link[message.from_user.id]
        message_id = link_data['message_id']
        chat_id = link_data['chat_id']
        reason = link_data.get('reason', 'spam')
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"<blockquote><b>{banner}📄 Запущен метод (Telegra.ph)</b></blockquote>\n\n<b>🔗 Ссылка: {url}</b>\n\n<b>Пожалуйста ожидайте...</b>",
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            ),
            disable_web_page_preview=True
        )
        
      
        stats = await telegraph_reporter.report_article(
            url=url,
            user_id=message.from_user.id,
            username=message.from_user.username,
            reason=reason
        )
            
        result_text = (
                f"<blockquote><b>{banner}✅ Отправка завершена!</b></blockquote>\n\n"
                "<b>📂 Метод: Telegra.ph</b>\n\n"
                f"<b>🟢 Успешно отправлено: {stats.get('success', 0)}</b>\n"
                f"<b>🔴 Не удалось отправить: {stats.get('failed', 0)}</b>\n\n"
                "<b>⚠️ Бот отправил запросы на блокировку. Далее решение принимает администрация Telegram.</b>"
            )
        
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=result_text,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            ),
            reply_markup=back_button(),
            disable_web_page_preview=True
        )
        
        
        db.add_report_history(
            message.from_user.id, 
            url, 
            reason, 
            "Telegraph (AI)"
        )
        
       
        log_message = (
            f"<b>{banner}🚀 Завершена отправка (Telegraph AI)</b>\n\n"
            f"<b>🎯 Таргет:</b>\n"
            f"<b>└─ URL: {url}</b>\n"
            f"<b>└─ Reason: {reason}</b>\n\n"
            f"<b>📊 Статистика:</b>\n"
            f"<b>└─ Всего: {stats.get('total', 0)}</b>\n"
            f"<b>└─ 🟢 Успешно: {stats.get('success', 0)}</b>\n"
            f"<b>└─ 🔴 Ошибок: {stats.get('failed', 0)}</b>\n\n"
            f"<b>👤 Отправитель: {message.from_user.id}</b>\n"
            f"<b>(@{message.from_user.username})</b>"
        )
        
        await bot.send_message(
            config.bot_logs,
            log_message,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            ),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logging.error(f"Error processing telegraph report: {str(e)}")
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"<b>❌ Произошла ошибка:</b>\n{str(e)}",
            parse_mode="HTML",
            reply_markup=back_button()
        )
    finally:
        states.waiting_for_telegraph_link.pop(message.from_user.id, None)

@dp.callback_query(F.data == 'check_sessions')
async def check_sessions_handler(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    await callback.message.edit_text(
        text="<b>Проверяю сессии...</b>",
        parse_mode="HTML"
    )
    
    try:
        stats = await rep_msg.check_sessions()
        await callback.message.edit_text(
            text=(
                "<b>Результаты проверки сессий:</b>\n\n"
                "Всего сессий: {total}\n"
                "Рабочих: {valid}\n"
                "Нерабочих: {invalid}\n\n"
                "Нерабочие сессии перемещены в папку no_work"
            ).format(**stats),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            text="<b>Ошибка при проверке сессий:</b>\n{error}".format(error=str(e)),
            parse_mode="HTML"
        )

@dp.callback_query(F.data == 'check_emails')
async def check_emails_handler(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    await callback.message.edit_text(
        text="<b>Проверяю почтовые аккаунты...</b>",
        parse_mode="HTML"
    )
    
    try:
        stats = await email_rep.check_all_accounts()
        await callback.message.edit_text(
            text=(
                "<b>Результаты проверки почт:</b>\n\n"
                "Всего почт: {total}\n"
                "Рабочих: {valid}\n"
                "Нерабочих: {invalid}\n\n"
                "Нерабочие почты перемещены в no_work.txt"
            ).format(**stats),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            text="<b>Ошибка при проверке почт:</b>\n{error}".format(error=str(e)),
            parse_mode="HTML"
        )

@dp.callback_query(F.data == 'add_premium')
async def add_premium_handler(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    states.waiting_for_premium_user_id[callback.from_user.id] = 'add_premium'
    await callback.message.edit_text(
        text="Введите ID пользователя для выдачи премиум подписки:"
    )

@dp.callback_query(F.data == 'remove_premium')
async def remove_premium_handler(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    states.waiting_for_premium_user_id[callback.from_user.id] = 'remove_premium'
    await callback.message.edit_text(
        text="Введите ID пользователя для снятия премиум подписки:"
    )

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_premium_user_id))
async def process_premium_user_id(message: Message):
    user_id = message.from_user.id
    action = states.waiting_for_premium_user_id.get(user_id)
    
    if not action or user_id not in config.ADMINS:
        return
    
    try:
        target_user_id = int(message.text.strip())
        
        if action == 'add_premium':
            states.waiting_for_premium_days[user_id] = target_user_id
            await message.answer(
                text="Введите количество дней для премиум подписки:"
            )
            
        elif action == 'remove_premium':
           
            db.remove_premium_subscription(target_user_id)
            
            await message.answer(
                text=f"✅ Пользователю {target_user_id} снята премиум подписка"
            )
            
            try:
                await bot.send_message(
                    target_user_id,
                    "<b>💎 Ваша премиум подписка была отменена администратором</b>",
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {str(e)}")
            
            await bot.send_message(
                config.bot_logs,
                f"Админ {user_id} снял премиум подписку пользователю {target_user_id}"
            )
            
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке: {str(e)}")
    finally:
        states.waiting_for_premium_user_id.pop(user_id, None)

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_premium_days))
async def process_premium_days(message: Message):
    user_id = message.from_user.id
    target_user_id = states.waiting_for_premium_days.get(user_id)
    
    if not target_user_id or user_id not in config.ADMINS:
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0:
            await message.answer("❌ Количество дней должно быть положительным!")
            return
        
        premium_until = db.set_premium_subscription(target_user_id, days)
        expiry_date = premium_until.strftime("%d.%m.%Y %H:%M")
        
        await message.answer(
            text=(
                f"💎 Пользователю {target_user_id} выдана премиум подписка на {days} дней\n"
                f"Дата окончания: {expiry_date}"
            )
        )
        
        try:
            await bot.send_message(
                target_user_id,
                f"<b>💎 Вам выдана премиум подписка на {days} дней!</b>\n\n"
                f"<b>Дата окончания: {expiry_date}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю {target_user_id}: {str(e)}")
        
        await bot.send_message(
            config.bot_logs,
            f"Админ {user_id} выдал премиум подписку пользователю {target_user_id} на {days} дней\n"
            f"Дата окончания: {expiry_date}"
        )
        
    except ValueError:
        await message.answer("❌ Некорректное количество дней!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выдаче премиум подписки: {str(e)}")
    finally:
        states.waiting_for_premium_days.pop(user_id, None)

@dp.callback_query(F.data == 'create_promo')
async def create_promo_handler(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    states.waiting_for_promo_create[callback.from_user.id] = {
        'message_id': callback.message.message_id,
        'chat_id': callback.message.chat.id,
        'step': 'code'
    }
    
    await callback.message.edit_text(
        text="📝 Введите код промокода:"
    )

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_promo_create))
async def process_promo_create(message: Message):
    user_id = message.from_user.id
    promo_data = states.waiting_for_promo_create.get(user_id)
    
    if not promo_data:
        return
    
    if promo_data['step'] == 'code':
        promo_data['code'] = message.text.strip().upper()
        promo_data['step'] = 'days'
        
        await message.answer(
            text="📅 Введите количество дней подписки:"
        )
        
    elif promo_data['step'] == 'days':
        try:
            days = int(message.text.strip())
            if days <= 0:
                await message.answer("❌ Количество дней должно быть положительным!")
                return
            
            promo_data['days'] = days
            promo_data['step'] = 'max_uses'
            
            await message.answer(
                text="🔢 Введите максимальное количество использований:"
            )
            
        except ValueError:
            await message.answer("❌ Некорректное количество дней!")
            return
        
    elif promo_data['step'] == 'max_uses':
        try:
            max_uses = int(message.text.strip())
            if max_uses <= 0:
                await message.answer("❌ Количество использований должно быть положительным!")
                return
            
            success = db.create_promocode(
                code=promo_data['code'],
                days=promo_data['days'],
                max_uses=max_uses
            )
            
            if success:
                await message.answer(
                    text=(
                        f"🎁 <b>Промокод создан!</b>\n\n"
                        f"<b>• Код:</b> <code>{promo_data['code']}</code>\n"
                        f"<b>• Дней:</b> {promo_data['days']}\n"
                        f"<b>• Макс. использований:</b> {max_uses}"
                    ),
                    parse_mode="HTML"
                )
                
                await bot.send_message(
                    config.bot_logs,
                    f"🎁 Админ {user_id} создал промокод:\n"
                    f"Код: {promo_data['code']}\n"
                    f"Дней: {promo_data['days']}\n"
                    f"Макс. использований: {max_uses}"
                )
            else:
                await message.answer(
                    text="❌ Промокод с таким кодом уже существует!"
                )
                
        except ValueError:
            await message.answer("❌ Некорректное количество использований!")
        finally:
            states.waiting_for_promo_create.pop(user_id, None)


@dp.callback_query(F.data == 'send_all')
async def send_all_start(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    await callback.message.edit_text(
        text="<b>Выберите тип рассылки:</b>",
        reply_markup=broadcast_type_menu(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith('broadcast_'))
async def process_broadcast_type(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    broadcast_type = callback.data.split('_')[1]
    
    if broadcast_type == 'text':
        states.waiting_for_broadcast_text[callback.from_user.id] = {
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id
        }
        await callback.message.edit_text(
            text="✉️ Введите текст для рассылки:",
            parse_mode="HTML"
        )
    elif broadcast_type == 'button':
        states.waiting_for_broadcast_button[callback.from_user.id] = {
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id
        }
        await callback.message.edit_text(
            text="✉️ Введите текст для рассылки с кнопкой подписки:",
            parse_mode="HTML"
        )

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_broadcast_text))
async def process_broadcast_text(message: Message):
    user_id = message.from_user.id
    text = message.text
    broadcast_data = states.waiting_for_broadcast_text.get(user_id)
    
    if not broadcast_data:
        return
    
    await message.delete()
    
   
    states.broadcast_text = text
    states.broadcast_type = 'text'
    
    confirm_keyboard = InlineKeyboardBuilder()
    confirm_keyboard.row(InlineKeyboardButton(
        text="✅ Подтвердить рассылку",
        callback_data="confirm_broadcast"
    ))
    confirm_keyboard.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="cancel_broadcast"
    ))
    
    await bot.edit_message_text(
        chat_id=broadcast_data['chat_id'],
        message_id=broadcast_data['message_id'],
        text=f"📝 <b>Предпросмотр рассылки:</b>\n\n{text}\n\n✅ <b>Подтвердите отправку</b>",
        parse_mode="HTML",
        reply_markup=confirm_keyboard.as_markup()
    )

@dp.message(F.text & F.from_user.id.in_(states.waiting_for_broadcast_button))
async def process_broadcast_button(message: Message):
    user_id = message.from_user.id
    text = message.text
    broadcast_data = states.waiting_for_broadcast_button.get(user_id)
    
    if not broadcast_data:
        return
    
    await message.delete()
    
   
    states.broadcast_text = text
    states.broadcast_type = 'button'
    
    
    subscribe_keyboard = InlineKeyboardBuilder()
    subscribe_keyboard.row(InlineKeyboardButton(
        text="Канал",
        url=config.bot_channel_link  
    ))
    
    confirm_keyboard = InlineKeyboardBuilder()
    confirm_keyboard.row(InlineKeyboardButton(
        text="✅ Подтвердить рассылку",
        callback_data="confirm_broadcast"
    ))
    confirm_keyboard.row(InlineKeyboardButton(
        text="❌ Отменить",
        callback_data="cancel_broadcast"
    ))
    
    await bot.edit_message_text(
        chat_id=broadcast_data['chat_id'],
        message_id=broadcast_data['message_id'],
        text=f"📝 <b>Предпросмотр рассылки с кнопкой:</b>\n\n{text}\n\n✅ <b>Подтвердите отправку</b>",
        parse_mode="HTML",
        reply_markup=confirm_keyboard.as_markup()
    )

@dp.callback_query(F.data == 'confirm_broadcast')
async def confirm_broadcast(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not hasattr(states, 'broadcast_text') or states.broadcast_text is None:
        await callback.answer("❌ Текст рассылки не найден!", show_alert=True)
        return
    
    text = states.broadcast_text
    broadcast_type = getattr(states, 'broadcast_type', 'text')
    
    users = db.get_all_users()
    total_users = len(users)
    success = 0
    failed = 0
    blocked = 0
    
    await callback.message.edit_text(
        text=f"📤 Начата рассылка... 0% (0/{total_users})"
    )
    
    for i, user in enumerate(users, 1):
        try:
            if broadcast_type == 'button':
                
                subscribe_keyboard = InlineKeyboardBuilder()
                subscribe_keyboard.row(InlineKeyboardButton(
                    text="Канал",
                    url=config.bot_channel_link  
                ))
                
                await bot.send_message(
                    user,
                    text=text,
                    reply_markup=subscribe_keyboard.as_markup(),
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    user,
                    text=text,
                    parse_mode="HTML"
                )
            success += 1
        except TelegramForbiddenError:
            blocked += 1
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка при отправке пользователю {user}: {str(e)}")
        
        
        if i % 10 == 0 or i == total_users:
            progress = int((i / total_users) * 100)
            try:
                await callback.message.edit_text(
                    text=(
                        f"📤 Рассылка... {progress}% ({i}/{total_users})\n"
                        f"✅ Успешно: {success} | 🚫 Блокировки: {blocked} | ❌ Ошибок: {failed}"
                    )
                )
            except Exception as e:
                logging.error(f"Ошибка при обновлении прогресса: {str(e)}")
        
        await asyncio.sleep(0.1)
    
    result_text = (
        f"✅ Рассылка завершена!\n\n"
        f"• Всего получателей: {total_users}\n"
        f"• Успешно доставлено: {success}\n"
        f"• Заблокировали бота: {blocked}\n"
        f"• Ошибок отправки: {failed}"
    )
    
    await callback.message.edit_text(
        text=result_text
    )
    
    
    states.waiting_for_broadcast_text.pop(user_id, None)
    states.waiting_for_broadcast_button.pop(user_id, None)
    states.broadcast_text = None
    states.broadcast_type = None

@dp.callback_query(F.data.startswith("auth_get_"))
async def start_listening_session(call: CallbackQuery):
    if call.from_user.id not in config.ADMINS: return
    
    session_name = call.data.replace("auth_get_", "")
    await call.answer(f"Подключаюсь к {session_name}...")
    
   
    asyncio.create_task(rep_msg.listen_for_auth_code(session_name, bot, call.from_user.id))


@dp.callback_query(F.data.startswith('history_page_'))
@dp.callback_query(F.data == 'report_history')
async def show_report_history(callback: CallbackQuery):
    
    page = 1
    if callback.data.startswith('history_page_'):
        page = int(callback.data.split('_')[-1])

    per_page = 5
    reports, total_count = db.get_reports_paginated(callback.from_user.id, page, per_page)
    
    if not reports and page == 1:
        callback.message.edit_text(
            text=f"<b>{banner}📜 Ваша история пуста</b>",
            reply_markup=back_button(),
            parse_mode="HTML"
        )
        return

    total_pages = (total_count + per_page - 1) // per_page
    
    text = f"<b>{banner}📜 История ваших репортов (стр. {page}/{total_pages}):</b>\n\n"
    
    for link, reason, method, date in reports:
      
        display_link = (link[:100] + '...') if len(link) > 100 else link
        text += (
            f"<blockquote>"
            f"<b>• Дата: {date}</b>\n"
            f"<b>• Ссылка: {display_link}</b>\n"
            f"<b>• Причина: {reason}</b>\n"
            f"<b>• Метод: {method}</b>\n"
            f"</blockquote>\n"
        )

    await callback.message.edit_text(
        text, 
        reply_markup=history_keyboard(page, total_pages),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            show_above_text=True,
            prefer_large_media=True
        ),
        disable_web_page_preview=True
    )

@dp.callback_query(F.data == 'cancel_broadcast')
async def cancel_broadcast(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    states.waiting_for_broadcast_text.pop(user_id, None)
    states.waiting_for_broadcast_button.pop(user_id, None)
    states.broadcast_text = None
    states.broadcast_type = None
    
    await callback.message.edit_text(
        text="❌ Рассылка отменена"
    )

@dp.callback_query(F.data == "admin_auth_list")
async def show_auth_sessions(call: CallbackQuery):
    if call.from_user.id not in config.ADMINS: 
        return
    
    from report_service.session_manager import list_sessions
    
    sessions = list_sessions()
    
    if not sessions:
        await call.message.edit_text(
            "📱 <b>Нет доступных сессий</b>\n\nДобавьте сессию через кнопку ниже:",
            reply_markup=get_auth_sessions_kb(),
            parse_mode="HTML"
        )
        return
    
    await call.message.edit_text(
        "📱 <b>Список доступных сессий:</b>\n\n<i>Нажмите на сессию для просмотра информации</i>",
        reply_markup=get_auth_sessions_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("auth_info_"))
async def show_session_info(call: CallbackQuery):
    if call.from_user.id not in config.ADMINS: 
        return
    
    session_name = call.data.replace("auth_info_", "")
    
    await call.message.edit_text(
        f"🔄 <b>Получаем информацию о сессии {session_name}...</b>",
        parse_mode="HTML"
    )
    
    try:
        from report_service.session_manager import get_client
        
        client = await get_client(session_name)
        
        try:
            me = await client.get_me()
            
          
            phone = me.phone if me.phone else 'Не указан'
            info_text = (
                f"<b>📱 Информация о сессии:</b>\n\n"
                f"<b>• Имя сессии:</b> <code>{session_name}</code>\n"
                f"<b>• Телефон:</b> <code>{phone}</code>\n"
                f"<b>• ID:</b> <code>{me.id}</code>\n"
                f"<b>• Username:</b> @{me.username or 'нет'}\n"
                f"<b>• Имя:</b> {me.first_name or ''} {me.last_name or ''}\n"
                f"<b>• Премиум:</b> {'✅ Да' if me.premium else '❌ Нет'}"
            )
            
        except Exception as e:
            info_text = f"<b>❌ Не удалось получить информацию:</b>\n{str(e)}"
        finally:
            await client.disconnect()
        
    except Exception as e:
        info_text = f"<b>❌ Ошибка подключения:</b>\n{str(e)}"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔑 Войти в аккаунт", 
        callback_data=f"auth_get_{session_name}"
    ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Назад к списку", 
        callback_data='admin_auth_list'
    ))
    
    await call.message.edit_text(
        info_text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "auth_refresh_phones")
async def refresh_session_phones(call: CallbackQuery):
    if call.from_user.id not in config.ADMINS:
        return
    
    await call.message.edit_text(
        "🔄 <b>Обновляем информацию о сессиях...</b>",
        parse_mode="HTML"
    )
    
   
    await show_auth_sessions(call)


class SessionStates(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_2fa = State()


@dp.callback_query(F.data == 'admin_add_session')
async def admin_add_session_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        return await callback.answer("У вас нет прав доступа!", show_alert=True)
    
    await state.set_state(SessionStates.waiting_phone)
    await callback.message.edit_text(
        text="📱 <b>Введите номер телефона</b>\n\n<i>Пример: +79123456789</i>",
        parse_mode="HTML"
    )


@dp.message(SessionStates.waiting_phone)
async def process_session_phone(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        return
    
    phone = message.text.strip()
    await message.delete()
    
    await state.update_data(phone=phone)
    await state.set_state(SessionStates.waiting_code)
    
    await message.answer(
        text=f"🔄 <b>Отправляю код на {phone}...</b>",
        parse_mode="HTML"
    )
    
    result = await session_manager.send_code(
        phone, 
        config.API_ID, 
        config.API_HASH
    )
        
    if result.get('flood_wait'):
        wait_time = result['flood_wait']
        minutes = wait_time // 60
        seconds = wait_time % 60
        
        await state.clear()
        await message.answer(
            text=f"⏳ <b>Требуется подождать {minutes} мин {seconds} сек</b>",
            parse_mode="HTML"
        )
        
    elif result['success']:
        await message.answer(
            text="✅ <b>Код отправлен!</b>\n\n📱 Введите код из Telegram:",
            parse_mode="HTML"
        )
    else:
        await state.clear()
        await message.answer(
            text=f"❌ <b>Ошибка:</b>\n{result['error']}",
            parse_mode="HTML"
        )


@dp.message(SessionStates.waiting_code)
async def process_session_code(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        return
    
    code = message.text.strip()
    await message.delete()
    
    data = await state.get_data()
    phone = data.get('phone')
    
    result = await session_manager.verify_code(phone, code)
    
    if result['success']:
        await state.clear()
        await message.answer(
            text="✅ <b>Сессия успешно создана!</b>",
            parse_mode="HTML"
        )
        await bot.send_message(config.bot_logs, f"📱 Админ создал сессию для {phone}")
        
    elif result.get('need_password'):
        await state.set_state(SessionStates.waiting_2fa)
        await message.answer(
            text="🔐 <b>Требуется двухфакторная аутентификация</b>\n\nВведите пароль:",
            parse_mode="HTML"
        )
    elif result.get('flood_wait'):
        wait_time = result['flood_wait']
        minutes = wait_time // 60
        seconds = wait_time % 60
        await state.clear()
        await message.answer(
            text=f"⏳ <b>Требуется подождать {minutes} мин {seconds} сек</b>",
            parse_mode="HTML"
        )
    else:
        await state.clear()
        await message.answer(
            text=f"❌ <b>Ошибка:</b>\n{result['error']}",
            parse_mode="HTML"
        )


@dp.message(SessionStates.waiting_2fa)
async def process_session_2fa(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        return
    
    password = message.text.strip()
    await message.delete()
    
    data = await state.get_data()
    phone = data.get('phone')
    
    result = await session_manager.verify_2fa(phone, password)
    
    if result['success']:
        await message.answer(
            text="✅ <b>Сессия успешно создана!</b>",
            parse_mode="HTML"
        )
        await bot.send_message(config.bot_logs, f"📱 Админ создал сессию для {phone}")
    elif result.get('flood_wait'):
        wait_time = result['flood_wait']
        minutes = wait_time // 60
        seconds = wait_time % 60
        await message.answer(
            text=f"⏳ <b>Требуется подождать {minutes} мин {seconds} сек</b>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text=f"❌ <b>Ошибка:</b>\n{result['error']}",
            parse_mode="HTML"
        )
    
    await state.clear()

mirror_manager.set_original_dp(dp)

async def on_startup():
    logging.info("Загружаю зеркала из базы данных...")
    await mirror_manager.load_mirrors_from_db()

async def main():
    try:
        logging.info("Запуск бота...")
        
        main_bot_info = await bot.get_me()
        mirror_manager.set_main_bot_username(main_bot_info.username)
        
        await on_startup()
        db.cleanup_old_payments(hours=2)
        await dp.start_polling(bot)
        
    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        await asyncio.sleep(10)

async def restart_scheduler():
    while True:
        await asyncio.sleep(3600) 
        logging.info("⏰ Плановый перезапуск бота...")
        os.execv(sys.executable, ['python'] + sys.argv)

AUTO_RESTART = True

async def main_with_restart():
    global AUTO_RESTART
    if AUTO_RESTART:
        asyncio.create_task(restart_scheduler())
    await main()

# Обработчики сигналов
def signal_handler():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mirror_manager.save_mirrors_state())
    loop.run_until_complete(mirror_manager.shutdown_all_mirrors())
    print("✅ Зеркала сохранены при выходе")
    sys.exit(0)

import signal
signal.signal(signal.SIGINT, lambda s, f: signal_handler())
signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

if __name__ == "__main__":
    try:
        asyncio.run(main_with_restart())
    except KeyboardInterrupt:
        print("Бот остановлен")      
