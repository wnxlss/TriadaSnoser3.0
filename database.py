import sqlite3
from datetime import datetime, timedelta
import os

class Database:
    def __init__(self, db_name='users.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id BIGINT PRIMARY KEY, 
                subscribe DATETIME,
                welcome_pinned INTEGER DEFAULT 0,
                captcha_passed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
       
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN welcome_pinned INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN captcha_passed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports(
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT,
                target_link TEXT,
                reason TEXT,
                method TEXT,
                date DATETIME
            )
        """)
        
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promocodes(
                code TEXT PRIMARY KEY, 
                days INTEGER, 
                uses INTEGER, 
                max_uses INTEGER
            )
        """)
        
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS used_promocodes(
                user_id BIGINT,
                promocode TEXT,
                used_at DATETIME,
                PRIMARY KEY (user_id, promocode)
            )
        """)
        
       
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals(
                referrer_id BIGINT, 
                referred_id BIGINT PRIMARY KEY, 
                date DATETIME
            )
        """)
        
       
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referral_counts(
                user_id BIGINT PRIMARY KEY, 
                count INTEGER DEFAULT 0
            )
        """)
        
     
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments(
                invoice_id TEXT PRIMARY KEY,
                user_id BIGINT,
                sub_type TEXT,
                days INTEGER,
                price REAL,
                currency TEXT,
                method TEXT,
                paid BOOLEAN DEFAULT FALSE,
                created_at DATETIME,
                message_chat_id BIGINT,
                message_id INTEGER
            )
        """)
        
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS premium_users(
                user_id BIGINT PRIMARY KEY,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until DATETIME,
                created_at DATETIME
            )
        """)
        
       
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT,
                session_name TEXT UNIQUE,
                phone TEXT,
                added_at DATETIME,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id)")
        
        self.conn.commit()

    
    
    def needs_captcha(self, user_id):
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT captcha_passed FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            
            # Если пользователь не найден или не проходил капчу
            if not result or result[0] == 0:
                return True
            return False
        except Exception as e:
            print(f"Error checking captcha status: {e}")
            return True  

    def set_captcha_passed(self, user_id):
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE users SET captcha_passed = 1 WHERE user_id = ?",
                (user_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error setting captcha passed: {e}")
            return False

    
    
    def add_report_history(self, user_id, target_link, reason, method):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO reports (user_id, target_link, reason, method, date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, target_link, reason, method, datetime.now().strftime("%d.%m.%Y %H:%M")))
        self.conn.commit()

    def get_reports_paginated(self, user_id, page=1, per_page=5):
        offset = (page - 1) * per_page
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT target_link, reason, method, date 
            FROM reports WHERE user_id = ? 
            ORDER BY report_id DESC LIMIT ? OFFSET ?
        """, (user_id, per_page, offset))
        items = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM reports WHERE user_id = ?", (user_id,))
        total_count = cursor.fetchone()[0]
        return items, total_count

    
    
    def user_exists(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

    def add_user(self, user_id):
        cursor = self.conn.cursor()
        if not self.user_exists(user_id):
            cursor.execute("""
                INSERT INTO users (user_id, subscribe, welcome_pinned, captcha_passed) 
                VALUES(?, ?, ?, ?)
            """, (user_id, "1999-01-01 20:00:00", False, 0))
            self.conn.commit()

    def check_welcome_pinned(self, user_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT welcome_pinned FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return bool(result[0]) if result else False
        except:
            return False

    def set_welcome_pinned(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET welcome_pinned = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_subscription(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT subscribe FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        return None

    def update_subscription(self, user_id, days):
        current_sub = self.get_subscription(user_id)
        if current_sub and current_sub > datetime.now():
            new_date = current_sub + timedelta(days=days)
        else:
            new_date = datetime.now() + timedelta(days=days)
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET subscribe = ? WHERE user_id = ?", 
                      (new_date.strftime("%Y-%m-%d %H:%M:%S"), user_id))
        self.conn.commit()
        return new_date

    def clear_subscription(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET subscribe = ? WHERE user_id = ?", ("1999-01-01 20:00:00", user_id))
        self.conn.commit()

    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]

    def get_user_count(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

    def get_active_subscriptions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscribe > datetime('now')")
        return cursor.fetchone()[0]

  
    
    def add_referral(self, referrer_id, referred_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO referrals VALUES(?, ?, ?)", 
                          (referrer_id, referred_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            cursor.execute("INSERT OR IGNORE INTO referral_counts VALUES(?, ?)", (referrer_id, 0))
            cursor.execute("UPDATE referral_counts SET count = count + 1 WHERE user_id = ?", (referrer_id,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_referral_count(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT count FROM referral_counts WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def reset_referral_count(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE referral_counts SET count = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()

   
    
    def create_promocode(self, code: str, days: int, max_uses: int):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO promocodes (code, days, uses, max_uses) VALUES (?, ?, ?, ?)",
                (code.upper(), days, 0, max_uses)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_promocode(self, code: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT code, days, uses, max_uses FROM promocodes WHERE code = ?",
            (code.upper(),)
        )
        result = cursor.fetchone()
        if result:
            return {'code': result[0], 'days': result[1], 'uses': result[2], 'max_uses': result[3]}
        return None

    def use_promocode(self, code: str, user_id: int):
        cursor = self.conn.cursor()
        promocode = self.get_promocode(code)
        if not promocode:
            return False, "Промокод не найден"
        if promocode['uses'] >= promocode['max_uses']:
            cursor.execute("DELETE FROM promocodes WHERE code = ?", (code.upper(),))
            self.conn.commit()
            return False, "Промокод уже использован"
        cursor.execute("SELECT 1 FROM used_promocodes WHERE user_id = ? AND promocode = ?", (user_id, code.upper()))
        if cursor.fetchone():
            return False, "Вы уже использовали этот промокод"
        cursor.execute("UPDATE promocodes SET uses = uses + 1 WHERE code = ?", (code.upper(),))
        cursor.execute("INSERT INTO used_promocodes (user_id, promocode, used_at) VALUES (?, ?, ?)",
                      (user_id, code.upper(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()
        return True, promocode['days']

    def delete_promocode(self, code: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM promocodes WHERE code = ?", (code.upper(),))
        deleted = cursor.rowcount
        self.conn.commit()
        return deleted > 0

    
    
    def add_payment(self, invoice_id, user_id, sub_type, days, price, currency, method, message_chat_id, message_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO payments 
                (invoice_id, user_id, sub_type, days, price, currency, method, paid, created_at, message_chat_id, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_id, user_id, sub_type, days, price, currency, method, False, 
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message_chat_id, message_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_payment(self, invoice_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE invoice_id = ?", (invoice_id,))
        result = cursor.fetchone()
        if result:
            return {
                'invoice_id': result[0], 'user_id': result[1], 'sub_type': result[2],
                'days': result[3], 'price': result[4], 'currency': result[5],
                'method': result[6], 'paid': bool(result[7]),
                'created_at': datetime.strptime(result[8], "%Y-%m-%d %H:%M:%S"),
                'message_chat_id': result[9], 'message_id': result[10]
            }
        return None

    def update_payment_status(self, invoice_id, paid=True):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE payments SET paid = ? WHERE invoice_id = ?", (paid, invoice_id))
        self.conn.commit()

    def cleanup_old_payments(self, hours=2):
        cursor = self.conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM payments WHERE paid = FALSE AND created_at < ?", (cutoff_time,))
        self.conn.commit()

    
    
    def set_premium_subscription(self, user_id, days):
        cursor = self.conn.cursor()
        premium_until = datetime.now() + timedelta(days=days)
        cursor.execute("""
            INSERT OR REPLACE INTO premium_users (user_id, is_premium, premium_until, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, True, premium_until.strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()
        return premium_until

    def get_premium_status(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_premium, premium_until FROM premium_users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            is_premium = bool(result[0])
            premium_until = datetime.strptime(result[1], "%Y-%m-%d %H:%M:%S")
            return {'is_premium': is_premium and premium_until > datetime.now(), 'premium_until': premium_until}
        return {'is_premium': False, 'premium_until': None}

    def remove_premium_subscription(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE premium_users 
            SET is_premium = FALSE, premium_until = ? 
            WHERE user_id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        self.conn.commit()


    
    def get_stats_data(self):
        cursor = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

      
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

      
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscribe > ?", (now,))
        active_regular = cursor.fetchone()[0]

       
        cursor.execute("SELECT COUNT(*) FROM premium_users WHERE is_premium = 1 AND premium_until > ?", (now,))
        active_premium = cursor.fetchone()[0]

       
        emails_count = 0
        try:
            file_path = os.path.join('report_service', 'emails.txt')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    emails_count = sum(1 for line in f if line.strip())
        except Exception as e:
            print(f"Ошибка при чтении файла почт: {e}")
            emails_count = 0

        return {
            "total_users": total_users,
            "active_regular": active_regular,
            "active_premium": active_premium,
            "emails_count": emails_count
        }

   
    
    def add_user_session(self, user_id, session_name, phone):
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_name, phone, added_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, session_name, phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_sessions(self, user_id):
       
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT session_name, phone, added_at, is_active 
            FROM user_sessions 
            WHERE user_id = ? 
            ORDER BY added_at DESC
        """, (user_id,))
        return cursor.fetchall()

    def deactivate_user_session(self, session_name):
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE user_sessions 
            SET is_active = FALSE 
            WHERE session_name = ?
        """, (session_name,))
        self.conn.commit()

    def close(self):
        self.conn.close()