import os, threading, asyncio, json
from flask import Flask, render_template, request, jsonify, abort, session
import jwt
from datetime import datetime, timedelta
from chatbot.database import auth_user, init_db
from chatbot.mcp.client_sse import InteractiveBankingAssistant
from preference_analyzer import PreferenceAnalyzer

# Initialize Flask app pointing to local templates/ and static/
app = Flask(__name__, template_folder="templates", static_folder="static")

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Instantiate & initialize the agent at startup
assistant = InteractiveBankingAssistant()

# Instantiate preference analyzer
preference_analyzer = PreferenceAnalyzer()

# Spin up a dedicated loop in a background thread
background_loop = asyncio.new_event_loop()
def _start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(assistant.initialize_session())
    loop.run_forever()

t = threading.Thread(target=_start_background_loop, args=(background_loop,), daemon=True)
t.start()

# Helpers for JWT
def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = payload.get("sub")
        if not user:
            abort(401, "Invalid token payload")
        return user
    except jwt.ExpiredSignatureError:
        abort(401, "Token has expired")
    except jwt.InvalidTokenError:
        abort(401, "Invalid token")

# Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("chat.html")

@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        abort(400, 'Missing "username" or "password"')

    # Validate against real database
    if not auth_user(username, password):
        return jsonify({"status": "fail"}), 401

    token = create_access_token(username)
    return jsonify({"status": "success", "access_token": token, "token_type": "bearer"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    import time
    import sqlite3
    
    # Mesurer le temps de début
    start_time = time.time()
    
    # Auth as before
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"reply": "🔒 Please login to continue."}), 401
    token = auth_header.split(" ", 1)[1]
    user = verify_access_token(token)

    # Grab the incoming message
    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify({"reply": "💡 I didn't get any text."}), 400

    # Variables pour la base de données
    conversation_id = None
    intent_detected = None
    confidence_score = 0.0
    bot_response = ""

    try:
        # 🆕 ANALYSER LES PRÉFÉRENCES AVANT DE RÉPONDRE
        detected_prefs = preference_analyzer.analyze_message(user, msg)
        if detected_prefs:
            print(f"🔍 Préférences détectées pour {user}: {detected_prefs}")
            # Vous pourriez extraire l'intent principal ici si votre analyzer le fournit
            if detected_prefs:
                # Prendre la première préférence comme intent principal
                first_pref = next(iter(detected_prefs.items()))
                intent_detected = f"{first_pref[0]}:{first_pref[1]}"
                confidence_score = 0.7  # ou une valeur basée sur votre logique
        
    except Exception as e:
        print(f"⚠️  Erreur analyse préférences: {e}")

    try:
        # Schedule your send_message onto the background loop
        future = asyncio.run_coroutine_threadsafe(
            assistant.send_message(msg),
            background_loop
        )
        result = future.result(timeout=30)   # wait up to 30s
        
        # Handle the two possible return types
        if isinstance(result, str):
            bot_response = result
        elif isinstance(result, dict) and "error" in result:
            bot_response = result["error"]
        else:
            bot_response = json.dumps(result, indent=2)
            
    except Exception as e:
        bot_response = f"❌ Internal error: {e}"
        
    # Calculer le temps de réponse
    response_time = time.time() - start_time
    
    # 🆕 SAUVEGARDER DANS LA BASE DE DONNÉES
    try:
        conn = sqlite3.connect('General_DB.db')
        cursor = conn.cursor()
        
        # D'abord, obtenir ou créer une conversation_id pour cet utilisateur
        # (vous pourriez vouloir une logique plus sophistiquée ici)
        cursor.execute("""
            SELECT id FROM chat_conversations 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (user,))
        
        conv_result = cursor.fetchone()
        if conv_result:
            conversation_id = conv_result[0]
        else:
            # Créer une nouvelle conversation si nécessaire
            cursor.execute("""
                INSERT INTO chat_conversations (user_id, created_at)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (user,))
            conversation_id = cursor.lastrowid
        
        # Insérer le message dans chat_messages
        cursor.execute("""
            INSERT INTO chat_messages (
                conversation_id, 
                user_message, 
                bot_response, 
                intent_detected, 
                confidence_score, 
                response_time,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            conversation_id,
            msg,
            bot_response,
            intent_detected,
            confidence_score,
            response_time
        ))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Message sauvegardé - User: {user}, Intent: {intent_detected}, Time: {response_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde DB: {e}")
        # Ne pas faire échouer la requête si la DB échoue
    
    # Retourner la réponse comme avant
    if isinstance(result, str):
        return jsonify({"reply": result})
    elif isinstance(result, dict) and "error" in result:
        return jsonify({"reply": result["error"]})
    else:
        return jsonify({"reply": json.dumps(result, indent=2)})

@app.route('/api/user/preferences/test', methods=['POST'])
def add_test_preferences():
    try:
        import sqlite3
        
        conn = sqlite3.connect('General_DB.db')
        cursor = conn.cursor()
        
        # Créer la table si elle n'existe pas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, preference_key, preference_value)
            )
        ''')
        
        # Ajouter des préférences de test basées sur des sujets variés
        test_prefs = [
            # Technologie
            ("test_user", "technologie", "informatique", 0.7),
            ("test_user", "technologie", "smartphones", 0.6),
            ("test_user", "programmation", "python", 0.8),
            ("test_user", "programmation", "web_dev", 0.5),
            
            # Bancaire
            ("test_user", "service_bancaire", "gestion_compte", 0.9),
            ("test_user", "service_bancaire", "carte_bancaire", 0.8),
            ("test_user", "transaction", "virement", 0.7),
            
            # Lifestyle
            ("test_user", "lifestyle", "cuisine", 0.6),
            ("test_user", "lifestyle", "sport", 0.5),
            ("test_user", "divertissement", "cinema", 0.4),
            
            # Voyage
            ("test_user", "voyage", "voyage_loisir", 0.3),
            ("test_user", "informations", "meteo", 0.5),
        ]
        
        for user_id, key, value, confidence in test_prefs:
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (user_id, preference_key, preference_value, confidence_score)
                VALUES (?, ?, ?, ?)
            """, (user_id, key, value, confidence))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Préférences de test ajoutées (sujets variés)',
            'preferences_added': len(test_prefs)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/user/preferences')
def get_user_preferences():
    user_id = "test_user"
    
    try:
        import sqlite3
        
        conn = sqlite3.connect('General_DB.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Vérifier d'abord quelles colonnes existent
        cursor.execute("PRAGMA table_info(user_preferences)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Construire la requête en fonction des colonnes disponibles
        if 'last_updated' in column_names:
            query = """
                SELECT preference_key, preference_value, confidence_score, last_updated
                FROM user_preferences WHERE user_id = ?
                ORDER BY confidence_score DESC
            """
        else:
            query = """
                SELECT preference_key, preference_value, confidence_score, 
                       'N/A' as last_updated
                FROM user_preferences WHERE user_id = ?
                ORDER BY confidence_score DESC
            """
        
        cursor.execute(query, (user_id,))
        prefs = cursor.fetchall()
        
        preferences_list = []
        for pref in prefs:
            preferences_list.append({
                'key': pref['preference_key'],
                'value': pref['preference_value'],
                'confidence': float(pref['confidence_score']) if pref['confidence_score'] else 0.0,
                'updated': pref['last_updated'] if 'last_updated' in column_names else 'N/A'
            })
        
        conn.close()
        
        return jsonify({
            'user_id': user_id,
            'preferences': preferences_list,
            'total_preferences': len(preferences_list),
            'status': 'success',
            'available_columns': column_names
        })
        
    except Exception as e:
        return jsonify({
            'error': f"Erreur: {str(e)}",
            'user_id': user_id,
            'preferences': [],
            'total_preferences': 0,
            'status': 'error'
        })

@app.route('/api/user/preferences/live')
def get_live_preferences():
    """Voir les préférences basées sur les vraies conversations"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Non autorisé"}), 401
    
    token = auth_header.split(" ", 1)[1]
    user = verify_access_token(token)
    
    try:
        # Récupérer les préférences de cet utilisateur
        top_prefs = preference_analyzer.get_top_preferences(user, limit=20)
        categories = preference_analyzer.get_preferences_by_category(user)
        
        return jsonify({
            'user_id': user,
            'top_preferences': top_prefs,
            'categories': categories,
            'total_preferences': len(top_prefs),
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'user_id': user,
            'preferences': [],
            'status': 'error'
        })

@app.route('/api/user/preferences/reset', methods=['POST'])
def reset_user_preferences():
    """Réinitialiser les préférences d'un utilisateur pour les tests"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Non autorisé"}), 401
    
    token = auth_header.split(" ", 1)[1]
    user = verify_access_token(token)
    
    try:
        import sqlite3
        
        conn = sqlite3.connect('General_DB.db')
        cursor = conn.cursor()
        
        # Supprimer toutes les préférences de cet utilisateur
        cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Préférences réinitialisées pour {user}',
            'deleted_preferences': deleted_count
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/debug/preferences-stats')
def get_preferences_stats():
    """Statistiques générales des préférences (pour debug)"""
    try:
        import sqlite3
        
        conn = sqlite3.connect('General_DB.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Stats générales
        cursor.execute("SELECT COUNT(*) as total FROM user_preferences")
        total_prefs = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) as users FROM user_preferences")
        total_users = cursor.fetchone()['users']
        
        # Top catégories
        cursor.execute("""
            SELECT preference_key, COUNT(*) as count 
            FROM user_preferences 
            GROUP BY preference_key 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_categories = [dict(row) for row in cursor.fetchall()]
        
        # Top sous-catégories
        cursor.execute("""
            SELECT preference_value, COUNT(*) as count, AVG(confidence_score) as avg_confidence
            FROM user_preferences 
            GROUP BY preference_value 
            ORDER BY count DESC 
            LIMIT 15
        """)
        top_subcategories = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total_preferences': total_prefs,
            'total_users': total_users,
            'top_categories': top_categories,
            'top_subcategories': top_subcategories,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        })
        
if __name__ == "__main__":
    init_db()
    # Turn off the reloader
    app.run(host="0.0.0.0", port=3000, debug=True, use_reloader=False)