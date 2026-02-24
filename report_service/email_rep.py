import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import requests
from datetime import datetime, timedelta
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from report_service.report_logger import ReportLogger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Mailer:
    def __init__(self, emails_file='report_service/emails.txt', no_work_file='report_service/no_work.txt', max_workers=5):
        self.emails_file = emails_file
        self.no_work_file = no_work_file
        self.last_used = {}
        self.timeout = 30
        self.max_workers = max_workers
        self.logger = ReportLogger()
        
        self.all_mail = [
            'abuse@telegram.org',
            'dmca@telegram.org', 
            'security@telegram.org',
            'support@telegram.org',
            'recovery@telegram.org',
            'stopCA@telegram.org',
        ]
        
    def set_max_workers(self, workers):
        self.max_workers = workers
        
    def load_email_accounts(self):
        if not os.path.exists(self.emails_file):
            return []
            
        accounts = []
        with open(self.emails_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    email, password = line.split(':', 1)
                    accounts.append({'email': email.strip(), 'password': password.strip()})
        
        return accounts
        
    async def can_send_email(self, user_id):
        if user_id in self.last_used:
            time_passed = datetime.now() - self.last_used[user_id]
            if time_passed < timedelta(minutes=5):
                remaining = 300 - time_passed.seconds
                return False, remaining
        return True, 0
        
    def send_single_email(self, email_account, to_emails, subject, body, attachment_data=None):
        try:
            logger.info(f"Подключаюсь к SMTP серверу для аккаунта: {email_account['email']}")
            
            msg = MIMEMultipart()
            msg['From'] = email_account['email']
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            if attachment_data and attachment_data.get('file_path'):
                try:
                    file_url = f"https://api.telegram.org/file/bot{config.TOKEN}/{attachment_data['file_path']}"
                    response = requests.get(file_url, timeout=30)
                    
                    if response.status_code == 200:
                        img_data = response.content
                        file_ext = attachment_data['file_path'].split('.')[-1].lower()
                        mime_type = 'jpeg' if file_ext in ['jpg', 'jpeg'] else 'png'
                            
                        image = MIMEImage(img_data, _subtype=mime_type)
                        image.add_header('Content-Disposition', 'attachment', filename=f'screenshot.{file_ext}')
                        msg.attach(image)
                        logger.info(f"Скриншот прикреплен к письму от {email_account['email']}")
                except Exception as e:
                    logger.error(f"Ошибка при прикреплении скриншота: {str(e)}")
            
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=self.timeout)
            server.starttls()
            server.login(email_account['email'], email_account['password'])
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Письмо успешно отправлено с {email_account['email']}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки для {email_account['email']}: {str(e)}")
            return False

    def _process_single_account(self, account_data):
        account, target_emails, subject, body, attachment_data, index, total = account_data
        try:
            logger.info(f"Обрабатываю аккаунт {index}/{total}: {account['email']}")
            
            result = self.send_single_email(account, target_emails, subject, body, attachment_data)
            if result:
                return True, f"✅ {account['email']}: успешно"
            else:
                return False, f"❌ {account['email']}: ошибка отправки"
                
        except Exception as e:
            return False, f"❌ {account['email']}: исключение - {str(e)}"
            
    async def send_email_report(self, user_id, target_email, subject, body, attachment_data=None):
        try:
            logger.info(f"Начало отправки отчета для пользователя {user_id}")
            
            email_accounts = self.load_email_accounts()
            if not email_accounts:
                return {'success': 0, 'total': 0, 'error': 'Нет доступных email-аккаунтов'}
                
            can_send, wait_time = await self.can_send_email(user_id)
            if not can_send:
                return {'success': 0, 'total': 0, 'error': f'Пожалуйста, подождите {wait_time} секунд'}
                
            if target_email == 'all':
                target_emails = self.all_mail
            else:
                target_emails = [target_email]
                
            total_accounts = len(email_accounts)
            success = 0
            failed = 0
            
            account_data_list = []
            for i, account in enumerate(email_accounts, 1):
                account_data_list.append((account, target_emails, subject, body, attachment_data, i, total_accounts))
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self._process_single_account, data) for data in account_data_list]
                
                for future in as_completed(futures):
                    try:
                        result, _ = future.result()
                        if result:
                            success += 1
                        else:
                            failed += 1
                    except Exception as e:
                        failed += 1
                        logger.error(f"Ошибка в потоке: {str(e)}")
            
            self.last_used[user_id] = datetime.now()
            
            result_stats = {
                'success': success,
                'failed': failed,
                'total': total_accounts,
                'target_emails': target_emails
            }
            
            stats_for_log = {
                'valid': success,
                'invalid': failed,
                'total': total_accounts
            }
            
            log_file = self.logger.save_report(
                user_id=user_id,
                method="Email",
                stats=stats_for_log,
                target_link=target_email,
                username=None
            )
            result_stats['log_file'] = log_file
            
            return result_stats
        except Exception as e:
            logger.error(f"Общая ошибка при отправке отчетов: {str(e)}")
            return {'success': 0, 'total': 0, 'error': f'Произошла ошибка: {str(e)}'}

    def check_email_account(self, email_account):
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=self.timeout)
            server.starttls()
            server.login(email_account['email'], email_account['password'])
            server.quit()
            return True
        except:
            return False

    def _check_single_account(self, account_data):
        account, index, total = account_data
        logger.info(f"Проверяю аккаунт {index}/{total}: {account['email']}")
        if self.check_email_account(account):
            return True, account
        else:
            return False, account
            
    async def check_all_accounts(self):
        try:
            accounts = self.load_email_accounts()
            if not accounts:
                return {'total': 0, 'valid': 0, 'invalid': 0}
                
            stats = {'total': len(accounts), 'valid': 0, 'invalid': 0}
            invalid_accounts = []
            
            account_data_list = [(account, i, stats['total']) for i, account in enumerate(accounts, 1)]
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self._check_single_account, data) for data in account_data_list]
                
                for future in as_completed(futures):
                    try:
                        is_valid, account = future.result()
                        if is_valid:
                            stats['valid'] += 1
                        else:
                            stats['invalid'] += 1
                            invalid_accounts.append(account)
                    except Exception as e:
                        stats['invalid'] += 1
            
            if invalid_accounts:
                await self.move_invalid_accounts(invalid_accounts)
                
            return stats
        except Exception as e:
            logger.error(f"Ошибка при проверке аккаунтов: {str(e)}")
            return {'total': 0, 'valid': 0, 'invalid': 0}
        
    async def move_invalid_accounts(self, invalid_accounts):
        try:
            valid_accounts = []
            
            if os.path.exists(self.emails_file):
                with open(self.emails_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and ':' in line:
                            email, password = line.split(':', 1)
                            account = {'email': email.strip(), 'password': password.strip()}
                            if account not in invalid_accounts:
                                valid_accounts.append(line)
            
            with open(self.emails_file, 'w') as f:
                f.write('\n'.join(valid_accounts))
                
            with open(self.no_work_file, 'a') as f:
                for account in invalid_accounts:
                    line = f"{account['email']}:{account['password']}\n"
                    f.write(line)
            
            logger.info("Невалидные аккаунты перемещены")
            
        except Exception as e:
            logger.error(f"Ошибка при перемещении аккаунтов: {str(e)}")