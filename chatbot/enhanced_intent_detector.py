"""
Détecteur d'intention amélioré avec intelligence utilisateur
Mise à jour du fichier intent_detector.py existant
"""
import re
from typing import Dict, List, Tuple
from .user_intelligence import UserIntelligence

class EnhancedIntentDetector:
    def __init__(self, db_path: str = "General_DB.db"):
        self.user_intelligence = UserIntelligence(db_path)
        
        # Patterns d'intention existants + nouveaux patterns personnalisés
        self.intent_patterns = {
            'balance_inquiry': {
                'keywords': ['balance', 'solde', 'combien', 'montant', 'disponible'],
                'patterns': [
                    r'(?:quel est|combien|montant).*(?:solde|balance)',
                    r'(?:solde|balance).*(?:compte|account)',
                    r'combien.*(?:argent|euros?|dollars?)'
                ],
                'confidence_boost': 0.1
            },
            'transfer': {
                'keywords': ['transfer', 'virer', 'envoyer', 'transférer', 'virement'],
                'patterns': [
                    r'(?:virer|transférer|envoyer).*(?:\d+|euros?|dollars?)',
                    r'(?:faire|effectuer).*(?:virement|transfer)',
                    r'(?:je veux|j\'aimerais).*(?:virer|transférer)'
                ],
                'confidence_boost': 0.15
            },
            'transaction_history': {
                'keywords': ['history', 'historique', 'transactions', 'opérations', 'mouvements'],
                'patterns': [
                    r'(?:voir|afficher|montrer).*(?:historique|history|transactions)',
                    r'(?:dernières?|récentes?).*(?:transactions|opérations)',
                    r'(?:historique|history).*(?:compte|account)'
                ],
                'confidence_boost': 0.1
            },
            'product_inquiry': {
                'keywords': ['produit', 'service', 'offre', 'carte', 'crédit', 'prêt'],
                'patterns': [
                    r'(?:quel|quelle).*(?:produit|service|offre)',
                    r'(?:carte|card).*(?:crédit|credit|bancaire)',
                    r'(?:prêt|loan|crédit)'
                ],
                'confidence_boost': 0.1
            },
            'investment': {
                'keywords': ['investir', 'placement', 'épargne', 'investment', 'saving'],
                'patterns': [
                    r'(?:investir|placer).*(?:argent|euros?|dollars?)',
                    r'(?:épargne|saving|placement)',
                    r'(?:portefeuille|portfolio).*(?:investment|investissement)'
                ],
                'confidence_boost': 0.2
            },
            'account_management': {
                'keywords': ['compte', 'account', 'ouvrir', 'fermer', 'créer'],
                'patterns': [
                    r'(?:ouvrir|créer|fermer).*compte',
                    r'(?:nouveau|new).*compte',
                    r'(?:gestion|management).*compte'
                ],
                'confidence_boost': 0.1
            }
        }
    
    def detect_intent_with_preferences(self, user_id: str, message: str, context: Dict = None) -> Dict[str, any]:
        """
        Détecte l'intention en tenant compte des préférences utilisateur
        """
        # Détection d'intention de base
        base_intent = self._detect_base_intent(message)
        
        # Prédiction intelligente basée sur l'utilisateur
        intelligent_prediction = self.user_intelligence.predict_user_intent(user_id, message, context)
        
        # Fusion des résultats de détection de base et intelligente
        final_intent = self._merge_intent_results(base_intent, intelligent_prediction)
        
        # Ajout des suggestions personnalisées
        final_intent['personalized_suggestions'] = intelligent_prediction.get('suggested_actions', [])
        final_intent['response_style'] = intelligent_prediction.get('personalized_response_style', 'neutral')
        
        # Log de l'interaction pour l'apprentissage
        interaction_data = {
            'action_type': 'intent_detection',
            'details': {
                'message': message,
                'detected_intent': final_intent['intent'],
                'confidence': final_intent['confidence']
            },
            'context': context or {}
        }
        self.user_intelligence.learn_from_interaction(user_id, interaction_data)
        
        return final_intent
    
    def _detect_base_intent(self, message: str) -> Dict[str, any]:
        """Détection d'intention de base avec patterns et mots-clés"""
        message_lower = message.lower()
        intent_scores = {}
        
        for intent_name, intent_config in self.intent_patterns.items():
            score = 0
            
            # Score basé sur les mots-clés
            keyword_matches = sum(1 for keyword in intent_config['keywords'] 
                                if keyword in message_lower)
            score += keyword_matches * 0.3
            
            # Score basé sur les patterns regex
            pattern_matches = sum(1 for pattern in intent_config['patterns']
                                if re.search(pattern, message_lower))
            score += pattern_matches * 0.5
            
            # Boost de confiance spécifique à l'intention
            if score > 0:
                score += intent_config.get('confidence_boost', 0)
            
            intent_scores[intent_name] = score
        
        # Trouver l'intention avec le score le plus élevé
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            return {
                'intent': best_intent[0],
                'confidence': min(0.95, best_intent[1]),
                'all_scores': intent_scores
            }
        
        return {
            'intent': 'unknown',
            'confidence': 0.2,
            'all_scores': intent_scores
        }
    
    def _merge_intent_results(self, base_intent: Dict, intelligent_prediction: Dict) -> Dict[str, any]:
        """Fusionne les résultats de détection de base et intelligente"""
        
        # Si les deux méthodes détectent la même intention
        if base_intent['intent'] == intelligent_prediction['primary_intent']:
            confidence = min(0.95, (base_intent['confidence'] + intelligent_prediction['confidence']) / 2 + 0.1)
            return {
                'intent': base_intent['intent'],
                'confidence': confidence,
                'method': 'merged_consensus',
                'base_scores': base_intent.get('all_scores', {}),
                'intelligent_confidence': intelligent_prediction['confidence']
            }
        
        # Si l'intelligence utilisateur a une forte confiance
        elif intelligent_prediction['confidence'] > 0.7:
            return {
                'intent': intelligent_prediction['primary_intent'],
                'confidence': intelligent_prediction['confidence'],
                'method': 'intelligent_override',
                'base_intent': base_intent['intent'],
                'base_confidence': base_intent['confidence']
            }
        
        # Si la détection de base a une forte confiance
        elif base_intent['confidence'] > 0.7:
            return {
                'intent': base_intent['intent'],
                'confidence': base_intent['confidence'],
                'method': 'base_detection',
                'intelligent_suggestion': intelligent_prediction['primary_intent'],
                'intelligent_confidence': intelligent_prediction['confidence']
            }
        
        # En cas de confiance faible des deux côtés, prendre le meilleur
        else:
            if base_intent['confidence'] >= intelligent_prediction['confidence']:
                chosen_intent = base_intent['intent']
                chosen_confidence = base_intent['confidence']
                method = 'base_fallback'
            else:
                chosen_intent = intelligent_prediction['primary_intent']
                chosen_confidence = intelligent_prediction['confidence']
                method = 'intelligent_fallback'
            
            return {
                'intent': chosen_intent,
                'confidence': chosen_confidence,
                'method': method,
                'alternative_intent': intelligent_prediction['primary_intent'] if method == 'base_fallback' else base_intent['intent'],
                'alternative_confidence': intelligent_prediction['confidence'] if method == 'base_fallback' else base_intent['confidence']
            }
    
    def add_user_specific_patterns(self, user_id: str, intent: str, user_expressions: List[str]):
        """Permet d'ajouter des patterns spécifiques à un utilisateur"""
        # Cette fonctionnalité pourrait être implémentée pour apprendre
        # des expressions spécifiques que chaque utilisateur utilise
        pass
    
    def get_intent_confidence_threshold(self, user_id: str) -> float:
        """Retourne le seuil de confiance adapté à l'utilisateur"""
        preferences = self.user_intelligence.get_user_preferences(user_id)
        
        # Utilisateurs expérimentés ont un seuil plus bas (plus de tolérance)
        activity_level = preferences.get('activity', {}).get('total_activity', 0)
        if activity_level > 50:
            return 0.6
        elif activity_level > 20:
            return 0.7
        else:
            return 0.8  # Nouveaux utilisateurs ont besoin de plus de certitude