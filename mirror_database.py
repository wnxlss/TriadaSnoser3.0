import sqlite3
import json
import logging
from datetime import datetime

class MirrorDatabase:
    def __init__(self, db_path="mirror.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mirrors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mirror_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    bot_token TEXT NOT NULL,
                    bot_username TEXT NOT NULL,
                    bot_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mirror_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mirror_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mirror_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mirror_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_visit TIMESTAMP,
                    visits_count INTEGER DEFAULT 1,
                    UNIQUE(mirror_id, user_id)
                )
            ''')
            conn.commit()
    
    def create_mirror(self, user_id, bot_token, bot_username, bot_name=""):
        mirror_id = f"mirror_{user_id}_{int(datetime.now().timestamp())}"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mirrors (mirror_id, user_id, bot_token, bot_username, bot_name, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (mirror_id, user_id, bot_token, bot_username, bot_name, 1))
            conn.commit()
        return mirror_id
    
    def get_user_mirrors_count(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM mirrors WHERE user_id = ? AND is_active = 1', (user_id,))
            return cursor.fetchone()[0]
    
    def update_mirror(self, mirror_id, **kwargs):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for key, value in kwargs.items():
                cursor.execute(f'UPDATE mirrors SET {key} = ? WHERE mirror_id = ?', (value, mirror_id))
            conn.commit()
    
    def add_log(self, mirror_id, event_type, event_data):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mirror_logs (mirror_id, event_type, event_data)
                VALUES (?, ?, ?)
            ''', (mirror_id, event_type, json.dumps(event_data, ensure_ascii=False)))
            conn.commit()
    
    def get_all_active_mirrors(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM mirrors WHERE is_active = 1 ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

mirror_db = MirrorDatabase()