import aiohttp
import asyncio
import logging
from datetime import datetime
from typing import Dict, Tuple
import re
from groq import Groq

from report_service.report_logger import ReportLogger

class TelegraphReporter:
    def __init__(self, email_rep=None, groq_api_key=None):
        self.email_rep = email_rep
        self.report_cooldown = {}
        self.cooldown_minutes = 3
        self.logger = ReportLogger()
        
        self.groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
        
        self.target_emails = [
            'abuse@telegram.org',
            'dmca@telegram.org', 
            'support@telegram.org'
        ]
        
        logging.info("TelegraphReporter инициализирован")

    async def can_report(self, user_id: int) -> Tuple[bool, int]:
        if user_id in self.report_cooldown:
            last = self.report_cooldown[user_id]
            passed = (datetime.now() - last).total_seconds()
            wait = self.cooldown_minutes * 60 - passed
            if wait > 0:
                return False, int(wait)
        return True, 0

    async def validate_url(self, url: str) -> Tuple[bool, str]:
        if not re.match(r'^https?://telegra\.ph/[a-zA-Z0-9-]+', url):
            return False, "Неверный формат ссылки"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        return True, "OK"
                    return False, f"Статья недоступна"
        except:
            return False, "Ошибка проверки ссылки"

    async def generate_text(self, url: str, reason: str, username: str = None) -> Tuple[str, str]:
        if not self.groq_client:
            return self._get_fallback_text(url, reason, username)
        
        try:
            prompts = {
                'spam': f"""Составь официальную жалобу на русском языке о спам-статье на Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: факты, ссылка, требование удалить материал\n- Без лишних объяснений, только суть\n- Формат: сначала тема, затем текст жалобы""",
                'copyright': f"""Составь официальную жалобу на русском языке о нарушении авторских прав на Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: указать на нарушение авторских прав, ссылка, требование удалить\n- Без лишних объяснений\n- Формат: сначала тема, затем текст жалобы""",
                'pornography': f"""Составь официальную жалобу на русском языке о порнографическом контенте на Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: указать на наличие порнографии, ссылка, требование удалить\n- Без лишних объяснений\n- Формат: сначала тема, затем текст жалобы""",
                'violence': f"""Составь официальную жалобу на русском языке о контенте с насилием на Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: указать на наличие сцен насилия, ссылка, требование удалить\n- Без лишних объяснений\n- Формат: сначала тема, затем текст жалобы""",
                'child_abuse': f"""Составь официальную жалобу на русском языке о жестоком обращении с детьми на Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: указать на наличие контента с жестоким обращением с детьми, ссылка, требование немедленно удалить\n- Без лишних объяснений\n- Формат: сначала тема, затем текст жалобы""",
                'drugs': f"""Составь официальную жалобу на русском языке о пропаганде наркотиков на Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: указать на пропаганду наркотиков, ссылка, требование удалить\n- Без лишних объяснений\n- Формат: сначала тема, затем текст жалобы""",
                'personal': f"""Составь официальную жалобу на русском языке об утечке личных данных на Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: указать на публикацию личных данных, ссылка, требование удалить\n- Без лишних объяснений\n- Формат: сначала тема, затем текст жалобы""",
                'other': f"""Составь официальную жалобу на русском языке о нарушении правил Telegra.ph.\n\nСсылка: {url}\n\nТребования:\n- Тема письма: кратко суть жалобы\n- Тело письма: описать нарушение, ссылка, требование удалить материал\n- Без лишних объяснений\n- Формат: сначала тема, затем текст жалобы"""
            }
            
            prompt = prompts.get(reason, prompts['other'])
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=250
            )
            
            text = response.choices[0].message.content
            
            lines = text.strip().split('\n')
            subject = lines[0][:100]
            body = '\n'.join(lines[1:]) if len(lines) > 1 else text
            
            return subject, body
            
        except Exception as e:
            logging.error(f"AI error: {e}")
            return self._get_fallback_text(url, reason, username)

    def _get_fallback_text(self, url: str, reason: str, username: str = None) -> Tuple[str, str]:
        reason_names = {
            'spam': 'СПАМ',
            'copyright': 'НАРУШЕНИЕ АВТОРСКИХ ПРАВ',
            'pornography': 'ПОРНОГРАФИЯ',
            'violence': 'НАСИЛИЕ',
            'child_abuse': 'ЖЕСТОКОЕ ОБРАЩЕНИЕ С ДЕТЬМИ',
            'drugs': 'ПРОПАГАНДА НАРКОТИКОВ',
            'personal': 'УТЕЧКА ЛИЧНЫХ ДАННЫХ',
            'other': 'НАРУШЕНИЕ ПРАВИЛ'
        }
        
        reason_name = reason_names.get(reason, 'НАРУШЕНИЕ')
        
        subject = f"Жалоба: {reason_name} на Telegra.ph"
        body = f"""
Здравствуйте,

Сообщаю о нарушении правил Telegra.ph.

Ссылка: {url}
Причина: {reason_name}

Прошу удалить данный материал.
"""
        return subject, body.strip()

    async def report_article(self, url: str, user_id: int, username: str = None, reason: str = 'spam') -> Dict:
        stats = {
            'success': 0,
            'failed': 0,
            'total': 0,
            'error': None,
            'details': []
        }
        
        if not self.email_rep:
            stats['error'] = "Email репортер не настроен"
            return stats
        
        is_valid, msg = await self.validate_url(url)
        if not is_valid:
            stats['error'] = msg
            return stats
        
        subject, body = await self.generate_text(url, reason, username)
        
        for email in self.target_emails:
            try:
                await asyncio.sleep(2)
                
                result = await self.email_rep.send_email_report(
                    user_id=user_id,
                    target_email=email,
                    subject=subject,
                    body=body,
                    attachment_data=None
                )
                
                if result and isinstance(result, dict):
                    if result.get('success', 0) > 0:
                        stats['success'] += result.get('success', 0)
                        stats['details'].append({
                            'email': email,
                            'status': 'success',
                            'count': result.get('success', 0)
                        })
                    else:
                        stats['failed'] += 1
                        stats['details'].append({
                            'email': email,
                            'status': 'failed',
                            'error': result.get('error', 'Unknown error')
                        })
                else:
                    stats['success'] += 1
                    stats['details'].append({
                        'email': email,
                        'status': 'success',
                        'count': 1
                    })
                
            except Exception as e:
                stats['failed'] += 1
                stats['details'].append({
                    'email': email,
                    'status': 'error',
                    'error': str(e)
                })
                logging.error(f"Ошибка отправки на {email}: {e}")
        
        stats['total'] = stats['success'] + stats['failed']
        
        self.report_cooldown[user_id] = datetime.now()
        
        stats_for_log = {
            'valid': stats['success'],
            'invalid': stats['failed'],
            'total': stats['total']
        }
        
        log_file = self.logger.save_report(
            user_id=user_id,
            method="Telegraph",
            stats=stats_for_log,
            target_link=url,
            username=username
        )
        stats['log_file'] = log_file
        
        logging.info(f"Telegraph report completed: {stats['success']} success, {stats['failed']} failed")
        
        return stats