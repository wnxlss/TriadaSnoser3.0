import logging
from telethon.tl.types import Channel, Chat, User
import re

logger = logging.getLogger('LinkParser')

class LinkParser:
    @staticmethod
    def validate_link_type(message_url):
        if '/c/' in message_url:
            raise ValueError("Ссылка ведет на приватный чат. Репорты можно отправлять только в публичные группы")
        
        clean_url = message_url.split('?')[0]
        path_parts = clean_url[len('https://t.me/'):].split('/')
        
        if len(path_parts) == 1:
            raise ValueError("Вы указали ссылку на профиль или канал. Нужно указать ссылку на конкретное сообщение в группе")
        
        message_id_part = path_parts[1]
        if not any(char.isdigit() for char in message_id_part):
            raise ValueError("Неверный формат ссылки. Убедитесь, что ссылка ведет на сообщение (в конце должны быть цифры)")
        
        return True

    @staticmethod
    def extract_username_and_message_id(message_url):
        try:
            if not message_url.startswith('https://t.me/'):
                raise ValueError("URL должен начинаться с https://t.me/")
            
            LinkParser.validate_link_type(message_url)
            
            clean_url = message_url.split('?')[0]
            path = clean_url[len('https://t.me/'):].split('/')
            
            username = path[0]
            message_id = int(path[1])
            
            return username, message_id
        except (IndexError, ValueError) as e:
            raise ValueError(f"Ошибка при разборе ссылки: {str(e)}")

    @staticmethod
    async def check_chat_type(client, chat_username):
        try:
            entity = await client.get_entity(chat_username)
            
            if isinstance(entity, User):
                raise ValueError("Репорты на пользователей запрещены. Только сообщения в группах")
            
            if isinstance(entity, Channel):
                if entity.broadcast:
                    raise ValueError("Это ссылка на канал. Репорты на каналы запрещены, только на группы")
                return True
            
            if isinstance(entity, Chat):
                return True
                
            raise ValueError("Тип чата не поддерживается для отправки репортов")
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Ошибка проверки типа чата {chat_username}: {str(e)}")
            raise ValueError(f"Не удалось проверить чат. Возможно, он недоступен")

    @staticmethod
    async def is_allowed_chat(client, chat_username, message_id=None):
        try:
            entity = await client.get_entity(chat_username)
            
            if isinstance(entity, Channel):
                return not entity.broadcast
            
            if isinstance(entity, Chat):
                return True
            
            return False
        except Exception:
            return False