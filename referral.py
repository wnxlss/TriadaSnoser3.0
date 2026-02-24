from datetime import datetime
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, LinkPreviewOptions
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database
import config

from keyboards import *

referalka = '<a href=\"https://i.ibb.co/nqyQSFvk/IMG-1223.jpg\">&#8203</a>'

class Referrals:
    def __init__(self, db: Database):
        self.db = db
        self.cache = {}

    async def process_referral_start(self, message: Message, bot: Bot):
        user_id = message.from_user.id
        self.db.add_user(user_id)
        
        if len(message.text.split()) > 1:
            await self._handle_referral_link(message, bot)
        
        self._update_cache(user_id)

    async def _handle_referral_link(self, message: Message, bot: Bot):
        user_id = message.from_user.id
        referrer_id_str = message.text.split()[1]
        
        try:
            if referrer_id_str.startswith('ref_'):
                referrer_id = int(referrer_id_str[4:])
            else:
                referrer_id = int(referrer_id_str)
            
            if (referrer_id != user_id and 
                self.db.user_exists(referrer_id) and
                not self._is_already_referred(user_id)):
                
                if self.db.add_referral(referrer_id, user_id):
                    self._update_cache(referrer_id)
                    await self._check_referral_reward(referrer_id, bot)
                    await self._log_referral(user_id, referrer_id, bot)
                    
        except (ValueError, IndexError):
            pass

    def _is_already_referred(self, user_id: int) -> bool:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT 1 FROM referrals WHERE referred_id = ?", (user_id,))
        return cursor.fetchone() is not None

    def _update_cache(self, user_id: int):
        ref_count = self.db.get_referral_count(user_id)
        self.cache[user_id] = {
            'count': ref_count,
            'last_updated': datetime.now()
        }

    async def _check_referral_reward(self, referrer_id: int, bot: Bot):
        ref_count = self.db.get_referral_count(referrer_id)
        
        if ref_count >= config.referral_needed:
            reward_count = ref_count // config.referral_needed
            remaining_refs = ref_count % config.referral_needed
            total_days = reward_count * config.referral_reward_days
            
            self.db.update_subscription(referrer_id, total_days)
            self._reset_referral_count_with_remainder(referrer_id, remaining_refs)
            self._update_cache(referrer_id)
            
            try:
                await bot.send_message(
                    referrer_id,
                    f"<b>🎉 Поздравляем! Вы получили награду!</b>\n\n"
                    f"Вы успешно пригласили <b>{ref_count}</b> пользователей.\n"
                    f"Ваша подписка продлена на <b>{total_days}</b> дней.\n\n"
                    f"<i>Следующая награда через {config.referral_needed - remaining_refs} приглашений</i>",
                    parse_mode="HTML"
                )
            except:
                pass

    def _reset_referral_count_with_remainder(self, user_id: int, remainder: int):
        cursor = self.db.conn.cursor()
        if remainder > 0:
            cursor.execute("UPDATE referral_counts SET count = ? WHERE user_id = ?", 
                          (remainder, user_id))
            if cursor.rowcount == 0:
                cursor.execute("INSERT INTO referral_counts VALUES(?, ?)", (user_id, remainder))
        else:
            cursor.execute("DELETE FROM referral_counts WHERE user_id = ?", (user_id,))
        self.db.conn.commit()

    async def _log_referral(self, referred_id: int, referrer_id: int, bot: Bot):
        ref_count = self.db.get_referral_count(referrer_id)
        
        log_message = (
            f"<b>📋 Реферальная регистрация</b>\n"
            f"└ <b>ID приглашенного:</b> <code>{referred_id}</code>\n"
            f"└ <b>ID реферера:</b> <code>{referrer_id}</code>\n"
            f"└ <b>Прогресс приглашений:</b> {ref_count}/{config.referral_needed}\n"
            f"└ <b>Время регистрации:</b> {datetime.now().strftime('%H:%M %d.%m.%Y')}"
        )
        await bot.send_message(config.bot_logs, log_message, parse_mode="HTML")

    async def show_referral_stats(self, callback: CallbackQuery, force_update: bool = False):
        user_id = callback.from_user.id
        
        if force_update:
            ref_count = self.db.get_referral_count(user_id)
            self._update_cache(user_id)
        elif user_id in self.cache:
            cached_data = self.cache[user_id]
            if (datetime.now() - cached_data['last_updated']).seconds > 300:
                ref_count = self.db.get_referral_count(user_id)
                self._update_cache(user_id)
            else:
                ref_count = cached_data['count']
        else:
            ref_count = self.db.get_referral_count(user_id)
            self._update_cache(user_id)
        
        remaining = max(0, config.referral_needed - ref_count)
        referral_link = self.get_referral_link(user_id)
        
        text = (
            f"<blockquote><b>{referalka}⚡ Реферальная система</b></blockquote>\n\n"
            f"<b>💸 Приглашайте друзей и получайте бонусы</b>\n\n"
            f"<b>📊 Ваша статистика:</b>\n"
            f"<b>• Приглашено:</b> <code>{ref_count}</code>\n"
            f"<b>• Осталось:</b> <code>{remaining}</code>\n"
            f"<b>• Награда: +{config.referral_reward_days} дней подписки</b>\n\n"
            f"<b>🔗 Ваша ссылка:</b>\n"
            f"<code>{referral_link}</code>"
        )
        
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True,
                prefer_large_media=True
            ),
            reply_markup=back_button()
        )

    def get_referral_link(self, user_id: int) -> str:
        bot_username = "triada_snoserbot"  # или получите из config
        return f"https://t.me/{bot_username}?start=ref_{user_id}"