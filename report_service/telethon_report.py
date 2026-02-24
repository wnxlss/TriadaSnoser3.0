import os
import random
import asyncio
import logging
import shutil
import re
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    PeerUser,
    ReportResultChooseOption
)

from report_service.link_parser import LinkParser
from report_service.promt_service import reason_prompts
from report_service.msg import reason_messages
from report_service.report_logger import ReportLogger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Reporter')

max_concurrent_reports = 1
min_delay = 2
max_delay = 8
report_cooldown_minutes = 5

class Reporter:
    def __init__(self, api_list=None, session_folder='tele_sessions', groq_api_key=None):
        self.api_list = api_list or []
        self.session_folder = session_folder
        self.no_work_folder = os.path.join(session_folder, 'no_work')
        self.last_used = {}
        self.api_usage = {}
        self.active_clients = {}
        self.groq_api_key = "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"
        self.logger = ReportLogger()
        
        os.makedirs(self.no_work_folder, exist_ok=True)

    async def move_session_to_no_work(self, session_name):
        try:
            os.makedirs(self.no_work_folder, exist_ok=True)
            
            session_file = f"{session_name}.session"
            session_path = os.path.join(self.session_folder, session_file)
            destination_path = os.path.join(self.no_work_folder, session_file)
            
            if os.path.exists(session_path):
                if os.access(self.no_work_folder, os.W_OK):
                    shutil.move(session_path, destination_path)
                    print(f"[!] {session_name} -> no_work")
                return True
            return False
        except Exception as e:
            print(f"Ошибка при перемещении {session_name}: {e}")
            return False

    async def generate_report_message(self, reason_type, offender_info=None, reason_key='spam'):
        try:
            import groq
            client = groq.Groq(api_key=self.groq_api_key)
            prompts = reason_prompts.get(reason_key, reason_prompts['spam'])
            prompt = random.choice(prompts)
            temperature = random.uniform(0.3, 0.7)
            max_tokens = random.randint(40, 80)
            
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            report_text = response.choices[0].message.content.strip()
            report_text = report_text.replace('"', '').replace("'", "").strip()
            lines = report_text.split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                if re.match(r'^(\d+\.|\*\*|[-•])', line):
                    continue
                if line and not line.startswith('Here are') and not line.startswith('1.'):
                    clean_lines.append(line)
            
            if clean_lines:
                report_text = ' '.join(clean_lines)
            
            if len(report_text) > 200:
                report_text = report_text[:200]
            
            report_text = report_text.split('.')[0] + '.' if '.' in report_text else report_text
            return report_text
        except Exception:
            return await self._generate_fallback_message(reason_type, reason_key)

    async def _generate_fallback_message(self, reason_type, reason_key='spam'):
        messages = reason_messages.get(reason_key, reason_messages['spam'])
        return random.choice(messages)

    def extract_username_and_message_id(self, message_url):
        return LinkParser.extract_username_and_message_id(message_url)

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
            return api_id.strip(), api_hash.strip()
        except ValueError:
            return None, None

    async def _get_offender_info(self, client, chat, message_id):
        try:
            message = await client.get_messages(chat, ids=message_id)
            if not message:
                return None
            offender_info = {'id': 'N/A', 'username': '@нет'}
            
            if hasattr(message, 'sender') and message.sender:
                sender = message.sender
                offender_info['id'] = getattr(sender, 'id', 'N/A')
                if hasattr(sender, 'username') and sender.username:
                    offender_info['username'] = f"@{sender.username}"
                    
            elif hasattr(message, 'from_id'):
                from_id = message.from_id
                if from_id and isinstance(from_id, PeerUser):
                    try:
                        user = await client.get_entity(PeerUser(from_id.user_id))
                        offender_info['id'] = user.id
                        if hasattr(user, 'username') and user.username:
                            offender_info['username'] = f"@{user.username}"
                    except:
                        offender_info['id'] = from_id.user_id
            return offender_info
        except Exception as e:
            logger.error(f"Ошибка в _get_offender_info: {e}")
            return None

    async def _get_report_options(self, client, chat, message_id):
        try:
            logger.info(f"Получение опций жалобы для сообщения {message_id}")
            
            result = await client(ReportRequest(
                peer=chat,
                id=[message_id],
                option=b'',
                message=""
            ))
            
            if not isinstance(result, ReportResultChooseOption):
                raise Exception(f"Ожидался ReportResultChooseOption, получен {type(result)}")
            
            options = []
            for i, option in enumerate(result.options):
                options.append({
                    'index': i,
                    'text': option.text,
                    'option': option.option,
                })
                logger.info(f"Опция {i}: {option.text}")
            
            random.shuffle(options)
            
            return {
                'title': result.title,
                'options': options
            }
                
        except Exception as e:
            logger.error(f"Ошибка получения опций жалобы: {e}")
            raise

    async def _select_best_option(self, options, reason_key='spam'):
        if not options:
            return None
        
        if options:
            selected_option = random.choice(options)
            logger.info(f"[RANDOM] Выбрана рандомная опция {selected_option['index']}: {selected_option['text']}")
            return selected_option
        
        return options[0] if options else None

    async def _send_report_with_option(self, client, chat, message_id, option, report_text=""):
        try:
            logger.info(f"Отправка с опцией '{option['text']}'")
            
            result = await client(ReportRequest(
                peer=chat,
                id=[message_id],
                option=option['option'],
                message=report_text
            ))
            
            if isinstance(result, ReportResultChooseOption):
                logger.info("Получен дополнительный уровень опций")
                
                new_options = []
                for i, opt in enumerate(result.options):
                    new_options.append({
                        'index': i,
                        'text': opt.text,
                        'option': opt.option,
                    })
                    logger.info(f"Подопция {i}: {opt.text}")
                
                if new_options:
                    if random.random() < 0.7 and len(new_options) > 1:
                        sub_option = random.choice(new_options)
                        logger.info(f"[RANDOM] Выбрана рандомная подопция: {sub_option['text']}")
                    else:
                        sub_option = new_options[0]
                        logger.info(f"Выбрана первая подопция: {sub_option['text']}")
                    
                    return await self._send_report_with_option(client, chat, message_id, sub_option, report_text)
            
            logger.info(f"Жалоба успешно отправлена")
            return {'type': 'success', 'result': result}
            
        except Exception as e:
            logger.error(f"Ошибка отправки жалобы: {e}")
            raise

    async def _process_session(self, session, chat_username, message_id, reason_key='spam'):
        valid = 0
        invalid = 0
        client = None
        report_text = None
        selected_options = []
        
        try:
            delay = random.uniform(min_delay * 2, max_delay * 2)
            logger.info(f"[{session}] Ожидание {delay:.1f} сек перед началом...")
            await asyncio.sleep(delay)
            
            session_file = f"{session}.session"
            session_path = os.path.join(self.session_folder, session_file)
            
            if not os.path.exists(session_path):
                print(f"[-] {session}: Файл отсутствует")
                return {'valid': 0, 'invalid': 1}
            
            api_id, api_hash = self.get_random_api()
            if not api_id or not api_hash:
                print(f"[-] {session}: Нет API")
                return {'valid': 0, 'invalid': 1}
            
            client = TelegramClient(session_path, int(api_id), api_hash, connection_retries=3)
            await client.connect()
            
            if not await client.is_user_authorized():
                print(f"[-] {session}: Ошибка авторизации")
                await client.disconnect()
                if random.random() < 0.5:
                    await self.move_session_to_no_work(session)
                return {'valid': 0, 'invalid': 1}
            
            await client.start()
            await LinkParser.check_chat_type(client, chat_username)
            chat = await client.get_entity(chat_username)
            
            offender_info = await self._get_offender_info(client, chat, message_id)
            
            report_text = await self.generate_report_message(reason_key, offender_info, reason_key)
            
            print(f"[*] {session}: Получение опций жалобы...")
            options_data = await self._get_report_options(client, chat, message_id)
            
            selected_option = await self._select_best_option(options_data['options'], reason_key)
            selected_options.append(selected_option['text'])
            
            print(f"[*] {session}: Отправка жалобы с опцией: {selected_option['text']}")
            result = await self._send_report_with_option(client, chat, message_id, selected_option, report_text)
            
            if result['type'] == 'success':
                print(f"[+] {session}: Жалоба успешно отправлена! Путь: {' -> '.join(selected_options)}")
                valid += 1
            else:
                print(f"[-] {session}: Неожиданный результат")
                invalid += 1
            
            await client.disconnect()
            
            stats = {
                'valid': valid,
                'invalid': invalid,
                'offender_info': offender_info,
                'report_text': report_text,
                'selected_options': selected_options
            }
            
            return stats
            
        except Exception as e:
            error_msg = str(e)
            print(f"[-] {session}: Ошибка - {error_msg}")
            logger.error(f"Ошибка в сессии {session}: {error_msg}")
            
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            
            if random.random() < 0.3:
                await self.move_session_to_no_work(session)
            
            return {
                'valid': 0,
                'invalid': 1,
                'error': error_msg,
                'report_text': report_text
            }

    async def report_message(self, chat_username, message_id, user_id, username=None, reason_key='spam'):
        try:
            can_report, wait_time = await self.can_report(user_id)
            if not can_report:
                return {'valid': 0, 'invalid': 0, 'error': f'Пожалуйста, подождите {wait_time} секунд'}
            
            if not os.path.exists(self.session_folder):
                return {'valid': 0, 'invalid': 0, 'error': 'Папка с сессиями не найдена'}
            
            sessions = [f.replace('.session', '') for f in os.listdir(self.session_folder) 
                       if f.endswith('.session')]
            
            if not sessions:
                return {'valid': 0, 'invalid': 0, 'error': 'Сессии не найдены'}
            
            random.shuffle(sessions)
            
            valid = 0
            invalid = 0
            offender_info = None
            generated_reports = []
            errors = []
            all_selected_options = []
            
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
                    errors.append(str(result))
                elif result and isinstance(result, dict):
                    if result.get('offender_info'):
                        offender_info = result['offender_info']
                    if result.get('report_text'):
                        generated_reports.append(result['report_text'])
                    if result.get('error'):
                        errors.append(result['error'])
                    if result.get('selected_options'):
                        all_selected_options.extend(result['selected_options'])
                    
                    valid += result.get('valid', 0)
                    invalid += result.get('invalid', 0)
            
            self.last_used[user_id] = datetime.now()
            
            total_stats = {
                'valid': valid,
                'invalid': invalid,
                'total': len(sessions),
                'offender_info': offender_info
            }
            
            if generated_reports:
                total_stats['generated_reports'] = list(set(generated_reports))[:5]
            if errors:
                total_stats['errors'] = list(set(errors))[:3]
            if all_selected_options:
                unique_options = list(set(all_selected_options))
                total_stats['used_options'] = unique_options
            
            target_link = f"https://t.me/{chat_username}/{message_id}"
            log_file = self.logger.save_report(
                user_id=user_id,
                method="Telethon",
                stats=total_stats,
                target_link=target_link,
                username=username
            )
            total_stats['log_file'] = log_file
            
            return total_stats
            
        except Exception as e:
            logger.error(f"Критическая ошибка в report_message: {e}")
            return {'valid': 0, 'invalid': 0, 'error': str(e)}

    async def can_report(self, user_id):
        if user_id in self.last_used:
            time_passed = datetime.now() - self.last_used[user_id]
            if time_passed < timedelta(minutes=report_cooldown_minutes):
                remaining = (timedelta(minutes=report_cooldown_minutes) - time_passed).seconds
                return False, remaining
        return True, 0

    async def check_sessions(self):
        if not os.path.exists(self.session_folder):
            return {'total': 0, 'valid': 0, 'invalid': 0}
        
        os.makedirs(self.no_work_folder, exist_ok=True)
        
        sessions = [f.replace('.session', '') for f in os.listdir(self.session_folder) if f.endswith('.session')]
        total = len(sessions)
        valid = 0
        invalid = 0
        session_details = []
        
        for session in sessions:
            client = None
            try:
                session_path = os.path.join(self.session_folder, f"{session}.session")
                api_id, api_hash = self.get_random_api()
                
                if not api_id or not api_hash:
                    invalid += 1
                    continue
                
                client = TelegramClient(session_path, int(api_id), api_hash, connection_retries=2)
                await asyncio.wait_for(client.connect(), timeout=10)
                
                if await client.is_user_authorized():
                    me = await client.get_me()
                    valid += 1
                    session_details.append({
                        'name': session,
                        'user_id': me.id,
                        'username': me.username or 'Нет username',
                        'phone': me.phone or 'Нет телефона'
                    })
                else:
                    invalid += 1
                    await self.move_session_to_no_work(session)
                    
            except Exception as e:
                invalid += 1
                logger.error(f"Ошибка с сессией {session}: {e}")
                await self.move_session_to_no_work(session)
                    
            finally:
                if client:
                    try:
                        await client.disconnect()
                    except:
                        pass
        
        return {'total': total, 'valid': valid, 'invalid': invalid, 'details': session_details}

    async def listen_for_auth_code(self, session_name, bot, admin_id):
        from telethon import events
        
        session_path = os.path.join(self.session_folder, f"{session_name}")
        api_id, api_hash = self.get_random_api()
        
        if not api_id or not api_hash:
            await bot.send_message(admin_id, f"❌ Нет доступных API для сессии {session_name}")
            return
        
        client = TelegramClient(session_path, int(api_id), api_hash)
        
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await bot.send_message(admin_id, f"❌ Сессия <code>{session_name}</code> невалидна.", parse_mode="HTML")
                return

            stop_event = asyncio.Event()

            @client.on(events.NewMessage(from_users=777000))
            async def handler(event):
                code = re.findall(r'\b\d{5,6}\b', event.raw_text)
                if code:
                    await bot.send_message(
                        admin_id, 
                        f"🔑 <b>Код получен!</b>\n\nАккаунт: <code>{session_name}</code>\nКод: <code>{code[0]}</code>",
                        parse_mode="HTML"
                    )
                    stop_event.set()

            await bot.send_message(admin_id, f"📡 Режим перехвата для <code>{session_name}</code>", parse_mode="HTML")
            
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=300)
            except asyncio.TimeoutError:
                await bot.send_message(admin_id, f"⏰ Время ожидания для <code>{session_name}</code> истекло.")
        
        except Exception as e:
            logger.error(f"Ошибка перехвата: {e}")
            await bot.send_message(admin_id, f"❌ Ошибка: {str(e)}")
        finally:
            await client.disconnect()

    async def check_session_detailed(self, session_name):
        try:
            session_path = os.path.join(self.session_folder, f"{session_name}.session")
            api_id, api_hash = self.get_random_api()
            
            if not api_id or not api_hash:
                return {'status': 'error', 'message': 'Нет API'}
            
            client = TelegramClient(session_path, int(api_id), api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                await self.move_session_to_no_work(session_name)
                return {'status': 'error', 'message': 'Auth error'}
            
            me = await client.get_me()
            await client.disconnect()
            
            return {
                'status': 'success', 
                'user_id': me.id, 
                'username': me.username,
                'phone': me.phone,
                'first_name': me.first_name
            }
        except Exception as e:
            await self.move_session_to_no_work(session_name)
            return {'status': 'error', 'message': str(e)}