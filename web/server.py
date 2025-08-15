from quart import Quart, render_template, jsonify, request
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
    try:
        conn = await get_db_connection()
        
        # Get total message count
        async with conn.execute('SELECT COUNT(*) FROM messages') as cursor:
            total_messages = (await cursor.fetchone())[0]
        
        # Get unique users count
        async with conn.execute('SELECT COUNT(DISTINCT user_id) FROM messages') as cursor:
            unique_users = (await cursor.fetchone())[0]
        
        # Get messages in last 24 hours
        async with conn.execute('''
            SELECT COUNT(*) FROM messages
            WHERE datetime(timestamp) > datetime('now', '-1 day')
        ''') as cursor:
            recent_messages = (await cursor.fetchone())[0]
        
        # Get top 5 users by message count
        async with conn.execute('''
            SELECT user_id, COUNT(*) as msg_count
            FROM messages
            GROUP BY user_id
            ORDER BY msg_count DESC
            LIMIT 5
        ''') as cursor:
            top_users_raw = await cursor.fetchall()
        
        await conn.close()

        # Map user IDs to usernames
        user_mappings = load_user_mappings()
        top_users = [(user_mappings.get(str(user_id), f"User {user_id}"), count)
                    for user_id, count in top_users_raw]
        
        # If user mappings are missing, attempt to pull usernames from the database
        if len(top_users) < len(top_users_raw):
            missing_user_ids = [user_id for user_id, _ in top_users_raw if str(user_id) not in user_mappings]
            
            if missing_user_ids:
                placeholders = ', '.join(['?'] * len(missing_user_ids))
                async with conn.execute(f'''
                    SELECT DISTINCT user_id, message_content
                    FROM messages
                    WHERE user_id IN ({placeholders})
                ''', missing_user_ids) as cursor:
                    user_info = await cursor.fetchall()
                    
                    # Update top_users with usernames from the database
                    for user_id, message_content in user_info:
                        username = message_content.split()[0]  # Extract the first word as username
                        for i, (uid, count) in enumerate(top_users_raw):
                            if uid == user_id:
                                top_users[i] = (username, count)
        
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

async def get_chart_data():
    try:
        conn = await get_db_connection()

        # Messages Over Time
        async with conn.execute('''
            SELECT DATE(timestamp) as date, COUNT(*) as message_count
            FROM messages
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp)
        ''') as cursor:
            messages_over_time = await cursor.fetchall()
        
        messages_data = [{'date': row[0], 'message_count': row[1]} for row in messages_over_time]

        # User Activity Over Time
        async with conn.execute('''
            SELECT DATE(timestamp) as date, COUNT(DISTINCT user_id) as active_users
            FROM messages
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp)
        ''') as cursor:
            user_activity_over_time = await cursor.fetchall()

        user_activity_data = [{'date': row[0], 'active_users': row[1]} for row in user_activity_over_time]

        # User Activity by Time
        async with conn.execute('''
            SELECT STRFTIME('%H', timestamp) as hour, COUNT(*) as message_count
            FROM messages
            GROUP BY hour
            ORDER BY hour
        ''') as cursor:
            user_activity_by_time = await cursor.fetchall()

        user_activity_by_time_data = [{'hour': row[0], 'message_count': row[1]} for row in user_activity_by_time]

        await conn.close()

        return {
            'messages_over_time': messages_data,
            'user_activity_over_time': user_activity_data,
            'user_activity_by_time': user_activity_by_time_data
        }
    except Exception as e:
        print(f"Error accessing database: {e}")
        return {
            'messages_over_time': [],
            'user_activity_over_time': [],
            'user_activity_by_time': [],
            'error': str(e)
        }

@app.route('/api/chart_data')
async def chart_data():
    return jsonify(await get_chart_data())

@app.route('/api/test_data')
async def test_data():
    try:
        conn = await get_db_connection()
        async with conn.execute("SELECT * FROM messages LIMIT 10;") as cursor:
            rows = await cursor.fetchall()
        await conn.close()
        
        # Convert rows to a list of dictionaries
        column_names = [description[0] for description in cursor.description]
        data = [dict(zip(column_names, row)) for row in rows]
        
        return jsonify(data)
    except Exception as e:
        print(f"Error accessing database: {e}")
        return jsonify({'error': str(e)})

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
    app.run(host='0.0.0.0', debug=True, port=5000)
