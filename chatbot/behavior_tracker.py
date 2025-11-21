"""
Système de suivi des comportements utilisateur pour l'intelligence des préférences
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from collections import defaultdict, Counter

class BehaviorTracker:
    def __init__(self, db_path: str = "General_DB.db"):
        self.db_path = db_path
        self.init_behavior_tables()
    
    def init_behavior_tables(self):
        """Initialise les tables de suivi des comportements"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table pour les logs de comportement
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_behavior_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                context TEXT,
                session_id TEXT
            )
        """)
        
        # Table pour les préférences déduites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                preference_category TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, preference_category, preference_key)
            )
        """)
        
        # Table pour les patterns de session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_session_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                start_time DATETIME,
                end_time DATETIME,
                total_actions INTEGER DEFAULT 0,
                primary_actions TEXT,
                session_duration INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_user_action(self, user_id: str, action_type: str, action_details: str = None, 
                       context: str = None, session_id: str = None):
        """Enregistre une action utilisateur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_behavior_log 
            (user_id, action_type, action_details, context, session_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action_type, action_details, context, session_id))
        
        conn.commit()
        conn.close()
    
    def analyze_transaction_patterns(self, user_id: str, days_back: int = 30) -> Dict:
        """Analyse les patterns de transactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT action_details, COUNT(*) as frequency,
                   strftime('%H', timestamp) as hour,
                   strftime('%w', timestamp) as weekday
            FROM user_behavior_log 
            WHERE user_id = ? AND action_type = 'transaction' 
            AND date(timestamp) >= ?
            GROUP BY action_details
        """, (user_id, since_date))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {}
        
        # Analyse des montants fréquents
        amounts = []
        time_patterns = defaultdict(int)
        weekday_patterns = defaultdict(int)
        
        for detail, freq, hour, weekday in results:
            try:
                detail_data = json.loads(detail) if detail else {}
                if 'amount' in detail_data:
                    amounts.extend([float(detail_data['amount'])] * freq)
                if hour:
                    time_patterns[int(hour)] += freq
                if weekday:
                    weekday_patterns[int(weekday)] += freq
            except:
                continue
        
        # Montants les plus fréquents
        amount_counter = Counter(amounts)
        frequent_amounts = dict(amount_counter.most_common(5))
        
        # Heures préférées
        preferred_hours = dict(sorted(time_patterns.items(), key=lambda x: x[1], reverse=True)[:3])
        
        # Jours préférés
        preferred_weekdays = dict(sorted(weekday_patterns.items(), key=lambda x: x[1], reverse=True)[:3])
        
        return {
            'frequent_amounts': frequent_amounts,
            'preferred_hours': preferred_hours,
            'preferred_weekdays': preferred_weekdays,
            'total_transactions': sum(amount_counter.values())
        }
    
    def analyze_account_preferences(self, user_id: str, days_back: int = 30) -> Dict:
        """Analyse les préférences de comptes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT action_details, COUNT(*) as frequency
            FROM user_behavior_log 
            WHERE user_id = ? AND action_type IN ('balance_check', 'transfer', 'transaction_history')
            AND date(timestamp) >= ?
        """, (user_id, since_date))
        
        results = cursor.fetchall()
        conn.close()
        
        account_usage = defaultdict(int)
        transfer_patterns = defaultdict(int)
        
        for detail, freq in results:
            try:
                detail_data = json.loads(detail) if detail else {}
                if 'account_type' in detail_data:
                    account_usage[detail_data['account_type']] += freq
                if 'from_account' in detail_data and 'to_account' in detail_data:
                    pattern = f"{detail_data['from_account']} -> {detail_data['to_account']}"
                    transfer_patterns[pattern] += freq
            except:
                continue
        
        return {
            'preferred_accounts': dict(sorted(account_usage.items(), key=lambda x: x[1], reverse=True)),
            'common_transfers': dict(sorted(transfer_patterns.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def analyze_communication_preferences(self, user_id: str, days_back: int = 30) -> Dict:
        """Analyse les préférences de communication"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT action_details, context, COUNT(*) as frequency
            FROM user_behavior_log 
            WHERE user_id = ? AND action_type = 'message'
            AND date(timestamp) >= ?
        """, (user_id, since_date))
        
        results = cursor.fetchall()
        conn.close()
        
        response_lengths = []
        question_types = defaultdict(int)
        interaction_times = []
        
        for detail, context, freq in results:
            try:
                detail_data = json.loads(detail) if detail else {}
                context_data = json.loads(context) if context else {}
                
                if 'response_length' in detail_data:
                    response_lengths.extend([detail_data['response_length']] * freq)
                
                if 'question_type' in context_data:
                    question_types[context_data['question_type']] += freq
                
                if 'interaction_duration' in context_data:
                    interaction_times.extend([context_data['interaction_duration']] * freq)
                    
            except:
                continue
        
        avg_response_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0
        preferred_question_types = dict(sorted(question_types.items(), key=lambda x: x[1], reverse=True)[:5])
        avg_interaction_time = sum(interaction_times) / len(interaction_times) if interaction_times else 0
        
        return {
            'preferred_response_length': 'detailed' if avg_response_length > 100 else 'concise',
            'common_question_types': preferred_question_types,
            'avg_interaction_time': avg_interaction_time,
            'communication_style': 'exploratory' if len(preferred_question_types) > 3 else 'focused'
        }
    
    def get_user_activity_pattern(self, user_id: str, days_back: int = 30) -> Dict:
        """Analyse le pattern d'activité général de l'utilisateur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour,
                   strftime('%w', timestamp) as weekday,
                   action_type,
                   COUNT(*) as frequency
            FROM user_behavior_log 
            WHERE user_id = ? AND date(timestamp) >= ?
            GROUP BY hour, weekday, action_type
            ORDER BY frequency DESC
        """, (user_id, since_date))
        
        results = cursor.fetchall()
        conn.close()
        
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        action_distribution = defaultdict(int)
        
        for hour, weekday, action_type, freq in results:
            if hour:
                hourly_activity[int(hour)] += freq
            if weekday:
                daily_activity[int(weekday)] += freq
            action_distribution[action_type] += freq
        
        # Déterminer les heures de pointe
        peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Déterminer les jours préférés
        preferred_days = sorted(daily_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Actions les plus fréquentes
        top_actions = sorted(action_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'peak_hours': dict(peak_hours),
            'preferred_days': dict(preferred_days),
            'top_actions': dict(top_actions),
            'total_activity': sum(action_distribution.values())
        }
    
    def update_user_preferences(self, user_id: str):
        """Met à jour les préférences utilisateur basées sur l'analyse des comportements"""
        transaction_patterns = self.analyze_transaction_patterns(user_id)
        account_preferences = self.analyze_account_preferences(user_id)
        communication_preferences = self.analyze_communication_preferences(user_id)
        activity_patterns = self.get_user_activity_pattern(user_id)
        
        preferences_to_update = []
        
        # Préférences de transaction
        if transaction_patterns.get('frequent_amounts'):
            most_frequent_amount = max(transaction_patterns['frequent_amounts'].items(), key=lambda x: x[1])
            preferences_to_update.append(('transaction', 'preferred_amount', str(most_frequent_amount[0]), 0.8))
        
        # Préférences de comptes
        if account_preferences.get('preferred_accounts'):
            preferred_account = max(account_preferences['preferred_accounts'].items(), key=lambda x: x[1])
            preferences_to_update.append(('account', 'primary_account', preferred_account[0], 0.9))
        
        # Préférences de communication
        if communication_preferences.get('preferred_response_length'):
            preferences_to_update.append(('communication', 'response_style', 
                                        communication_preferences['preferred_response_length'], 0.7))
        
        # Pattern d'activité
        if activity_patterns.get('peak_hours'):
            peak_hour = max(activity_patterns['peak_hours'].items(), key=lambda x: x[1])
            preferences_to_update.append(('activity', 'peak_hour', str(peak_hour[0]), 0.6))
        
        # Sauvegarder les préférences
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for category, key, value, confidence in preferences_to_update:
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (user_id, preference_category, preference_key, preference_value, confidence_score, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, category, key, value, confidence))
        
        conn.commit()
        conn.close()
        
        return len(preferences_to_update)