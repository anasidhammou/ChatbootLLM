import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class UserIntelligence:
    """Classe pour gérer l'intelligence utilisateur et la personnalisation des réponses"""
    
    def __init__(self, data_file="user_profiles.json"):
        self.data_file = data_file
        self.user_profiles = self._load_user_profiles()
    
    def _load_user_profiles(self) -> Dict[str, Any]:
        """Charge les profils utilisateur depuis le fichier JSON"""
        if os.path.exists(self.data_file):
            try:
                # Essayer d'abord UTF-8
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except UnicodeDecodeError:
                try:
                    # Essayer avec un autre encodage
                    with open(self.data_file, 'r', encoding='utf-8', errors='ignore') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    print(f"Erreur de lecture du fichier {self.data_file}. Création d'un nouveau profil.")
                    # Sauvegarder l'ancien fichier et créer un nouveau
                    backup_file = f"{self.data_file}.backup"
                    try:
                        os.rename(self.data_file, backup_file)
                        print(f"Fichier corrompu sauvegardé comme {backup_file}")
                    except:
                        pass
                    return {}
            except (json.JSONDecodeError, IOError):
                print(f"Erreur de lecture du fichier {self.data_file}. Réinitialisation.")
                return {}
        return {}
    
    def _save_user_profiles(self):
        """Sauvegarde les profils utilisateur dans le fichier JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_profiles, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Erreur lors de la sauvegarde des profils: {e}")
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Récupère les préférences d'un utilisateur"""
        return self.user_profiles.get(user_id, {}).get('preferences', {})
    
    def get_user_profile_summary(self, user_id: str) -> Dict[str, Any]:
        """Récupère un résumé du profil utilisateur"""
        profile = self.user_profiles.get(user_id, {})
        
        return {
            'activity_level': self._calculate_activity_level(user_id),
            'primary_account': profile.get('preferences', {}).get('account', {}).get('primary_account', {}).get('value', 'Non défini'),
            'communication_style': profile.get('preferences', {}).get('communication', {}).get('style', {}).get('value', 'neutral'),
            'most_frequent_action': self._get_most_frequent_action(user_id),
            'peak_usage_hour': self._get_peak_usage_hour(user_id),
            'preferences_count': len(profile.get('preferences', {})),
            'last_preference_update': profile.get('last_updated', 'Jamais')
        }
    
    def personalize_response(self, user_id: str, base_response: str, context: Dict[str, Any]) -> str:
        """Personnalise une réponse basée sur les préférences utilisateur"""
        preferences = self.get_user_preferences(user_id)
        
        # Style de communication
        comm_style = preferences.get('communication', {}).get('style', {}).get('value', 'neutral')
        
        if comm_style == 'detailed':
            return self._make_response_detailed(base_response, context)
        elif comm_style == 'concise':
            return self._make_response_concise(base_response)
        else:
            return base_response
    
    def learn_from_interaction(self, user_id: str, interaction_data: Dict[str, Any]):
        """Apprend des interactions utilisateur pour améliorer la personnalisation"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'preferences': {},
                'interactions': [],
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
        
        # Ajouter l'interaction
        self.user_profiles[user_id]['interactions'].append({
            **interaction_data,
            'timestamp': datetime.now().isoformat()
        })
        
        # Limiter l'historique à 100 interactions
        if len(self.user_profiles[user_id]['interactions']) > 100:
            self.user_profiles[user_id]['interactions'] = self.user_profiles[user_id]['interactions'][-100:]
        
        # Mettre à jour les préférences basées sur les interactions
        self._update_preferences_from_interaction(user_id, interaction_data)
        
        # Mettre à jour la date de dernière modification
        self.user_profiles[user_id]['last_updated'] = datetime.now().isoformat()
        
        # Sauvegarder
        self._save_user_profiles()
    
    def reset_user_preferences(self, user_id: str):
        """Remet à zéro les préférences d'un utilisateur"""
        if user_id in self.user_profiles:
            self.user_profiles[user_id]['preferences'] = {}
            self.user_profiles[user_id]['last_updated'] = datetime.now().isoformat()
            self._save_user_profiles()
    
    def _calculate_activity_level(self, user_id: str) -> str:
        """Calcule le niveau d'activité de l'utilisateur"""
        profile = self.user_profiles.get(user_id, {})
        interactions = profile.get('interactions', [])
        
        if len(interactions) >= 50:
            return "Très actif"
        elif len(interactions) >= 20:
            return "Actif"
        elif len(interactions) >= 5:
            return "Modéré"
        else:
            return "Occasionnel"
    
    def _get_most_frequent_action(self, user_id: str) -> str:
        """Trouve l'action la plus fréquente de l'utilisateur"""
        profile = self.user_profiles.get(user_id, {})
        interactions = profile.get('interactions', [])
        
        if not interactions:
            return "Non défini"
        
        actions = {}
        for interaction in interactions:
            action = interaction.get('details', {}).get('intent', 'unknown')
            actions[action] = actions.get(action, 0) + 1
        
        if actions:
            return max(actions, key=actions.get)
        return "Non défini"
    
    def _get_peak_usage_hour(self, user_id: str) -> str:
        """Trouve l'heure de pic d'utilisation de l'utilisateur"""
        profile = self.user_profiles.get(user_id, {})
        interactions = profile.get('interactions', [])
        
        if not interactions:
            return "Variable"
        
        hours = {}
        for interaction in interactions:
            try:
                timestamp = interaction.get('context', {}).get('timestamp', '')
                if timestamp:
                    hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
                    hours[hour] = hours.get(hour, 0) + 1
            except:
                continue
        
        if hours:
            return str(max(hours, key=hours.get))
        return "Variable"
    
    def _make_response_detailed(self, response: str, context: Dict[str, Any]) -> str:
        """Rend une réponse plus détaillée"""
        if context.get('intent') == 'balance_inquiry':
            return f"{response}\n\nPour plus d'informations sur vos comptes, vous pouvez également consulter l'historique de vos transactions récentes ou configurer des alertes de solde."
        elif context.get('intent') == 'transfer':
            return f"{response}\n\nN'oubliez pas que vous pouvez programmer des virements récurrents et définir des bénéficiaires favoris pour simplifier vos futures transactions."
        else:
            return f"{response}\n\nN'hésitez pas si vous avez d'autres questions ou si vous souhaitez plus de détails sur ce sujet."
    
    def _make_response_concise(self, response: str) -> str:
        """Rend une réponse plus concise"""
        # Prend seulement la première phrase ou les 150 premiers caractères
        sentences = response.split('. ')
        if len(sentences) > 1 and len(sentences[0]) > 50:
            return sentences[0] + '.'
        elif len(response) > 150:
            return response[:147] + '...'
        return response
    
    def _update_preferences_from_interaction(self, user_id: str, interaction_data: Dict[str, Any]):
        """Met à jour les préférences basées sur une interaction"""
        intent = interaction_data.get('details', {}).get('intent')
        response_length = interaction_data.get('details', {}).get('response_length', 0)
        
        # Inférer le style de communication préféré
        if response_length > 300:
            style = 'detailed'
        elif response_length < 100:
            style = 'concise'
        else:
            style = 'neutral'
        
        # Mettre à jour les préférences
        if 'preferences' not in self.user_profiles[user_id]:
            self.user_profiles[user_id]['preferences'] = {}
        
        if 'communication' not in self.user_profiles[user_id]['preferences']:
            self.user_profiles[user_id]['preferences']['communication'] = {}
        
        self.user_profiles[user_id]['preferences']['communication']['style'] = {
            'value': style,
            'confidence': 0.7,
            'last_updated': datetime.now().isoformat()
        }