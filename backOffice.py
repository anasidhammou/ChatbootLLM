from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
import json
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class AdminUser(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return AdminUser(user_data[0], user_data[1], user_data[2], user_data[4])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accès non autorisé', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ✅ AJOUT DE LA FONCTION MANQUANTE
def log_system_event(level, message, module=None, user_id=None):
    """Fonction pour enregistrer les événements système"""
    try:
        conn = sqlite3.connect('General_DB.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_logs (level, message, module, user_id)
            VALUES (?, ?, ?, ?)
        ''', (level, message, module, user_id))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du log: {e}")
        # Ne pas faire planter l'application si le logging échoue

# Initialisation des tables backoffice dans General_DB.db
def init_backoffice_tables():
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    # Vérifier et créer les tables backoffice si elles n'existent pas
    
    # Table des utilisateurs admin pour le backoffice
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'moderator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des conversations (intégration avec le chatbot existant)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des messages du chat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            user_message TEXT,
            bot_response TEXT,
            intent_detected TEXT,
            confidence_score REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_time REAL,
            FOREIGN KEY (conversation_id) REFERENCES chat_conversations (id)
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation 
        ON chat_messages(conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chat_conversations_user 
        ON chat_conversations(user_id)
    ''')
    
    # Table des analytics quotidiennes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE,
            total_conversations INTEGER DEFAULT 0,
            total_messages INTEGER DEFAULT 0,
            avg_response_time REAL DEFAULT 0,
            top_intents TEXT,
            user_satisfaction REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des configurations du bot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name TEXT UNIQUE,
            config_value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY (updated_by) REFERENCES admin_users (id)
        )
    ''')
    
    # Table des logs du système
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            module TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES admin_users (id)
        )
    ''')
    
    # Créer un utilisateur admin par défaut
    default_admin_hash = generate_password_hash('admin123')
    cursor.execute('''
        INSERT OR IGNORE INTO admin_users (username, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    ''', ('admin', 'admin@s2m.com', default_admin_hash, 'admin'))
    
    # Insérer quelques configurations par défaut
    default_configs = [
        ('max_response_time', '5.0', 'Temps de réponse maximum en secondes'),
        ('max_conversation_length', '50', 'Nombre maximum de messages par conversation'),
        ('enable_analytics', 'true', 'Activer la collecte d\'analytics'),
        ('bot_personality', 'professional', 'Personnalité du bot (professional/friendly/formal)'),
        ('default_language', 'fr', 'Langue par défaut du bot')
    ]
    
    for config_name, config_value, description in default_configs:
        cursor.execute('''
            INSERT OR IGNORE INTO bot_config (config_name, config_value, description, updated_by)
            VALUES (?, ?, ?, 1)
        ''', (config_name, config_value, description))
    
    conn.commit()
    conn.close()
    print("Tables backoffice initialisées dans General_DB.db")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('General_DB.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin_users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[3], password):
            user = AdminUser(user_data[0], user_data[1], user_data[2], user_data[4])
            login_user(user)
            
            # Log de connexion
            log_system_event('INFO', f'Connexion admin: {username}', 'auth', user_data[0])
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants invalides', 'error')
            log_system_event('WARNING', f'Tentative de connexion échouée: {username}', 'auth')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_system_event('INFO', f'Déconnexion admin: {current_user.username}', 'auth', current_user.id)
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    # Statistiques générales des conversations
    cursor.execute('SELECT COUNT(*) FROM chat_conversations')
    total_conversations = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM chat_messages')
    total_messages = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT AVG(response_time) FROM chat_messages WHERE response_time IS NOT NULL')
    avg_response_time_result = cursor.fetchone()[0]
    avg_response_time = avg_response_time_result if avg_response_time_result is not None else 0
    
    # Conversations récentes - utilisation des colonnes existantes
    cursor.execute('''
        SELECT id, user_id, created_at, updated_at
        FROM chat_conversations 
        ORDER BY updated_at DESC 
        LIMIT 10
    ''')
    recent_conversations = cursor.fetchall() or []
    
    # Intents les plus fréquents
    cursor.execute('''
        SELECT intent_detected, COUNT(*) as count 
        FROM chat_messages 
        WHERE intent_detected IS NOT NULL 
        GROUP BY intent_detected 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    top_intents = cursor.fetchall() or []
    
    # Messages par heure (dernières 24h) - utilisation de la colonne timestamp
    cursor.execute('''
        SELECT strftime('%H:00', timestamp) as hour, COUNT(*) as count
        FROM chat_messages 
        WHERE timestamp >= datetime('now', '-24 hours')
        GROUP BY strftime('%H', timestamp)
        ORDER BY hour
    ''')
    hourly_data = cursor.fetchall()
    
    # Convertir en format approprié pour le graphique avec gestion des valeurs None
    hourly_messages = []
    hourly_dict = {hour: count for hour, count in hourly_data if hour is not None and count is not None}
    
    for i in range(24):
        hour_key = f"{i:02d}:00"
        count_value = hourly_dict.get(hour_key, 0)
        # S'assurer que count_value n'est pas None
        if count_value is None:
            count_value = 0
        
        hourly_messages.append({
            'hour': hour_key,
            'count': int(count_value)  # S'assurer que c'est un entier
        })
    
    # Statistiques des comptes bancaires (intégration avec le système existant)
    # Vérifier si la table accounts existe d'abord
    try:
        cursor.execute('SELECT COUNT(*) FROM accounts')
        total_accounts = cursor.fetchone()[0] or 0
    except sqlite3.OperationalError:
        total_accounts = 0
    
    try:
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE timestamp >= date("now", "-30 days")')
        recent_transactions = cursor.fetchone()[0] or 0
    except sqlite3.OperationalError:
        recent_transactions = 0
    
    # Calculer le nombre de messages par conversation (remplacer message_count)
    cursor.execute('''
        SELECT conversation_id, COUNT(*) as message_count
        FROM chat_messages 
        GROUP BY conversation_id
    ''')
    conversation_message_counts = dict(cursor.fetchall())
    
    conn.close()
    
    stats = {
        'total_conversations': int(total_conversations),
        'total_messages': int(total_messages),
        'avg_response_time': round(float(avg_response_time), 2),
        'recent_conversations': recent_conversations,
        'top_intents': top_intents,
        'total_accounts': int(total_accounts),
        'recent_transactions': int(recent_transactions),
        'hourly_messages': hourly_messages,
        'conversation_message_counts': conversation_message_counts
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/conversations')
@login_required
def conversations():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    # Récupérer les conversations avec le nombre de messages calculé
    cursor.execute('''
        SELECT 
            c.id, 
            c.user_id, 
            COUNT(m.id) as message_count,
            c.created_at, 
            c.updated_at
        FROM chat_conversations c
        LEFT JOIN chat_messages m ON c.id = m.conversation_id
        GROUP BY c.id, c.user_id, c.created_at, c.updated_at
        ORDER BY c.updated_at DESC 
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    conversations_data = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM chat_conversations')
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('conversations.html', 
                         conversations=conversations_data,
                         page=page,
                         per_page=per_page,
                         total=total)

@app.route('/conversation/<int:conv_id>')
@login_required
def conversation_detail(conv_id):
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    # Détails de la conversation
    cursor.execute('SELECT * FROM chat_conversations WHERE id = ?', (conv_id,))
    conversation = cursor.fetchone()
    
    # Messages de la conversation
    cursor.execute('''
        SELECT user_message, bot_response, intent_detected, confidence_score, timestamp, response_time
        FROM chat_messages 
        WHERE conversation_id = ? 
        ORDER BY timestamp ASC
    ''', (conv_id,))
    messages = cursor.fetchall()
    
    conn.close()
    
    if not conversation:
        flash('Conversation non trouvée', 'error')
        return redirect(url_for('conversations'))
    
    return render_template('conversation_detail.html', 
                         conversation=conversation, 
                         messages=messages)

@app.route('/analytics')
@login_required
def analytics():
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    # Données pour les graphiques (7 derniers jours)
    cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM chat_messages 
        WHERE timestamp >= date('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''')
    daily_messages = cursor.fetchall()
    
    # Compléter les jours manquants avec 0 messages
    daily_messages_complete = []
    daily_dict = {date: count for date, count in daily_messages if date is not None}
    
    for i in range(7):
        target_date = cursor.execute("SELECT date('now', '-{} days')".format(6-i)).fetchone()[0]
        count = daily_dict.get(target_date, 0)
        daily_messages_complete.append((target_date, count))
    
    # Analyse des intents
    cursor.execute('''
        SELECT intent_detected, COUNT(*) as count,
               ROUND(AVG(confidence_score), 3) as avg_confidence
        FROM chat_messages 
        WHERE intent_detected IS NOT NULL AND intent_detected != ''
        GROUP BY intent_detected
        ORDER BY count DESC
        LIMIT 10
    ''')
    intent_analysis = cursor.fetchall()
    
    # Temps de réponse par heure (dernières 24h)
    cursor.execute('''
        SELECT strftime('%H', timestamp) as hour,
               ROUND(AVG(response_time), 2) as avg_time,
               COUNT(*) as message_count
        FROM chat_messages 
        WHERE response_time IS NOT NULL
        AND timestamp >= datetime('now', '-24 hours')
        GROUP BY strftime('%H', timestamp)
        ORDER BY hour
    ''')
    hourly_performance_data = cursor.fetchall()
    
    # Compléter les heures manquantes avec des valeurs par défaut
    hourly_performance = []
    hourly_dict = {hour: (avg_time, msg_count) for hour, avg_time, msg_count in hourly_performance_data if hour is not None}
    
    for i in range(24):
        hour_key = f"{i:02d}"
        if hour_key in hourly_dict:
            avg_time, msg_count = hourly_dict[hour_key]
            hourly_performance.append((hour_key, avg_time or 0, msg_count or 0))
        else:
            hourly_performance.append((hour_key, 0, 0))
    
    # Statistiques générales des conversations
    cursor.execute('SELECT COUNT(*) FROM chat_conversations')
    total_conversations = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM chat_messages')
    total_messages = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT AVG(subquery.message_count) as avg_messages_per_conversation
        FROM (
            SELECT conversation_id, COUNT(*) as message_count
            FROM chat_messages
            GROUP BY conversation_id
        ) subquery
    ''')
    avg_messages_per_conv_result = cursor.fetchone()[0]
    avg_messages_per_conv = round(avg_messages_per_conv_result, 2) if avg_messages_per_conv_result else 0
    
    # Analyse des utilisateurs les plus actifs
    cursor.execute('''
        SELECT c.user_id, COUNT(DISTINCT c.id) as conversation_count, COUNT(m.id) as message_count
        FROM chat_conversations c
        LEFT JOIN chat_messages m ON c.id = m.conversation_id
        GROUP BY c.user_id
        ORDER BY message_count DESC
        LIMIT 10
    ''')
    top_users = cursor.fetchall()
    
    # Analyse temporelle des conversations (par jour de la semaine)
    cursor.execute('''
        SELECT 
            CASE strftime('%w', created_at)
                WHEN '0' THEN 'Dimanche'
                WHEN '1' THEN 'Lundi' 
                WHEN '2' THEN 'Mardi'
                WHEN '3' THEN 'Mercredi'
                WHEN '4' THEN 'Jeudi'
                WHEN '5' THEN 'Vendredi'
                WHEN '6' THEN 'Samedi'
            END as day_name,
            COUNT(*) as conversation_count
        FROM chat_conversations
        WHERE created_at >= datetime('now', '-30 days')
        GROUP BY strftime('%w', created_at)
        ORDER BY strftime('%w', created_at)
    ''')
    conversations_by_day = cursor.fetchall()
    
    # Analytics bancaires intégrées (optionnel)
    banking_activity = []
    try:
        cursor.execute('''
            SELECT DATE(date) as date, COUNT(*) as transaction_count, SUM(amount) as total_amount
            FROM transactions 
            WHERE date >= date('now', '-30 days')
            GROUP BY DATE(date)
            ORDER BY date
        ''')
        banking_activity = cursor.fetchall()
    except sqlite3.OperationalError:
        banking_activity = []
    
    # Métriques de qualité
    cursor.execute('''
        SELECT 
            COUNT(CASE WHEN confidence_score >= 0.8 THEN 1 END) as high_confidence,
            COUNT(CASE WHEN confidence_score BETWEEN 0.5 AND 0.79 THEN 1 END) as medium_confidence,
            COUNT(CASE WHEN confidence_score < 0.5 THEN 1 END) as low_confidence,
            COUNT(*) as total_with_confidence
        FROM chat_messages 
        WHERE confidence_score IS NOT NULL
        AND timestamp >= datetime('now', '-7 days')
    ''')
    confidence_metrics = cursor.fetchone()
    
    conn.close()
    
    analytics_data = {
        'daily_messages': daily_messages_complete,
        'intent_analysis': intent_analysis,
        'hourly_performance': hourly_performance,
        'banking_activity': banking_activity,
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'avg_messages_per_conv': avg_messages_per_conv,
        'top_users': top_users,
        'conversations_by_day': conversations_by_day,
        'confidence_metrics': {
            'high_confidence': confidence_metrics[0] or 0,
            'medium_confidence': confidence_metrics[1] or 0,
            'low_confidence': confidence_metrics[2] or 0,
            'total_with_confidence': confidence_metrics[3] or 0
        }
    }
    
    return render_template('analytics.html', **analytics_data)


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint pour récupérer les statistiques en temps réel"""
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    try:
        # Utilisateurs actifs (compte total des comptes bancaires)
        try:
            cursor.execute('SELECT COUNT(*) FROM accounts')
            active_users = cursor.fetchone()[0] or 0
        except sqlite3.OperationalError:
            active_users = 0
        
        # Messages par heure (dernières 24h) - format pour le graphique
        cursor.execute('''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM chat_messages 
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        ''')
        hourly_data = cursor.fetchall()
        
        # Convertir en format approprié pour le graphique
        hourly_messages = []
        hourly_dict = {hour: count for hour, count in hourly_data if hour is not None and count is not None}
        
        for i in range(24):
            hour_key = f"{i:02d}"
            count_value = hourly_dict.get(hour_key, 0)
            if count_value is None:
                count_value = 0
            hourly_messages.append(int(count_value))
        
        # Statistiques générales
        cursor.execute('SELECT COUNT(*) FROM chat_conversations')
        total_conversations = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM chat_messages')
        total_messages = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(response_time) FROM chat_messages WHERE response_time IS NOT NULL')
        avg_response_time_result = cursor.fetchone()[0]
        avg_response_time = round(float(avg_response_time_result), 2) if avg_response_time_result else 0
        
        # Intents les plus fréquents
        cursor.execute('''
            SELECT intent_detected, COUNT(*) as count 
            FROM chat_messages 
            WHERE intent_detected IS NOT NULL AND intent_detected != ''
            GROUP BY intent_detected 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        top_intents = cursor.fetchall() or []
        
        conn.close()
        
        return jsonify({
            'success': True,
            'active_users': active_users,
            'hourly_messages': hourly_messages,
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'avg_response_time': avg_response_time,
            'top_intents': top_intents,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        conn.close()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@app.route('/banking')
@login_required
def banking_overview():
    """Vue d'ensemble du système bancaire"""
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    try:
        # Statistiques des comptes par devise
        cursor.execute('''
            SELECT CurrencyCode, COUNT(*) as count, SUM(Balance) as total_balance
            FROM accounts
            GROUP BY CurrencyCode
        ''')
        account_stats = cursor.fetchall()
        
        # Transactions récentes avec infos comptes
        cursor.execute('''
           SELECT t.TransactionNumber, t.AccountNumber, t.OtherAccountNumber, 
                  t.TransactionDateTime, t.TransactionTypeCode, t.Amount, 
                  t.BalanceAfter,
                  a1.AccountName as account_name,
                  a2.AccountName as other_account_name
           FROM Transactions t
           LEFT JOIN Accounts a1 ON t.AccountNumber = a1.AccountNumber
           LEFT JOIN Accounts a2 ON t.OtherAccountNumber = a2.AccountNumber
           ORDER BY t.TransactionDateTime DESC
           LIMIT 20
        ''')
        recent_transactions = cursor.fetchall()
        
        # Activité journalière des transactions (sur 30 jours)
        cursor.execute('''
           SELECT DATE(TransactionDateTime) as date, 
                COUNT(*) as count, 
                SUM(ABS(Amount)) as volume
            FROM Transactions
            WHERE TransactionDateTime >= date('now', '-30 days')
            GROUP BY DATE(TransactionDateTime)
            ORDER BY date
        ''')
        daily_activity = cursor.fetchall()
        
    except sqlite3.OperationalError as e:
        print(f"Erreur de base de données: {e}")
        account_stats = []
        recent_transactions = []
        daily_activity = []
    
    conn.close()
    
    return render_template(
        'banking_overview.html',
        account_stats=account_stats,
        recent_transactions=recent_transactions,
        daily_activity=daily_activity
    )



@app.route('/configuration')
@login_required
@admin_required
def configuration():
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    # Récupérer toutes les configurations ordonnées par nom
    cursor.execute('''
        SELECT id, config_name, config_value, description, updated_at, updated_by 
        FROM bot_config 
        ORDER BY config_name
    ''')
    configs = cursor.fetchall()
    
    # Statistiques de configuration
    cursor.execute('SELECT COUNT(*) FROM bot_config')
    total_configs = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT COUNT(*) FROM bot_config 
        WHERE updated_at >= datetime('now', '-7 days')
    ''')
    recent_updates = cursor.fetchone()[0] or 0
    
    # Configurations récemment modifiées
    cursor.execute('''
        SELECT config_name, config_value, updated_at, updated_by
        FROM bot_config 
        ORDER BY updated_at DESC 
        LIMIT 5
    ''')
    recent_configs = cursor.fetchall()
    
    conn.close()
    
    return render_template('configuration.html', 
                         configs=configs,
                         total_configs=total_configs,
                         recent_updates=recent_updates,
                         recent_configs=recent_configs)

@app.route('/update_config', methods=['POST'])
@login_required
@admin_required
def update_config():
    config_name = request.form.get('config_name')
    config_value = request.form.get('config_value')
    description = request.form.get('description')
    
    if not config_name or not config_value:
        flash('Le nom et la valeur de configuration sont obligatoires', 'error')
        return redirect(url_for('configuration'))
    
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    try:
        # Vérifier si la configuration existe déjà
        cursor.execute('SELECT id FROM bot_config WHERE config_name = ?', (config_name,))
        existing_config = cursor.fetchone()
        
        if existing_config:
            # Mettre à jour la configuration existante
            cursor.execute('''
                UPDATE bot_config 
                SET config_value = ?, description = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                WHERE config_name = ?
            ''', (config_value, description, current_user.id, config_name))
            action = 'mise à jour'
        else:
            # Créer une nouvelle configuration
            cursor.execute('''
                INSERT INTO bot_config (config_name, config_value, description, updated_by)
                VALUES (?, ?, ?, ?)
            ''', (config_name, config_value, description, current_user.id))
            action = 'créée'
        
        conn.commit()
        
        # Log de l'action (si la fonction existe)
        try:
            log_system_event('INFO', f'Configuration {action}: {config_name} = {config_value}', 'config', current_user.id)
        except NameError:
            # Si log_system_event n'existe pas, ignorer
            pass
        
        flash(f'Configuration {action} avec succès', 'success')
    
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Erreur lors de la mise à jour: {str(e)}', 'error')
    
    finally:
        conn.close()
    
    return redirect(url_for('configuration'))

@app.route('/delete_config/<int:config_id>', methods=['POST'])
@login_required
@admin_required
def delete_config(config_id):
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    try:
        # Récupérer le nom de la configuration avant suppression
        cursor.execute('SELECT config_name FROM bot_config WHERE id = ?', (config_id,))
        config = cursor.fetchone()
        
        if not config:
            flash('Configuration non trouvée', 'error')
            return redirect(url_for('configuration'))
        
        config_name = config[0]
        
        # Supprimer la configuration
        cursor.execute('DELETE FROM bot_config WHERE id = ?', (config_id,))
        conn.commit()
        
        # Log de l'action (si la fonction existe)
        try:
            log_system_event('INFO', f'Configuration supprimée: {config_name}', 'config', current_user.id)
        except NameError:
            pass
        
        flash('Configuration supprimée avec succès', 'success')
    
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    
    finally:
        conn.close()
    
    return redirect(url_for('configuration'))

@app.route('/get_config/<config_name>')
@login_required
def get_config(config_name):
    """
    API endpoint pour récupérer une configuration spécifique
    Utile pour les requêtes AJAX
    """
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT config_name, config_value, description, updated_at 
        FROM bot_config 
        WHERE config_name = ?
    ''', (config_name,))
    
    config = cursor.fetchone()
    conn.close()
    
    if config:
        return {
            'success': True,
            'config_name': config[0],
            'config_value': config[1],
            'description': config[2],
            'updated_at': config[3]
        }
    else:
        return {'success': False, 'message': 'Configuration non trouvée'}, 404

@app.route('/export_config')
@login_required
@admin_required
def export_config():
    """
    Exporter toutes les configurations en JSON
    """
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT config_name, config_value, description, updated_at, updated_by
        FROM bot_config 
        ORDER BY config_name
    ''')
    
    configs = cursor.fetchall()
    conn.close()
    
    # Convertir en format JSON
    config_data = []
    for config in configs:
        config_data.append({
            'config_name': config[0],
            'config_value': config[1],
            'description': config[2],
            'updated_at': config[3],
            'updated_by': config[4]
        })
    
    from flask import jsonify
    response = jsonify(config_data)
    response.headers['Content-Disposition'] = 'attachment; filename=bot_config_export.json'
    response.headers['Content-Type'] = 'application/json'
    
    return response

def get_bot_config(config_name, default_value=None):
    """
    Fonction utilitaire pour récupérer une configuration
    Peut être utilisée dans d'autres parties de l'application
    """
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT config_value FROM bot_config WHERE config_name = ?', (config_name,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else default_value

def set_bot_config(config_name, config_value, description="", updated_by=None):
    """
    Fonction utilitaire pour définir une configuration programmatiquement
    """
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO bot_config (config_name, config_value, description, updated_by, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (config_name, config_value, description, updated_by))
        
        conn.commit()
        return True
    
    except sqlite3.Error:
        conn.rollback()
        return False
    
    finally:
        conn.close()

        

# Fonction utilitaire pour intégrer les logs du chatbot principal
@app.route('/api/log_chat_message', methods=['POST'])
def log_chat_message():
    """API pour enregistrer les messages du chatbot principal"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    conn = sqlite3.connect('General_DB.db')
    cursor = conn.cursor()
    
    # Créer ou récupérer la conversation
    conversation_id = data.get('conversation_id')
    if not conversation_id:
        # Créer nouvelle conversation
        cursor.execute('''
            INSERT INTO chat_conversations (user_id, session_id, message_count)
            VALUES (?, ?, 1)
        ''', (data.get('user_id', 'anonymous'), data.get('session_id', ''), 1))
        conversation_id = cursor.lastrowid
    else:
        # Mettre à jour conversation existante
        cursor.execute('''
            UPDATE chat_conversations 
            SET message_count = message_count + 1, last_activity = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (conversation_id,))
    
    # Enregistrer le message
    cursor.execute('''
        INSERT INTO chat_messages 
        (conversation_id, user_message, bot_response, intent_detected, confidence_score, response_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        conversation_id,
        data.get('user_message'),
        data.get('bot_response'),
        data.get('intent_detected'),
        data.get('confidence_score'),
        data.get('response_time')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'conversation_id': conversation_id})

if __name__ == '__main__':
    init_backoffice_tables()
    app.run(debug=True, port=5001)