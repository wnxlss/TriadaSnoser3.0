import os
import random
import asyncio
import logging
import shutil
import re
from datetime import datetime, timedelta
from pyrogram import Client
from pyrogram.errors import (
    FloodWait, 
    AuthKeyUnregistered,
    Unauthorized
)
from pyrogram.raw.functions.messages import Report
from pyrogram.raw.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonIllegalDrugs,
    InputReportReasonPersonalDetails,
    InputReportReasonOther
)

from report_service.link_parser import LinkParser
from report_service.promt_service import reason_prompts
from report_service.msg import reason_messages
from report_service.report_logger import ReportLogger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PyrogramReporter')

max_concurrent_reports = 1
min_delay = 2
max_delay = 8
report_cooldown_minutes = 5

class PyrogramReporter:
    def __init__(self, api_list=None, session_folder='pyro_sessions', groq_api_key=None):
        self.api_list = api_list or []
        self.last_used = {}
        self.api_usage = {}
        self.groq_api_key = groq_api_key or "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"
        self.session_folder = os.path.abspath(session_folder)
        self.no_work_folder = os.path.abspath(os.path.join(session_folder, 'no_work'))
        self.logger = ReportLogger()
        
        self.reason_keys = ['spam', 'violence', 'pornography', 'child_abuse', 'drugs', 'personal', 'other']
        
        os.makedirs(self.no_work_folder, exist_ok=True)
        os.makedirs(self.session_folder, exist_ok=True)
        
        logger.info(f"PyrogramReporter инициализирован")

    def get_sessions_count(self):
        try:
            if not os.path.exists(self.session_folder):
                return 0
            
            sessions = [f for f in os.listdir(self.session_folder) if f.endswith('.session')]
            return len(sessions)
        except Exception as e:
            logger.error(f"Ошибка при подсчете сессий: {e}")
            return 0

    def _get_random_reason_key(self):
        return random.choice(self.reason_keys)

    def _get_report_reason(self, reason_key):
        reason_map = {
            'spam': InputReportReasonSpam(),
            'violence': InputReportReasonViolence(),
            'pornography': InputReportReasonPornography(),
            'child_abuse': InputReportReasonChildAbuse(),
            'drugs': InputReportReasonIllegalDrugs(),
            'personal': InputReportReasonPersonalDetails(),
            'other': InputReportReasonOther()
        }
        return reason_map.get(reason_key, InputReportReasonSpam())

    async def generate_report_message(self, reason_key='spam', offender_info=None):
        try:
            if self.groq_api_key:
                import groq
                client = groq.Groq(api_key=self.groq_api_key)
                
                prompts = reason_prompts.get(reason_key, reason_prompts['spam'])
                prompt = random.choice(prompts)
                
                if offender_info and offender_info.get('username') != '@нет':
                    prompt += f" The offender's username is {offender_info['username']}."
                
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=random.randint(40, 80),
                    temperature=random.uniform(0.3, 0.7)
                )
                
                report_text = response.choices[0].message.content.strip()
               
                report_text = re.sub(r'^[0-9\*\-•]+\s*', '', report_text)
                report_text = report_text.replace('"', '').replace("'", "")
                
                if len(report_text) > 200:
                    report_text = report_text[:200]
                
                if '.' in report_text:
                    report_text = report_text.split('.')[0] + '.'
                elif len(report_text) > 0 and report_text[-1] not in '.!?':
                    report_text += '.'
                
                logger.info(f"Сгенерирован текст через ИИ для причины {reason_key}: {report_text[:50]}...")
                return report_text
                
        except Exception as e:
            logger.error(f"Ошибка генерации через ИИ: {e}")
        
        messages = reason_messages.get(reason_key, reason_messages['spam'])
        fallback_text = random.choice(messages)
        logger.info(f"Использован фолбек текст для причины {reason_key}: {fallback_text[:50]}...")
        return fallback_text

    def get_random_api(self):
        if not self.api_list:
            return None, None
        now = datetime.now()
        available_apis = [api for api in self.api_list 
                         if self.api_usage.get(api, datetime.min) < now - timedelta(hours=1)]
        if not available_apis:
            available_apis = self.api_list
        api = random.choice(available_apis)
        self.api_usage[api] = now
        try:
            api_id, api_hash = api.split(':', 1)
            return int(api_id.strip()), api_hash.strip()
        except ValueError:
            return None, None

    async def move_session_to_no_work(self, session_name):
        try:
            session_name = session_name.replace('.session', '')
            session_file = f"{session_name}.session"
            session_path = os.path.join(self.session_folder, session_file)
            destination_path = os.path.join(self.no_work_folder, session_file)
            
            if os.path.exists(session_path):
                logger.info(f"Перемещаем {session_name} в no_work")
                shutil.move(session_path, destination_path)
                logger.info(f"[!] {session_name} -> no_work")
                return True
        except Exception as e:
            logger.error(f"Ошибка при перемещении {session_name}: {e}")
        return False

    async def get_offender_info(self, client, chat_id, message_id):
        try:
            message = await client.get_messages(chat_id, message_ids=message_id)
            if not message:
                return None
            
            offender_info = {
                'id': 'N/A', 
                'username': '@нет', 
                'first_name': '',
                'last_name': '',
                'is_premium': False
            }
            
            if message and message.from_user:
                user = message.from_user
                offender_info['id'] = user.id
                offender_info['username'] = f"@{user.username}" if user.username else '@нет'
                
            return offender_info
        except Exception as e:
            logger.error(f"Ошибка получения информации об отправителе: {e}")
            return None

    async def _process_session(self, session_name, chat_identifier, message_id, forced_reason=None):
        valid = 0
        invalid = 0
        client = None
        offender_info = None
        report_text = None
        used_reason = None
        
        try:
            await asyncio.sleep(random.uniform(min_delay, max_delay))
            session_name = session_name.replace('.session', '')
            session_path = os.path.join(self.session_folder, session_name)
            session_file = f"{session_path}.session"
            
            if not os.path.exists(session_file):
                logger.warning(f"[-] {session_name}: Файл не найден")
                invalid += 1
                return {'valid': valid, 'invalid': invalid}
            
            api_id, api_hash = self.get_random_api()
            if not api_id or not api_hash:
                logger.warning(f"[-] {session_name}: Нет API")
                invalid += 1
                return {'valid': valid, 'invalid': invalid}
            
            client = Client(
                name=session_path,
                api_id=api_id,
                api_hash=api_hash,
                workdir=os.path.dirname(session_path)
            )
            
            await client.connect()
            
            try:
                me = await client.get_me()
                if not me:
                    raise Exception("Not authorized")
                logger.info(f"[{session_name}] Авторизован как {me.id}")
            except (Unauthorized, AuthKeyUnregistered) as e:
                logger.warning(f"[-] {session_name}: Не авторизован - {e}")
                invalid += 1
                await client.disconnect()
                await self.move_session_to_no_work(session_name)
                return {'valid': valid, 'invalid': invalid}
            
            try:
                chat = await client.get_chat(chat_identifier)
                logger.info(f"[{session_name}] Чат получен: {chat.id}")
            except Exception as e:
                logger.warning(f"[-] {session_name}: Чат не найден - {e}")
                invalid += 1
                await client.disconnect()
                return {'valid': valid, 'invalid': invalid}
            
            offender_info = await self.get_offender_info(client, chat.id, message_id)
            
            if forced_reason:
                used_reason = forced_reason
            else:
                used_reason = self._get_random_reason_key()
            
            report_text = await self.generate_report_message(used_reason, offender_info)
            
            reason = self._get_report_reason(used_reason)
            
            try:
                peer = await client.resolve_peer(chat.id)
                await client.invoke(
                    Report(
                        peer=peer,
                        id=[message_id],
                        reason=reason,
                        message=report_text
                    )
                )
                
                logger.info(f"[+] {session_name}: Успешно! Причина: {used_reason}")
                valid += 1
                
            except FloodWait as e:
                logger.warning(f"[-] {session_name}: Flood wait {e.value} сек")
                await asyncio.sleep(e.value)
                invalid += 1
            except Exception as e:
                logger.warning(f"[-] {session_name}: Ошибка репорта - {e}")
                invalid += 1
            
            await client.disconnect()
            
            result = {
                'valid': valid, 
                'invalid': invalid,
                'used_reason': used_reason
            }
            if offender_info:
                result['offender_info'] = offender_info
            if report_text:
                result['report_text'] = report_text
                
            return result
            
        except Exception as e:
            logger.error(f"[-] {session_name}: Критическая ошибка - {e}")
            invalid += 1
            
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            
            return {'valid': valid, 'invalid': invalid, 'used_reason': used_reason}

    async def report_message(self, chat_username, message_id, user_id, username=None, reason_key=None):
        try:
            can_report, wait_time = await self.can_report(user_id)
            if not can_report:
                return {'valid': 0, 'invalid': 0, 'error': f'Подождите {wait_time} сек'}
            
            if not os.path.exists(self.session_folder):
                return {'valid': 0, 'invalid': 0, 'error': 'Папка с Pyrogram сессиями не найдена'}
            
            sessions = [f.replace('.session', '') for f in os.listdir(self.session_folder) 
                       if f.endswith('.session')]
            
            if not sessions:
                return {'valid': 0, 'invalid': 0, 'error': 'Pyrogram сессии не найдены'}
            
            valid = 0
            invalid = 0
            offender_info = None
            generated_reports = []
            used_reasons = []
            reason_stats = {}
            
            semaphore = asyncio.Semaphore(max_concurrent_reports)
            
            async def limited_process(session):
                async with semaphore:
                    return await self._process_session(session, chat_username, message_id, reason_key)
            
            tasks = [limited_process(session) for session in sessions]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Ошибка в задаче: {result}")
                    invalid += 1
                elif isinstance(result, dict):
                    if 'error' in result:
                        return result
                    if result.get('offender_info') and not offender_info:
                        offender_info = result['offender_info']
                    if result.get('report_text'):
                        generated_reports.append(result['report_text'])
                    if result.get('used_reason'):
                        used_reasons.append(result['used_reason'])
                        reason_stats[result['used_reason']] = reason_stats.get(result['used_reason'], 0) + 1
                    valid += result.get('valid', 0)
                    invalid += result.get('invalid', 0)
            
            self.last_used[user_id] = datetime.now()
            
            result_stats = {
                'valid': valid,
                'invalid': invalid,
                'total': len(sessions),
                'offender_info': offender_info,
                'reason_stats': reason_stats,
                'total_reasons_used': len(set(used_reasons))
            }
            
            if generated_reports:
                result_stats['generated_reports'] = list(set(generated_reports))[:3]
            
            target_link = f"https://t.me/{chat_username}/{message_id}"
            log_file = self.logger.save_report(
                user_id=user_id,
                method="Pyrogram",
                stats=result_stats,
                target_link=target_link,
                username=username
            )
            result_stats['log_file'] = log_file
            
            return result_stats
            
        except Exception as e:
            logger.error(f"Ошибка в report_message: {e}")
            return {'valid': 0, 'invalid': 0, 'error': str(e)}

    async def can_report(self, user_id):
        if user_id in self.last_used:
            time_passed = datetime.now() - self.last_used[user_id]
            if time_passed < timedelta(minutes=report_cooldown_minutes):
                remaining = (timedelta(minutes=report_cooldown_minutes) - time_passed).seconds
                return False, remaining
        return True, 0