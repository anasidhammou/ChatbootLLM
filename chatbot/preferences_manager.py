import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/General_DB.db")

def get_user_preferences(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT language, tone, favorite_products, last_intents
        FROM user_preferences
        WHERE user_id=?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "language": row[0],
            "tone": row[1],
            "favorite_products": json.loads(row[2]) if row[2] else [],
            "last_intents": json.loads(row[3]) if row[3] else []
        }
    else:
        return None

def set_user_preferences(user_id, preferences):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existing = get_user_preferences(user_id)
    if existing:
        cursor.execute("""
            UPDATE user_preferences
            SET language=?, tone=?, favorite_products=?, last_intents=?, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=?
        """, (
            preferences.get("language", existing["language"]),
            preferences.get("tone", existing["tone"]),
            json.dumps(preferences.get("favorite_products", existing["favorite_products"])),
            json.dumps(preferences.get("last_intents", existing["last_intents"])),
            user_id
        ))
    else:
        cursor.execute("""
            INSERT INTO user_preferences (user_id, language, tone, favorite_products, last_intents)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            preferences.get("language", "fr"),
            preferences.get("tone", "friendly"),
            json.dumps(preferences.get("favorite_products", [])),
            json.dumps(preferences.get("last_intents", []))
        ))
    conn.commit()
    conn.close()
