import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from mirror_database import mirror_db

from keyboards import (
    main_menu, back_button, channel_subscribe, mirror_menu, shop_menu, 
    shop_usd_menu, shop_stars_menu, payment_menu, report_library_menu, 
    email_target_menu, email_attachment_menu, email_confirm_keyboard, 
    info_menu, admin_menu, broadcast_type_menu, get_auth_sessions_kb, 
    history_keyboard, telegraph_reason_menu, library_info_menu,
    promo_check_prof, miniapp_kb, report_method_menu
)

async def track_mirror_user(mirror_id: str, user_id: int, username: str = None):
    try:
        with sqlite3.connect("mirror.db") as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mirror_users (mirror_id, user_id, username, last_visit)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(mirror_id, user_id) 
                DO UPDATE SET 
                    last_visit = CURRENT_TIMESTAMP,
                    visits_count = visits_count + 1,
                    username = COALESCE(?, username)
            ''', (mirror_id, user_id, username, username))
            conn.commit()
    except Exception as e:
        logging.error(f"Error tracking mirror user: {e}")

class MirrorManager:
    def __init__(self):
        self.active_mirrors = {} 
        self.mirror_tasks = {}     
        self.original_dp = None
        self.main_bot_token = None
        self.main_bot_username = None
        self.main_bot_instance = None
        self._shutdown_flag = False
        
    def set_original_dp(self, dp):
        self.original_dp = dp
        
    def set_main_bot_token(self, token):
        self.main_bot_token = token
        
    def set_main_bot_username(self, username):
        self.main_bot_username = username
        
    def set_main_bot_instance(self, bot):
        self.main_bot_instance = bot
    
    async def save_mirrors_state(self):
        """Сохраняет состояние зеркал перед выходом"""
        for mirror_id in self.active_mirrors:
            mirror_db.update_mirror(mirror_id, is_active=1, last_active=datetime.now())
        logging.info(f"Saved {len(self.active_mirrors)} mirrors state")
        
    async def shutdown_all_mirrors(self):
        self._shutdown_flag = True
        logging.info("Shutting down all mirrors...")
        
        mirror_ids = list(self.active_mirrors.keys())
        for mirror_id in mirror_ids:
            await self.stop_mirror(mirror_id, permanent=False)
        
        for task in self.mirror_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logging.error(f"Error cancelling task: {e}")
        
        self.mirror_tasks.clear()
        logging.info(f"All mirrors stopped. Total: {len(mirror_ids)}")
        
    async def run_mirror_bot(self, mirror_id: str, token: str):
        try:
            if not self.original_dp:
                logging.error("Original dispatcher not set")
                return
                
            if self._shutdown_flag:
                logging.info(f"Mirror {mirror_id} not started due to shutdown flag")
                return
                
            mirror_bot = Bot(token=token)
            mirror_dp = Dispatcher(storage=MemoryStorage())
            
            @mirror_dp.message.outer_middleware()
            async def track_user_middleware(handler, event, data):
                if isinstance(event, Message):
                    user_id = event.from_user.id
                    username = event.from_user.username
                    asyncio.create_task(track_mirror_user(mirror_id, user_id, username))
                return await handler(event, data)

            @mirror_dp.callback_query.outer_middleware()
            async def track_callback_middleware(handler, event, data):
                if isinstance(event, CallbackQuery):
                    user_id = event.from_user.id
                    username = event.from_user.username
                    asyncio.create_task(track_mirror_user(mirror_id, user_id, username))
                return await handler(event, data)
            
            from start import (
    cmd_start, process_captcha_answer, check_subscription, profile,
    info_handler, mirror_create_start, process_mirror_token,
    shop, shop_usd, promo_handler, process_promo_code, 
    check_promo_bio_handler, shop_premium_direct,
    referral_refresh_handler, referral_menu_handler,
    process_subscription, delete_invoice_after_delay, check_payment_status,
    clean_paid_invoice_after_delay, cancel_payment, report_start,
    premium_only_handler, report_link_start, report_link_telethon_start,
    report_link_pyrogram_start, process_report_link_simple,
    library_info_handler, report_email_start, email_all_targets_handler,
    email_abuse_handler, email_support_handler, email_dmca_handler,
    email_sms_handler, handle_email_report_steps,
    email_with_attachment_handler, email_without_attachment_handler,
    process_email_attachment, confirm_email_send, edit_email_text,
    cancel_email_send, back_to_menu, reganah_cmd, process_reganah,
    admin_cmd, add_subscribe_handler, clear_subscribe_handler,
    process_user_id_for_subscription, process_days_for_subscription,
    improve_email_text, report_telegraph_start, process_telegraph_reason,
    process_telegraph_report, check_sessions_handler, check_emails_handler,
    add_premium_handler, remove_premium_handler, process_premium_user_id,
    process_premium_days, create_promo_handler, process_promo_create,
    send_all_start, process_broadcast_type, process_broadcast_text,
    process_broadcast_button, confirm_broadcast, cancel_broadcast,
    show_auth_sessions, show_session_info, refresh_session_phones,
    admin_add_session_start, process_session_phone, process_session_code,
    process_session_2fa, show_report_history, start_listening_session,
    CaptchaStates, MirrorStates, ReganaStates,
    SessionStates, states, shop_stars, pre_checkout_handler, 
    success_payment_handler
)
            
            @mirror_dp.callback_query(F.data.startswith('buy_sub_XTR_'))
            async def process_stars_payment_mirror(callback: CallbackQuery):
                parts = callback.data.split('_')
                sub_type = parts[3]
                
                prices_map = {'100': 1, '2': 300, '4': 600, '6': 1000, '8': 1550}
                days_map = {'1': 1, '2': 7, '4': 30, '6': 9999, '8': 9999}
                
                days = days_map.get(sub_type, 1)
                amount = prices_map.get(sub_type, 100)
                
                payload = f"pay_{sub_type}_{callback.from_user.id}"
                deep_link = f"https://t.me/{self.main_bot_username}?start={payload}"
                
                kb = InlineKeyboardBuilder()
                kb.row(InlineKeyboardButton(text="💎 Оплатить звёздами", url=deep_link))
                kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
                
                await callback.message.edit_text(
                    f"<b>⭐ Оплата звёздами</b>\n\n"
                    f"Для оплаты подписки на {days} дней ({amount} ⭐) перейдите в основного бота по кнопке ниже.\n\n"
                    f"После оплаты подписка активируется автоматически.",
                    reply_markup=kb.as_markup(),
                    parse_mode="HTML"
                )
                await callback.answer()
            
            mirror_dp.message.register(cmd_start, Command("start"))
            mirror_dp.message.register(process_captcha_answer, CaptchaStates.waiting_for_captcha)
            mirror_dp.message.register(process_mirror_token, MirrorStates.waiting_for_token)
            mirror_dp.message.register(process_report_link_simple, F.text.startswith(('https://t.me/', 'http://t.me/')))
            mirror_dp.message.register(process_telegraph_report, F.text.startswith(('https://telegra.ph/', 'http://telegra.ph/')))
            mirror_dp.message.register(process_reganah, ReganaStates.waiting_for_id)
            mirror_dp.message.register(admin_cmd, Command("admin"))          
            mirror_dp.message.register(process_promo_code, F.text & F.from_user.id.in_(states.waiting_for_promo_code))
            mirror_dp.message.register(handle_email_report_steps, F.text & (F.from_user.id.in_(states.email_data)))
            mirror_dp.message.register(process_email_attachment, F.photo & F.from_user.id.in_(states.email_data))
            mirror_dp.message.register(process_user_id_for_subscription, F.text & F.from_user.id.in_(states.waiting_for_user_id))
            mirror_dp.message.register(process_days_for_subscription, F.text & F.from_user.id.in_(states.waiting_for_days))
            mirror_dp.message.register(process_premium_user_id, F.text & F.from_user.id.in_(states.waiting_for_premium_user_id))
            mirror_dp.message.register(process_premium_days, F.text & F.from_user.id.in_(states.waiting_for_premium_days))
            mirror_dp.message.register(process_promo_create, F.text & F.from_user.id.in_(states.waiting_for_promo_create))
            mirror_dp.message.register(process_broadcast_text, F.text & F.from_user.id.in_(states.waiting_for_broadcast_text))
            mirror_dp.message.register(process_broadcast_button, F.text & F.from_user.id.in_(states.waiting_for_broadcast_button))
            mirror_dp.message.register(process_session_phone, SessionStates.waiting_phone)
            mirror_dp.message.register(process_session_code, SessionStates.waiting_code)
            mirror_dp.message.register(process_session_2fa, SessionStates.waiting_2fa)
            mirror_dp.message.register(success_payment_handler, F.successful_payment)
            
            mirror_dp.callback_query.register(check_subscription, F.data == 'check_subscription')
            mirror_dp.callback_query.register(profile, F.data == 'profile')
            mirror_dp.callback_query.register(info_handler, F.data == 'info')
            mirror_dp.callback_query.register(mirror_create_start, F.data == 'mirror_create')
            mirror_dp.callback_query.register(shop, F.data == 'shop')
            mirror_dp.callback_query.register(shop_usd, F.data == 'shop_usd')
            mirror_dp.callback_query.register(promo_handler, F.data == 'promo')
            mirror_dp.callback_query.register(check_promo_bio_handler, F.data == 'check_promo_bio')
            mirror_dp.callback_query.register(shop_premium_direct, F.data == 'shop_usd_8')
            mirror_dp.callback_query.register(referral_refresh_handler, F.data == 'referral_refresh')
            mirror_dp.callback_query.register(referral_menu_handler, F.data == 'referral')
            mirror_dp.callback_query.register(shop_stars, F.data == 'shop_stars')
            mirror_dp.callback_query.register(process_subscription, F.data.startswith('buy_sub_'))
            mirror_dp.callback_query.register(check_payment_status, F.data.startswith('check_payment_'))
            mirror_dp.callback_query.register(cancel_payment, F.data == 'cancel_payment')
            mirror_dp.callback_query.register(report_start, F.data == 'report')
            mirror_dp.callback_query.register(premium_only_handler, F.data == 'premium_only')
            mirror_dp.callback_query.register(report_link_start, F.data == 'report_link')
            mirror_dp.callback_query.register(report_link_telethon_start, F.data == 'report_link_telethon')
            mirror_dp.callback_query.register(report_link_pyrogram_start, F.data == 'report_link_pyrogram')
            mirror_dp.callback_query.register(library_info_handler, F.data == 'library_info')
            mirror_dp.callback_query.register(report_email_start, F.data == 'report_email')
            mirror_dp.callback_query.register(email_all_targets_handler, F.data == 'all_mail')
            mirror_dp.callback_query.register(email_abuse_handler, F.data == 'email_abuse')
            mirror_dp.callback_query.register(email_support_handler, F.data == 'email_support')
            mirror_dp.callback_query.register(email_dmca_handler, F.data == 'email_dmca')
            mirror_dp.callback_query.register(email_sms_handler, F.data == 'email_recovery')
            mirror_dp.callback_query.register(email_sms_handler, F.data == 'email_stopca')
            mirror_dp.callback_query.register(email_with_attachment_handler, F.data == 'email_with_attachment')
            mirror_dp.callback_query.register(email_without_attachment_handler, F.data == 'email_without_attachment')
            mirror_dp.callback_query.register(confirm_email_send, F.data == 'confirm_email_send')
            mirror_dp.callback_query.register(edit_email_text, F.data == 'edit_email_text')
            mirror_dp.callback_query.register(cancel_email_send, F.data == 'cancel_email_send')
            mirror_dp.callback_query.register(back_to_menu, F.data == 'back')
            mirror_dp.callback_query.register(reganah_cmd, F.data == 'reganah')
            mirror_dp.callback_query.register(add_subscribe_handler, F.data == 'add_subscribe')
            mirror_dp.callback_query.register(clear_subscribe_handler, F.data == 'clear_subscribe')
            mirror_dp.callback_query.register(improve_email_text, F.data == 'improve_text_groq')
            mirror_dp.callback_query.register(report_telegraph_start, F.data == 'report_telegraph')
            mirror_dp.callback_query.register(process_telegraph_reason, F.data.startswith('telegraph_reason_'))
            mirror_dp.callback_query.register(check_sessions_handler, F.data == 'check_sessions')
            mirror_dp.callback_query.register(check_emails_handler, F.data == 'check_emails')
            mirror_dp.callback_query.register(add_premium_handler, F.data == 'add_premium')
            mirror_dp.callback_query.register(remove_premium_handler, F.data == 'remove_premium')
            mirror_dp.callback_query.register(create_promo_handler, F.data == 'create_promo')
            mirror_dp.callback_query.register(send_all_start, F.data == 'send_all')
            mirror_dp.callback_query.register(process_broadcast_type, F.data.startswith('broadcast_'))
            mirror_dp.callback_query.register(confirm_broadcast, F.data == 'confirm_broadcast')
            mirror_dp.callback_query.register(cancel_broadcast, F.data == 'cancel_broadcast')
            mirror_dp.callback_query.register(start_listening_session, F.data.startswith("auth_get_"))
            mirror_dp.callback_query.register(show_report_history, F.data == 'report_history')
            mirror_dp.callback_query.register(show_report_history, F.data.startswith('history_page_'))
            mirror_dp.callback_query.register(show_auth_sessions, F.data == "admin_auth_list")
            mirror_dp.callback_query.register(show_session_info, F.data.startswith("auth_info_"))
            mirror_dp.callback_query.register(refresh_session_phones, F.data == "auth_refresh_phones")
            mirror_dp.callback_query.register(admin_add_session_start, F.data == 'admin_add_session')
            
            mirror_dp.pre_checkout_query.register(pre_checkout_handler)
            
            mirror_db.update_mirror(mirror_id, last_active=datetime.now(), is_active=1)
            
            self.active_mirrors[mirror_id] = mirror_bot
            logging.info(f"Mirror {mirror_id} started successfully")
                       
            await mirror_dp.start_polling(mirror_bot)
            
        except asyncio.CancelledError:
            logging.info(f"Mirror {mirror_id} polling cancelled")
            raise
        except Exception as e:
            logging.error(f"Mirror {mirror_id} error: {e}")
            mirror_db.add_log(mirror_id, "mirror_error", {"error": str(e)})
        finally:
            if mirror_id in self.active_mirrors:
                await self.stop_mirror(mirror_id, permanent=False)
    
    async def stop_mirror(self, mirror_id: str, permanent: bool = False):
        if mirror_id in self.active_mirrors:
            try:
                bot = self.active_mirrors[mirror_id]                           
                await bot.session.close()
                logging.info(f"Mirror {mirror_id} session closed")
                
            except Exception as e:
                logging.error(f"Error closing mirror {mirror_id} session: {e}")
            finally:
                del self.active_mirrors[mirror_id]
                
                if permanent:
                    mirror_db.update_mirror(mirror_id, is_active=0)
                    mirror_db.add_log(mirror_id, "mirror_stopped_permanent", {})
                else:
                    mirror_db.update_mirror(mirror_id, is_active=0)
                    mirror_db.add_log(mirror_id, "mirror_stopped", {})
                
                logging.info(f"Mirror {mirror_id} stopped. Permanent: {permanent}")
    
    async def delete_mirror_completely(self, mirror_id: str) -> bool:
        logging.info(f"Starting complete deletion of mirror {mirror_id}")
        
        try:
            if mirror_id in self.active_mirrors:
                await self.stop_mirror(mirror_id, permanent=True)
                await asyncio.sleep(1)
            
            if mirror_id in self.mirror_tasks:
                task = self.mirror_tasks[mirror_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logging.error(f"Error cancelling task for mirror {mirror_id}: {e}")
                del self.mirror_tasks[mirror_id]
            
            result = mirror_db.delete_mirror(mirror_id, hard_delete=True)
            
            if result:
                logging.info(f"Mirror {mirror_id} completely deleted from database")
            else:
                logging.warning(f"Mirror {mirror_id} not found in database")
            
            return result
            
        except Exception as e:
            logging.error(f"Error deleting mirror {mirror_id} completely: {e}")
            return False
    
    def is_mirror_running(self, mirror_id: str) -> bool:
        return mirror_id in self.active_mirrors
    
    async def load_mirrors_from_db(self):
        mirrors = mirror_db.get_all_active_mirrors()
        logging.info(f"Loading {len(mirrors)} mirrors from database")
        
        for mirror in mirrors:
            if mirror['is_active'] and not self._shutdown_flag:
                if mirror['mirror_id'] not in self.active_mirrors:
                    task = asyncio.create_task(
                        self.run_mirror_bot(mirror['mirror_id'], mirror['bot_token'])
                    )
                    self.mirror_tasks[mirror['mirror_id']] = task
                    await asyncio.sleep(0.5)
                else:
                    logging.info(f"Mirror {mirror['mirror_id']} already running")
            else:
                if mirror['is_active']:
                    mirror_db.update_mirror(mirror['mirror_id'], is_active=0)
                    logging.info(f"Mirror {mirror['mirror_id']} deactivated in database")

mirror_manager = MirrorManager()