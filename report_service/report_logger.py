import os
from datetime import datetime
from typing import Dict, Any, Optional

class ReportLogger:
    def __init__(self):
        pass
    
    def save_report(self, user_id: int, method: str, stats: Dict[str, Any],
                   target_link: str = None, username: str = None) -> str:
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        display_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        
        offender_info = stats.get('offender_info', {})
        valid = stats.get('valid', 0)
        invalid = stats.get('invalid', 0)
        
        if valid > 0:
            status = "Успешно"
            status_color = "success"
        else:
            status = "Неудача"
            status_color = "error"
        
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет #{user_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: radial-gradient(circle at 50% 50%, #1a1a2e, #0a0a0f);
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }}

       
        body::before {{
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 30%, rgba(108, 242, 194, 0.03) 0%, transparent 30%),
                radial-gradient(circle at 80% 70%, rgba(100, 150, 255, 0.03) 0%, transparent 35%),
                repeating-linear-gradient(45deg, rgba(255,255,255,0.01) 0px, rgba(255,255,255,0.01) 1px, transparent 1px, transparent 20px);
            pointer-events: none;
        }}

        .card {{
            max-width: 560px;
            width: 100%;
            background: rgba(18, 18, 26, 0.75);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: 32px;
            padding: 36px;
            box-shadow: 
                0 30px 60px -15px rgba(0, 0, 0, 0.8),
                0 0 0 1px rgba(255, 255, 255, 0.03) inset,
                0 0 30px rgba(108, 242, 194, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.02);
            position: relative;
            z-index: 1;
            animation: cardAppear 0.6s ease-out;
        }}

        @keyframes cardAppear {{
            0% {{
                opacity: 0;
                transform: translateY(20px) scale(0.98);
            }}
            100% {{
                opacity: 1;
                transform: translateY(0) scale(1);
            }}
        }}

        .header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 30px;
            position: relative;
        }}

        .icon {{
            width: 56px;
            height: 56px;
            background: linear-gradient(145deg, #1e1e2e, #15151f);
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: 
                0 8px 20px rgba(0, 0, 0, 0.4),
                0 0 0 1px rgba(108, 242, 194, 0.3) inset,
                0 0 15px rgba(108, 242, 194, 0.2);
            color: #6cf2c2;
            position: relative;
            overflow: hidden;
        }}

        .icon::after {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(108, 242, 194, 0.1), transparent);
            animation: shine 4s infinite;
        }}

        @keyframes shine {{
            0% {{ transform: translateX(-100%) translateY(-100%) rotate(45deg); }}
            100% {{ transform: translateX(100%) translateY(100%) rotate(45deg); }}
        }}

        .title {{
            font-size: 28px;
            font-weight: 600;
            background: linear-gradient(135deg, #ffffff, #b0b0c0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
            text-shadow: 0 2px 10px rgba(255,255,255,0.1);
        }}

        .badge {{
            display: inline-block;
            padding: 8px 24px;
            background: rgba(18, 18, 26, 0.7);
            backdrop-filter: blur(10px);
            border-radius: 100px;
            font-size: 15px;
            font-weight: 500;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            color: {'#6cf2c2' if valid > 0 else '#ff6b6b'};
            border-color: {'rgba(108, 242, 194, 0.2)' if valid > 0 else 'rgba(255, 107, 107, 0.2)'};
            text-shadow: 0 0 10px {'rgba(108, 242, 194, 0.3)' if valid > 0 else 'rgba(255, 107, 107, 0.3)'};
            animation: badgePulse 2s infinite;
        }}

        @keyframes badgePulse {{
            0% {{ box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), 0 0 0 0 {'rgba(108, 242, 194, 0.3)' if valid > 0 else 'rgba(255, 107, 107, 0.3)'}; }}
            50% {{ box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 15px {'rgba(108, 242, 194, 0.2)' if valid > 0 else 'rgba(255, 107, 107, 0.2)'}; }}
            100% {{ box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), 0 0 0 0 {'rgba(108, 242, 194, 0.3)' if valid > 0 else 'rgba(255, 107, 107, 0.3)'}; }}
        }}

        .grid {{
            display: grid;
            gap: 12px;
            margin: 30px 0;
        }}

        .row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(5px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.02);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .row::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            width: 3px;
            background: linear-gradient(135deg, #6cf2c2, #4ac7a2);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}

        .row:hover {{
            background: rgba(40, 40, 55, 0.3);
            border-color: rgba(108, 242, 194, 0.2);
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }}

        .row:hover::before {{
            opacity: 1;
        }}

        .label {{
            color: #a0a0b5;
            font-size: 14px;
            font-weight: 500;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .label::before {{
            content: '●';
            color: #6cf2c2;
            font-size: 8px;
            opacity: 0.5;
        }}

        .value {{
            color: #ffffff;
            font-size: 15px;
            font-weight: 500;
            background: rgba(0, 0, 0, 0.2);
            padding: 6px 14px;
            border-radius: 40px;
            border: 1px solid rgba(255, 255, 255, 0.03);
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
        }}

        .method-tag {{
            background: rgba(108, 242, 194, 0.03);
            color: #6cf2c2;
            padding: 6px 16px;
            border-radius: 40px;
            font-size: 13px;
            font-weight: 600;
            border: 1px solid rgba(108, 242, 194, 0.2);
            backdrop-filter: blur(5px);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .link {{
            color: #6cf2c2;
            text-decoration: none;
            font-size: 14px;
            word-break: break-all;
            transition: all 0.3s ease;
            background: rgba(108, 242, 194, 0.03);
            padding: 6px 14px;
            border-radius: 40px;
            border: 1px solid rgba(108, 242, 194, 0.1);
            max-width: 250px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .link:hover {{
            background: rgba(108, 242, 194, 0.1);
            border-color: rgba(108, 242, 194, 0.3);
            text-decoration: none;
            transform: scale(1.02);
        }}

        .footer {{
            text-align: center;
            margin-top: 35px;
            padding-top: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.03);
            color: #5f5f7a;
            font-size: 13px;
            letter-spacing: 0.5px;
            position: relative;
        }}

        .footer::before {{
            content: '';
            position: absolute;
            top: -1px;
            left: 50%;
            transform: translateX(-50%);
            width: 50px;
            height: 1px;
            background: linear-gradient(90deg, transparent, #6cf2c2, transparent);
        }}

        .time {{
            font-family: 'JetBrains Mono', 'Monaco', monospace;
            font-size: 13px;
            letter-spacing: 0.5px;
        }}

        
        .glow-text {{
            text-shadow: 0 0 20px currentColor;
        }}

        .user-id {{
            color: #6cf2c2;
            font-weight: 600;
        }}

        @media (max-width: 480px) {{
            .card {{
                padding: 24px;
            }}
            
            .row {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
            
            .link {{
                max-width: 100%;
                white-space: normal;
            }}
        }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="icon">📋</div>
            <div class="title">Отчет о репорте</div>
        </div>
        
        <div class="badge">{status}</div>
        
        <div class="grid">
            <div class="row">
                <span class="label">Время</span>
                <span class="value time">{display_time}</span>
            </div>
            
            <div class="row">
                <span class="label">Отправитель</span>
                <span class="value">@{username or 'Не указан'} · <span class="user-id">{user_id}</span></span>
            </div>
            
            <div class="row">
                <span class="label">Метод</span>
                <span class="method-tag">{method}</span>
            </div>
            
            {f'''
            <div class="row">
                <span class="label">Ссылка</span>
                <a href="{target_link}" class="link" target="_blank">{target_link[:40]}{'...' if target_link and len(target_link) > 40 else ''}</a>
            </div>
            ''' if target_link else ''}
            
            <div class="row">
                <span class="label">Цель</span>
                <span class="value">@{offender_info.get('username', 'Нет')} · <span class="user-id">{offender_info.get('id', 'N/A')}</span></span>
            </div>
        </div>
        
        <div class="footer">
            <span class="glow-text">✦ TRIADA SNOSER ✦</span><br>
            {display_time.split()[0]}
        </div>
    </div>
</body>
</html>"""
        
        filename = f'report_{user_id}_{timestamp}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filename