from quart import Quart, render_template, jsonify, request
import sqlite3
import time
from datetime import datetime
import os
import sys
import json

# Add parent directory to path so we can import from database.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection

app = Quart(__name__)

def load_user_mappings():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('user_mappings', {})
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def save_user_mappings(mappings):
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        config = {'user_mappings': mappings}
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

async def get_stats():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chat_history.db')
    print(f"Connecting to database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get total message count
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        # Get unique users count
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM messages')
        unique_users = cursor.fetchone()[0]
        
        # Get messages in last 24 hours
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE datetime(timestamp) > datetime('now', '-1 day')
        ''')
        recent_messages = cursor.fetchone()[0]
        
        # Get top 5 users by message count
        cursor.execute('''
            SELECT user_id, COUNT(*) as msg_count 
            FROM messages 
            GROUP BY user_id 
            ORDER BY msg_count DESC 
            LIMIT 5
        ''')
        top_users_raw = cursor.fetchall()
        
        conn.close()

        # Map user IDs to usernames
        user_mappings = load_user_mappings()
        top_users = [(user_mappings.get(str(user_id), f"User {user_id}"), count) 
                    for user_id, count in top_users_raw]
        
        return {
            'total_messages': total_messages,
            'unique_users': unique_users,
            'recent_messages': recent_messages,
            'top_users': top_users,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"Error accessing database: {e}")
        return {
            'total_messages': 0,
            'unique_users': 0,
            'recent_messages': 0,
            'top_users': [],
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e)
        }

@app.route('/')
async def index():
    return await render_template('index.html')

@app.route('/admin')
async def admin():
    return await render_template('admin.html')

@app.route('/api/stats')
async def stats():
    return jsonify(await get_stats())

@app.route('/api/mappings', methods=['GET'])
async def get_mappings():
    return jsonify(load_user_mappings())

@app.route('/api/mappings', methods=['POST'])
async def add_mapping():
    data = await request.get_json()
    user_id = str(data.get('user_id'))
    username = data.get('username')
    
    if not user_id or not username:
        return jsonify({'error': 'Missing user_id or username'}), 400
    
    mappings = load_user_mappings()
    mappings[user_id] = username
    
    if save_user_mappings(mappings):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save mapping'}), 500

@app.route('/api/mappings/<user_id>', methods=['DELETE'])
async def delete_mapping(user_id):
    mappings = load_user_mappings()
    if user_id in mappings:
        del mappings[user_id]
        if save_user_mappings(mappings):
            return jsonify({'success': True})
    
    return jsonify({'error': 'Failed to delete mapping'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
