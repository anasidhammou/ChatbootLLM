import sqlite3
import re
from collections import Counter
from datetime import datetime

class PreferenceAnalyzer:
    def __init__(self, db_path='General_DB.db'):
        self.db_path = db_path
        
        # Mots-clés UNIVERSELS basés sur ce que les gens demandent vraiment
        self.keyword_preferences = {
            # ===== SERVICES BANCAIRES =====
            'compte': ('service_bancaire', 'gestion_compte', 0.3),
            'accounts': ('service_bancaire', 'gestion_compte', 0.3),
            'transfer': ('service_bancaire', 'gestion_compte', 0.3),
            'transactions': ('service_bancaire', 'gestion_compte', 0.3),
            'solde': ('service_bancaire', 'consultation_solde', 0.4),
            'carte': ('service_bancaire', 'carte_bancaire', 0.4),
            'virement': ('transaction', 'virement', 0.5),
            'crédit': ('service_bancaire', 'credit', 0.4),
            'prêt': ('service_bancaire', 'credit', 0.4),
            'épargne': ('service_bancaire', 'epargne', 0.3),
            'assurance': ('service_bancaire', 'assurance', 0.3),
            'investir': ('finance', 'investissement', 0.3),
            'bourse': ('finance', 'investissement_bourse', 0.3),
            'iban': ('service_bancaire', 'gestion_compte', 0.3),
            'rib': ('service_bancaire', 'gestion_compte', 0.3),
            'plafond': ('service_bancaire', 'carte_bancaire', 0.3),
            'cashback': ('service_bancaire', 'avantages', 0.3),
            'cryptomonnaie': ('finance', 'crypto', 0.5),
            'bitcoin': ('finance', 'crypto', 0.5),
            'ethereum': ('finance', 'crypto', 0.4),
            'wallet': ('finance', 'wallet', 0.4),
            'bancontact': ('service_bancaire', 'paiements', 0.3),
            
            # ===== TECHNOLOGIE (très demandé) =====
            'ordinateur': ('technologie', 'informatique', 0.3),
            'pc': ('technologie', 'informatique', 0.3),
            'laptop': ('technologie', 'informatique', 0.3),
            'smartphone': ('technologie', 'mobile', 0.3),
            'téléphone': ('technologie', 'mobile', 0.3),
            'iphone': ('technologie', 'mobile', 0.3),
            'android': ('technologie', 'mobile', 0.3),
            'application': ('technologie', 'applications', 0.3),
            'app': ('technologie', 'applications', 0.3),
            'internet': ('technologie', 'internet', 0.3),
            'wifi': ('technologie', 'internet', 0.3),
            'logiciel': ('technologie', 'logiciels', 0.3),
            'windows': ('technologie', 'systemes', 0.3),
            'mac': ('technologie', 'systemes', 0.3),
            'linux': ('technologie', 'systemes', 0.2),
            'ia': ('technologie', 'intelligence_artificielle', 0.5),
            'ai': ('technologie', 'intelligence_artificielle', 0.5),
            'chatgpt': ('technologie', 'ia', 0.5),
            'openai': ('technologie', 'ia', 0.4),
            'ollama': ('technologie', 'ia', 0.3),
            'api': ('technologie', 'api', 0.3),
            'saas': ('technologie', 'cloud', 0.3),
            'cloud': ('technologie', 'cloud', 0.4),
            'aws': ('technologie', 'cloud', 0.3),
            'azure': ('technologie', 'cloud', 0.3),
            'gcp': ('technologie', 'cloud', 0.3),
            
            # ===== PROGRAMMATION =====
            'python': ('programmation', 'python', 0.4),
            'javascript': ('programmation', 'javascript', 0.4),
            'java': ('programmation', 'java', 0.3),
            'html': ('programmation', 'web_dev', 0.3),
            'css': ('programmation', 'web_dev', 0.3),
            'react': ('programmation', 'frameworks', 0.3),
            'angular': ('programmation', 'frameworks', 0.3),
            'nodejs': ('programmation', 'backend', 0.3),
            'base de données': ('programmation', 'database', 0.3),
            'sql': ('programmation', 'database', 0.3),
            'mysql': ('programmation', 'database', 0.3),
            'mongodb': ('programmation', 'database', 0.2),
            'flutter': ('programmation', 'frameworks', 0.3),
            'django': ('programmation', 'frameworks', 0.3),
            'fastapi': ('programmation', 'backend', 0.3),
            'spring': ('programmation', 'backend', 0.3),
            'kotlin': ('programmation', 'mobile_dev', 0.3),
            'swift': ('programmation', 'mobile_dev', 0.3),
            'graphql': ('programmation', 'api', 0.3),
            'docker': ('programmation', 'devops', 0.3),
            'kubernetes': ('programmation', 'devops', 0.3),
            
            # ===== SANTÉ (questions fréquentes) =====
            'médecin': ('sante', 'medical', 0.3),
            'docteur': ('sante', 'medical', 0.3),
            'hôpital': ('sante', 'medical', 0.3),
            'médicament': ('sante', 'medicaments', 0.3),
            'symptôme': ('sante', 'symptomes', 0.4),
            'maladie': ('sante', 'maladies', 0.3),
            'douleur': ('sante', 'symptomes', 0.3),
            'fièvre': ('sante', 'symptomes', 0.3),
            'pharmacie': ('sante', 'pharmacie', 0.3),
            'rendez-vous': ('sante', 'rdv_medical', 0.3),
            'covid': ('sante', 'epidemies', 0.5),
            'vaccin': ('sante', 'vaccination', 0.4),
            'psy': ('sante', 'psychologie', 0.3),
            'psychologue': ('sante', 'psychologie', 0.3),
            'kiné': ('sante', 'kinesitherapie', 0.3),
            'diabète': ('sante', 'maladies', 0.4),
            'cholestérol': ('sante', 'maladies', 0.3),
            'allergie': ('sante', 'allergies', 0.3),
            
            # ===== VOYAGE (très populaire) =====
            'voyage': ('voyage', 'voyage_general', 0.4),
            'voyager': ('voyager', 'voyage_general', 0.4),
            'plan': ('plan', 'voyage_general', 0.4),
            'vacances': ('voyage', 'voyage_loisir', 0.4),
            'avion': ('voyage', 'transport_aerien', 0.3),
            'vol': ('voyage', 'transport_aerien', 0.3),
            'hôtel': ('voyage', 'hebergement', 0.3),
            'réservation': ('voyage', 'reservation', 0.3),
            'train': ('voyage', 'transport_terrestre', 0.3),
            'voiture': ('voyage', 'transport_terrestre', 0.3),
            'location': ('voyage', 'location_vehicule', 0.2),
            'visa': ('voyage', 'formalites', 0.3),
            'passeport': ('voyage', 'formalites', 0.3),
            'airbnb': ('voyage', 'hebergement', 0.3),
            'booking': ('voyage', 'reservation', 0.3),
            'croisière': ('voyage', 'loisir', 0.3),
            'camping': ('voyage', 'hebergement', 0.3),
            'safari': ('voyage', 'loisir', 0.3),
            'roadtrip': ('voyage', 'voyage_loisir', 0.3),
            
            # ===== ÉDUCATION =====
            'école': ('education', 'scolarite', 0.3),
            'université': ('education', 'universite', 0.3),
            'étudier': ('education', 'etudes', 0.3),
            'cours': ('education', 'cours', 0.3),
            'formation': ('education', 'formation', 0.3),
            'diplôme': ('education', 'diplomes', 0.3),
            'examen': ('education', 'examens', 0.3),
            'apprentissage': ('education', 'apprentissage', 0.3),
            'certification': ('education', 'formation', 0.3),
            'mooc': ('education', 'formation_en_ligne', 0.3),
            'udemy': ('education', 'formation_en_ligne', 0.3),
            'coursera': ('education', 'formation_en_ligne', 0.3),
            'linkedin learning': ('education', 'formation_en_ligne', 0.3),
            
            # ===== TRAVAIL / EMPLOI =====
            'travail': ('emploi', 'travail_general', 0.4),
            'emploi': ('emploi', 'recherche_emploi', 0.4),
            'job': ('emploi', 'recherche_emploi', 0.4),
            'cv': ('emploi', 'cv', 0.4),
            'entretien': ('emploi', 'entretien_embauche', 0.4),
            'salaire': ('emploi', 'salaire', 0.4),
            'entreprise': ('emploi', 'entreprise', 0.3),
            'carrière': ('emploi', 'carriere', 0.3),
            'stage': ('emploi', 'stage', 0.3),
            'freelance': ('emploi', 'freelance', 0.2),
            'startup': ('emploi', 'entrepreneuriat', 0.4),
            'business': ('emploi', 'entrepreneuriat', 0.4),
            'investisseur': ('emploi', 'entrepreneuriat', 0.3),
            'freelancer': ('emploi', 'freelance', 0.3),
            'remote': ('emploi', 'teletravail', 0.4),
            
            # ===== MAISON / IMMOBILIER =====
            'maison': ('immobilier', 'achat_maison', 0.3),
            'appartement': ('immobilier', 'achat_appartement', 0.3),
            'location': ('immobilier', 'location', 0.3),
            'loyer': ('immobilier', 'location', 0.3),
            'hypothèque': ('immobilier', 'financement', 0.3),
            'rénovation': ('immobilier', 'travaux', 0.3),
            'travaux': ('immobilier', 'travaux', 0.3),
            'déménagement': ('immobilier', 'demenagement', 0.3),
            'domotique': ('immobilier', 'domotique', 0.3),
            'smart home': ('immobilier', 'domotique', 0.3),
            'alarme': ('immobilier', 'securite', 0.3),
            'climatisation': ('immobilier', 'equipement', 0.3),
            'chauffage': ('immobilier', 'equipement', 0.3),
            
            # ===== CUISINE / ALIMENTATION =====
            'cuisine': ('lifestyle', 'cuisine', 0.3),
            'préparer': ('lifestyle', 'cuisine', 0.3),
            'recette': ('lifestyle', 'recettes', 0.4),
            'restaurant': ('lifestyle', 'restaurants', 0.3),
            'manger': ('lifestyle', 'alimentation', 0.2),
            'nourriture': ('lifestyle', 'alimentation', 0.2),
            'régime': ('lifestyle', 'regime', 0.3),
            'nutrition': ('lifestyle', 'nutrition', 0.3),
            
            # ===== SPORT / FITNESS =====
            'sport': ('lifestyle', 'sport', 0.3),
            'fitness': ('lifestyle', 'fitness', 0.3),
            'gym': ('lifestyle', 'fitness', 0.3),
            'musculation': ('lifestyle', 'musculation', 0.3),
            'course': ('lifestyle', 'running', 0.3),
            'yoga': ('lifestyle', 'yoga', 0.3),
            'football': ('lifestyle', 'football', 0.2),
            'tennis': ('lifestyle', 'tennis', 0.2),
            'méditation': ('lifestyle', 'bien_etre', 0.3),
            'coaching': ('lifestyle', 'developpement_personnel', 0.3),
            'voyance': ('lifestyle', 'voyance', 0.2),
            'mode': ('lifestyle', 'mode', 0.3),
            'maquillage': ('lifestyle', 'beaute', 0.3),
            'soins': ('lifestyle', 'beaute', 0.3),
            
            # ===== DIVERTISSEMENT =====
            'film': ('divertissement', 'cinema', 0.3),
            'cinéma': ('divertissement', 'cinema', 0.3),
            'série': ('divertissement', 'series', 0.3),
            'netflix': ('divertissement', 'streaming', 0.3),
            'musique': ('divertissement', 'musique', 0.3),
            'concert': ('divertissement', 'concerts', 0.3),
            'livre': ('divertissement', 'lecture', 0.3),
            'jeu': ('divertissement', 'jeux', 0.3),
            'gaming': ('divertissement', 'jeux_video', 0.3),
            'playstation': ('divertissement', 'jeux_video', 0.4),
            'ps5': ('divertissement', 'jeux_video', 0.4),
            'xbox': ('divertissement', 'jeux_video', 0.4),
            'nintendo': ('divertissement', 'jeux_video', 0.4),
            'steam': ('divertissement', 'jeux_video', 0.3),
            'twitch': ('divertissement', 'streaming', 0.3),
            
            # ===== MÉTÉO (très demandé) =====
            'météo': ('informations', 'meteo', 0.5),
            'temps': ('informations', 'meteo', 0.4),
            'pluie': ('informations', 'meteo', 0.3),
            'soleil': ('informations', 'meteo', 0.2),
            'température': ('informations', 'meteo', 0.3),
            
            # ===== ACTUALITÉS =====
            'actualités': ('informations', 'actualites', 0.3),
            'news': ('informations', 'actualites', 0.3),
            'politique': ('informations', 'politique', 0.2),
            'économie': ('informations', 'economie', 0.2),
            
            # ===== SHOPPING =====
            'acheter': ('commerce', 'shopping', 0.3),
            'achat': ('commerce', 'shopping', 0.3),
            'magasin': ('commerce', 'magasins', 0.3),
            'prix': ('commerce', 'prix', 0.4),
            'promotion': ('commerce', 'promotions', 0.3),
            'soldes': ('commerce', 'soldes', 0.3),
            'amazon': ('commerce', 'e_commerce', 0.2),
            
            # ===== TRANSPORT =====
            'transport': ('transport', 'transport_general', 0.3),
            'métro': ('transport', 'transport_public', 0.3),
            'bus': ('transport', 'transport_public', 0.3),
            'uber': ('transport', 'vtc', 0.3),
            'taxi': ('transport', 'taxi', 0.3),
            'vélo': ('transport', 'velo', 0.2),
            'trottinette': ('transport', 'trottinette', 0.2),
            
            # ===== AIDE / SUPPORT =====
            'aide': ('support', 'aide_generale', 0.3),
            'problème': ('support', 'problemes', 0.4),
            'bug': ('support', 'problemes_technique', 0.3),
            'erreur': ('support', 'problemes_technique', 0.3),
            'comment': ('support', 'guide', 0.2),
            'pourquoi': ('support', 'explications', 0.2),

            # ===== Réseaux sociaux =====
            'facebook': ('reseaux_sociaux', 'reseaux', 0.4),
            'instagram': ('reseaux_sociaux', 'reseaux', 0.4),
            'tiktok': ('reseaux_sociaux', 'reseaux', 0.4),
            'twitter': ('reseaux_sociaux', 'reseaux', 0.3),
            'threads': ('reseaux_sociaux', 'reseaux', 0.3),
            'snapchat': ('reseaux_sociaux', 'reseaux', 0.3),
            'linkedin': ('reseaux_sociaux', 'reseaux', 0.3),
        }
    
    def analyze_message(self, user_id, message):
        """
        Analyse un message utilisateur et détecte les préférences
        """
        message_lower = message.lower()
        detected_preferences = []
        
        # Analyser chaque mot-clé dans le message
        for keyword, (category, subcategory, weight) in self.keyword_preferences.items():
            # Recherche plus précise avec des mots entiers
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, message_lower):
                detected_preferences.append((category, subcategory, weight))
        
        # Sauvegarder les préférences détectées
        if detected_preferences:
            self._update_preferences(user_id, detected_preferences)
            print(f"✅ Préférences détectées pour {user_id}: {detected_preferences}")
        
        return detected_preferences
    
    def _update_preferences(self, user_id, preferences):
        """
        Met à jour la base de données avec les nouvelles préférences
        """
        try:
            conn = sqlite3.connect(self.db_path)
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
            
            for category, subcategory, weight in preferences:
                # Vérifier si la préférence existe déjà
                cursor.execute("""
                    SELECT confidence_score FROM user_preferences
                    WHERE user_id = ? AND preference_key = ? AND preference_value = ?
                """, (user_id, category, subcategory))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Augmenter le score de confiance
                    new_score = min(1.0, existing[0] + weight)
                    cursor.execute("""
                        UPDATE user_preferences 
                        SET confidence_score = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND preference_key = ? AND preference_value = ?
                    """, (new_score, user_id, category, subcategory))
                else:
                    # Créer une nouvelle préférence
                    cursor.execute("""
                        INSERT INTO user_preferences 
                        (user_id, preference_key, preference_value, confidence_score)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, category, subcategory, weight))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour des préférences: {e}")
    
    def get_top_preferences(self, user_id, limit=10):
        """
        Récupère les préférences principales d'un utilisateur
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT preference_key, preference_value, confidence_score, last_updated
                FROM user_preferences
                WHERE user_id = ?
                ORDER BY confidence_score DESC
                LIMIT ?
            """, (user_id, limit))
            
            preferences = cursor.fetchall()
            conn.close()
            
            return [dict(pref) for pref in preferences]
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des préférences: {e}")
            return []
    
    def get_preferences_by_category(self, user_id):
        """
        Récupère les préférences organisées par catégorie
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT preference_key, preference_value, confidence_score
                FROM user_preferences
                WHERE user_id = ?
                ORDER BY preference_key, confidence_score DESC
            """, (user_id,))
            
            preferences = cursor.fetchall()
            conn.close()
            
            # Organiser par catégorie
            categories = {}
            for pref in preferences:
                category = pref['preference_key']
                if category not in categories:
                    categories[category] = []
                categories[category].append({
                    'value': pref['preference_value'],
                    'confidence': float(pref['confidence_score'])
                })
            
            return categories
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des préférences par catégorie: {e}")
            return {}