import os
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify
import requests

TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 8080))
DATA_FILE = 'vip_users.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_data(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Save error: {e}")

    def get_user(self, user_id):
        if user_id not in self.data:
            self.data[user_id] = {
                'user_id': user_id,
                'points': 0,
                'total_earned': 0,
                'vip_level': 0,
                'vip_points': 0,
                'daily_streak': 0,
                'last_daily': None,
                'username': '',
                'first_name': '',
                'last_name': '',
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            self._save_data()
        return self.data[user_id]

    def save_user(self, user_id, data):
        self.data[user_id] = data
        self._save_data()

    def get_all_users(self):
        return self.data

storage = Storage()

def send_message(chat_id, text, parse_mode='Markdown'):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }, timeout=10)
        if response.status_code == 200:
            logger.info(f"Message sent to {chat_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get('result', [])
        return []
    except Exception as e:
        logger.error(f"Get updates error: {e}")
        return []

def delete_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
    try:
        response = requests.get(url, timeout=10)
        logger.info(f"Webhook deleted: {response.json()}")
        return response.json().get('ok', False)
    except Exception as e:
        logger.error(f"Delete webhook error: {e}")
        return False

VIP_LEVELS = {
    0: {'name': 'Member', 'emoji': '🔰', 'points_required': 0},
    1: {'name': 'Bronze', 'emoji': '🥉', 'points_required': 100},
    2: {'name': 'Silver', 'emoji': '🥈', 'points_required': 500},
    3: {'name': 'Gold', 'emoji': '🥇', 'points_required': 1000},
    4: {'name': 'Platinum', 'emoji': '💎', 'points_required': 5000},
    5: {'name': 'Diamond', 'emoji': '👑', 'points_required': 10000}
}

VIP_BENEFITS = {
    0: ['Basic rewards', 'Standard claims'],
    1: ['10% bonus on daily rewards', 'Bronze badge', 'Access to basic rewards'],
    2: ['20% bonus on daily rewards', 'Weekly bonus chest', 'Silver badge', 'Priority queue'],
    3: ['30% bonus on daily rewards', 'Exclusive drops', 'Gold badge', 'VIP support'],
    4: ['50% bonus on daily rewards', 'VIP rewards club', 'Platinum badge', '24/7 support', 'Exclusive events'],
    5: ['100% bonus on daily rewards', 'Elite rewards', 'Diamond badge', 'Personalized offers', 'Free claims']
}

def get_vip_level(user):
    points = user.get('vip_points', 0)
    if points >= 10000:
        return 5
    elif points >= 5000:
        return 4
    elif points >= 1000:
        return 3
    elif points >= 500:
        return 2
    elif points >= 100:
        return 1
    return 0

def get_vip_info(level):
    return VIP_LEVELS.get(level, VIP_LEVELS[0])

def get_vip_benefits(level):
    return VIP_BENEFITS.get(level, VIP_BENEFITS[0])

def get_streak_emoji(streak):
    if streak >= 100:
        return "👑"
    elif streak >= 50:
        return "💎"
    elif streak >= 30:
        return "🌟"
    elif streak >= 14:
        return "⭐"
    elif streak >= 7:
        return "🔥"
    return "💪"

def get_time_until(iso_time):
    if not iso_time:
        return "Available now!"
    try:
        last = datetime.fromisoformat(iso_time)
        next_time = last + timedelta(hours=24)
        now = datetime.now()
        if now >= next_time:
            return "Available now!"
        diff = next_time - now
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    except:
        return "Available now!"

def handle_start(chat_id, user_data):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    user['username'] = user_data.get('username', '')
    user['first_name'] = user_data.get('first_name', 'User')
    user['last_name'] = user_data.get('last_name', '')
    user['last_active'] = datetime.now().isoformat()
    storage.save_user(user_id, user)
    
    vip_level = get_vip_level(user)
    vip_info = get_vip_info(vip_level)
    
    welcome = f"""
👑 *WELCOME TO VIP REWARDS PRO!*

👋 *Hello {user['first_name']}!*

{vip_info['emoji']} *VIP Level: {vip_info['name']}*
📊 *VIP Points: {user.get('vip_points', 0)}*
💰 *Points: {user['points']}*
📅 *Streak: {user['daily_streak']} days*

📋 *Available Commands:*
/vip - Check VIP status 🌟
/daily - Claim daily reward 📅
/upgrade - Upgrade VIP level 📈
/profile - View your profile 👤
/leaderboard - Top VIPs 🏆
/help - All commands 📚

🔥 *VIP Benefits:*
• Bonus points on daily claims
• Exclusive rewards per tier
• Higher tiers = more perks

*Use /vip to see all benefits!*
    """
    send_message(chat_id, welcome)

def handle_help(chat_id):
    help_text = """
📚 *VIP REWARDS PRO COMMANDS*
━━━━━━━━━━━━━━━━

👑 *VIP Commands:*
/vip - Check VIP status
/daily - Claim daily reward
/upgrade - Upgrade VIP level

📊 *Info Commands:*
/profile - View your profile
/leaderboard - Top VIPs
/help - This menu

⭐ *VIP Levels:*
🔰 Member → 🥉 Bronze → 🥈 Silver → 🥇 Gold → 💎 Platinum → 👑 Diamond

💡 *Earn VIP points by:*
• Daily claims (+1 each)
• Streaks (+1 per week)
• Referrals (+10 each)
    """
    send_message(chat_id, help_text)

def handle_daily(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    now = datetime.now()
    
    if user.get('last_daily'):
        try:
            last = datetime.fromisoformat(user['last_daily'])
            if now - last < timedelta(hours=24):
                time_left = get_time_until(user['last_daily'])
                send_message(
                    chat_id,
                    f"""
⏳ *Already Claimed Today!*
━━━━━━━━━━━━━━━━
🕐 Next claim in: {time_left}

📅 Current Streak: {user['daily_streak']} days
👑 VIP Level: {get_vip_info(get_vip_level(user))['emoji']} {get_vip_info(get_vip_level(user))['name']}
                    """
                )
                return
        except:
            pass
    
    if user.get('last_daily'):
        try:
            last = datetime.fromisoformat(user['last_daily'])
            if now - last < timedelta(hours=48):
                user['daily_streak'] += 1
            else:
                user['daily_streak'] = 1
        except:
            user['daily_streak'] = 1
    else:
        user['daily_streak'] = 1
    
    base_reward = 10
    vip_level = get_vip_level(user)
    vip_bonus = vip_level * 2
    streak_bonus = (user['daily_streak'] // 7) * 5
    total_reward = base_reward + vip_bonus + streak_bonus
    
    user['vip_points'] = user.get('vip_points', 0) + 1
    user['points'] += total_reward
    user['total_earned'] = user.get('total_earned', 0) + total_reward
    user['last_daily'] = now.isoformat()
    storage.save_user(user_id, user)
    
    new_vip_level = get_vip_level(user)
    vip_info = get_vip_info(new_vip_level)
    emoji = get_streak_emoji(user['daily_streak'])
    
    message = f"""
🎉 *Daily Reward Claimed!*
━━━━━━━━━━━━━━━━
{emoji} *Reward: +{total_reward} points*
📊 *Base: {base_reward}*
👑 *VIP Bonus: +{vip_bonus}*
📅 *Streak: {user['daily_streak']} days*

{vip_info['emoji']} *VIP Level: {vip_info['name']}*
💰 *Total Points: {user['points']}*
⭐ *VIP Points: {user['vip_points']}*

Come back tomorrow for more! 🚀
    """
    send_message(chat_id, message)

def handle_vip(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    
    vip_level = get_vip_level(user)
    vip_info = get_vip_info(vip_level)
    benefits = get_vip_benefits(vip_level)
    
    next_level = vip_level + 1 if vip_level < 5 else None
    next_info = get_vip_info(next_level) if next_level else None
    
    message = f"""
👑 *VIP REWARDS PRO*
━━━━━━━━━━━━━━━━
{vip_info['emoji']} *Level: {vip_info['name']}*
📊 *VIP Points: {user.get('vip_points', 0)}*
💰 *Points: {user['points']}*
📅 *Streak: {user['daily_streak']} days*

🎁 *Your Benefits:*
{chr(10).join([f'• {b}' for b in benefits])}
    """
    
    if next_level and next_info:
        points_required = VIP_LEVELS[next_level]['points_required']
        current = user.get('vip_points', 0)
        needed = max(0, points_required - current)
        progress = min(100, (current / points_required) * 100) if points_required > 0 else 0
        
        message += f"""
━━━━━━━━━━━━━━━━
📈 *Next Level: {next_info['emoji']} {next_info['name']}*
🎯 *Progress: {int(progress)}%*
💪 *Points needed: {needed}*

💡 *Earn VIP points by:*
• Daily claims (+1 each)
• Streaks (+1 per week)
• Referrals (+10 each)
        """
    else:
        message += """
━━━━━━━━━━━━━━━━
🏆 *MAX LEVEL REACHED!*
You are a {vip_info['emoji']} {vip_info['name']} VIP!

Keep earning to maintain your status!
        """
    
    send_message(chat_id, message)

def handle_upgrade(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    
    vip_level = get_vip_level(user)
    
    if vip_level >= 5:
        send_message(chat_id, "👑 You're already at the highest VIP level!")
        return
    
    next_level = vip_level + 1
    next_info = get_vip_info(next_level)
    points_required = VIP_LEVELS[next_level]['points_required']
    current = user.get('vip_points', 0)
    
    if current >= points_required:
        send_message(
            chat_id,
            f"""
🎊 *VIP UPGRADE AVAILABLE!*
━━━━━━━━━━━━━━━━
{next_info['emoji']} *You qualify for {next_info['name']}!*

🎁 *New Benefits:*
{chr(10).join([f'• {b}' for b in get_vip_benefits(next_level)])}

Use /vip to see your new status!
            """
        )
    else:
        needed = points_required - current
        progress = min(100, (current / points_required) * 100)
        
        send_message(
            chat_id,
            f"""
📈 *Upgrade to {next_info['emoji']} {next_info['name']}*
━━━━━━━━━━━━━━━━
🎯 *Progress: {int(progress)}%*
💪 *Points needed: {needed}*
📊 *Current: {current}/{points_required}*

💡 *Earn more VIP points by:*
• Daily claims (+1 each)
• Building streaks (+1 per week)
• Referring friends (+10 each)
            """
        )

def handle_profile(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    
    vip_level = get_vip_level(user)
    vip_info = get_vip_info(vip_level)
    benefits = get_vip_benefits(vip_level)
    emoji = get_streak_emoji(user['daily_streak'])
    
    all_users = storage.get_all_users()
    sorted_users = sorted(
        [(uid, data) for uid, data in all_users.items()],
        key=lambda x: x[1].get('vip_points', 0),
        reverse=True
    )
    
    rank = 1
    for i, (uid, data) in enumerate(sorted_users, 1):
        if uid == user_id:
            rank = i
            break
    
    profile_text = f"""
👤 *YOUR PROFILE*
━━━━━━━━━━━━━━━━

👤 *Name:* {user.get('first_name', 'User')}
📛 *Username:* @{user.get('username', 'N/A')}

👑 *VIP Status:*
• Level: {vip_info['emoji']} {vip_info['name']}
• VIP Points: {user.get('vip_points', 0)}
• Rank: #{rank} of {len(sorted_users)} users

💰 *Balance:*
• Points: {user['points']}
• Total Earned: {user.get('total_earned', 0)}
• Streak: {user['daily_streak']} days {emoji}

🎁 *VIP Benefits:*
{chr(10).join([f'• {b}' for b in benefits])}
    """
    send_message(chat_id, profile_text)

def handle_leaderboard(chat_id):
    all_users = storage.get_all_users()
    
    sorted_users = sorted(
        [(uid, data) for uid, data in all_users.items()],
        key=lambda x: x[1].get('vip_points', 0),
        reverse=True
    )[:10]
    
    if not sorted_users:
        send_message(chat_id, "No VIP users yet! Be the first! 🏆")
        return
    
    message = "👑 *VIP LEADERBOARD* 👑\n━━━━━━━━━━━━━━━━\n\n"
    message += "📊 *Top 10 VIP Players*\n\n"
    
    for i, (uid, data) in enumerate(sorted_users, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f"{i}."
        name = data.get('username', data.get('first_name', f"User{uid}"))
        vip_level = get_vip_level(data)
        vip_info = get_vip_info(vip_level)
        vip_points = data.get('vip_points', 0)
        points = data.get('points', 0)
        
        message += f"{medal} @{name} {vip_info['emoji']}\n"
        message += f"   VIP: {vip_points} pts | Points: {points}\n"
    
    send_message(chat_id, message)

def process_updates():
    last_update_id = 0
    logger.info("Starting polling loop...")
    
    delete_webhook()
    
    while True:
        try:
            updates = get_updates(last_update_id + 1 if last_update_id else None)
            
            for update in updates:
                update_id = update.get('update_id')
                if update_id:
                    last_update_id = update_id
                
                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    user_data = msg.get('from', {})
                    
                    if 'text' in msg:
                        text = msg['text']
                        logger.info(f"Command from {chat_id}: {text}")
                        
                        if text.startswith('/start'):
                            handle_start(chat_id, user_data)
                        elif text.startswith('/help'):
                            handle_help(chat_id)
                        elif text.startswith('/daily'):
                            handle_daily(chat_id)
                        elif text.startswith('/vip'):
                            handle_vip(chat_id)
                        elif text.startswith('/upgrade'):
                            handle_upgrade(chat_id)
                        elif text.startswith('/profile'):
                            handle_profile(chat_id)
                        elif text.startswith('/leaderboard'):
                            handle_leaderboard(chat_id)
                        else:
                            send_message(
                                chat_id,
                                "❓ Unknown command. Use /help to see available commands."
                            )
            
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Process updates error: {e}")
            time.sleep(5)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    all_users = storage.get_all_users()
    vip_users = sum(1 for data in all_users.values() if get_vip_level(data) > 0)
    total_vip_points = sum(data.get('vip_points', 0) for data in all_users.values())
    
    return f"""
    <h1>👑 VIP Rewards Pro Bot</h1>
    <p>Bot is running!</p>
    <p>Users: {len(all_users)}</p>
    <p>VIP Users: {vip_users}</p>
    <p>Total VIP Points: {total_vip_points}</p>
    <p>Status: ✅ Active</p>
    <p>Bot: @viprewardspro_bot</p>
    """

@app.route('/stats', methods=['GET'])
def stats_route():
    all_users = storage.get_all_users()
    return jsonify({
        'users': len(all_users),
        'vip_users': sum(1 for data in all_users.values() if get_vip_level(data) > 0),
        'total_vip_points': sum(data.get('vip_points', 0) for data in all_users.values()),
        'total_points': sum(data.get('points', 0) for data in all_users.values())
    })

def main():
    logger.info("=" * 50)
    logger.info("Starting VIP Rewards Pro Bot...")
    logger.info(f"Bot: @viprewardspro_bot")
    logger.info(f"Data File: {DATA_FILE}")
    logger.info("=" * 50)
    
    poll_thread = threading.Thread(target=process_updates, daemon=True)
    poll_thread.start()
    logger.info("Polling thread started")
    
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
