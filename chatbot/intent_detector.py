"""Intent detection for the banking assistant."""
from typing import Optional, Tuple, Dict, List
import re
from chatbot.config_client import COMMANDS

class IntentDetector:
    """Detects user commands and banking intents from input text."""
    
    # Mots-clés pour les différentes intentions bancaires
    BANKING_INTENTS = {
        "account_balance": [
            "solde", "balance", "combien", "montant", "argent disponible",
            "combien j'ai", "mon solde", "balance de", "solde de"
        ],
        "account_info": [
            "informations", "détails", "infos", "renseignements", 
            "info compte", "détails compte", "informations compte"
        ],
        "account_list": [
            "mes comptes", "tous mes comptes", "liste comptes", 
            "comptes", "liste de mes comptes", "afficher comptes"
        ],
        "transactions": [
            "transactions", "historique", "mouvements", "opérations",
            "dernières transactions", "historique compte", "mouvements compte"
        ],
        "transfer": [
            "virement", "transférer", "envoyer", "transfer", 
            "virer", "envoyer argent", "transférer argent"
        ]
    }
    
    # Patterns pour extraire les informations des comptes
    ACCOUNT_PATTERNS = {
        'account_id': r'\b\d{10,12}\b',  # ID de compte (10-12 chiffres)
        'account_type': r'\b(checking|savings|épargne|courant|livret|compte courant|compte épargne)\b',
        'amount': r'\b\d+(?:[.,]\d{2})?\s*(?:€|euros?|dollars?|\$)?\b'
    }
    
    @staticmethod
    def detect_command(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect if the text contains a command.
        
        Returns:
            Tuple of (command_type, command_arg) or (None, None) if no command detected
        """
        text_lower = text.strip().lower()
        
        # Check for exit command
        if any(text_lower == cmd for cmd in COMMANDS["exit"]):
            return ("exit", None)
            
        # Check for clear command
        if any(text_lower == cmd for cmd in COMMANDS["clear"]):
            return ("clear", None)
            
        # Check for user command
        if text_lower.startswith("user "):
            return ("user", text[5:].strip())
            
        return (None, None)
    
    @staticmethod
    def detect_banking_intent(text: str) -> Tuple[Optional[str], Dict[str, Optional[str]]]:
        """
        Detect banking-related intents from user input.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (intent_type, extracted_info) where extracted_info contains
            account_id, account_type, amount, etc.
        """
        text_lower = text.strip().lower()
        
        # Dictionnaire pour stocker les informations extraites
        extracted_info = {
            'account_id': None,
            'account_type': None,
            'amount': None,
            'original_text': text
        }
        
        # Extraire les informations du texte
        extracted_info.update(IntentDetector._extract_account_info(text))
        
        # Détecter l'intention principale
        for intent, keywords in IntentDetector.BANKING_INTENTS.items():
            if any(keyword in text_lower for keyword in keywords):
                return (intent, extracted_info)
        
        # Si aucune intention spécifique n'est détectée mais qu'on a un ID de compte
        if extracted_info['account_id']:
            return ("account_info", extracted_info)
        
        return (None, extracted_info)
    
    @staticmethod
    def _extract_account_info(text: str) -> Dict[str, Optional[str]]:
        """
        Extract account-related information from text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with extracted account information
        """
        info = {}
        
        # Extraire l'ID du compte
        account_id_match = re.search(IntentDetector.ACCOUNT_PATTERNS['account_id'], text)
        info['account_id'] = account_id_match.group() if account_id_match else None
        
        # Extraire le type de compte
        account_type_match = re.search(IntentDetector.ACCOUNT_PATTERNS['account_type'], text.lower())
        info['account_type'] = account_type_match.group() if account_type_match else None
        
        # Extraire le montant
        amount_match = re.search(IntentDetector.ACCOUNT_PATTERNS['amount'], text)
        info['amount'] = amount_match.group() if amount_match else None
        
        return info
    
    @staticmethod
    def is_banking_query(text: str) -> bool:
        """
        Check if the text is a banking-related query.
        
        Args:
            text: Input text
            
        Returns:
            True if the text contains banking-related keywords
        """
        text_lower = text.strip().lower()
        
        # Mots-clés généraux bancaires
        banking_keywords = [
            'compte', 'solde', 'virement', 'transaction', 'argent', 
            'euro', 'dollar', 'balance', 'épargne', 'courant'
        ]
        
        # Vérifier la présence de mots-clés bancaires
        has_banking_keywords = any(keyword in text_lower for keyword in banking_keywords)
        
        # Vérifier la présence d'un pattern de compte
        has_account_pattern = bool(re.search(IntentDetector.ACCOUNT_PATTERNS['account_id'], text))
        
        return has_banking_keywords or has_account_pattern
    
    @staticmethod
    def get_intent_confidence(text: str, intent: str) -> float:
        """
        Calculate confidence score for a detected intent.
        
        Args:
            text: Input text
            intent: Detected intent
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not intent or intent not in IntentDetector.BANKING_INTENTS:
            return 0.0
        
        text_lower = text.strip().lower()
        keywords = IntentDetector.BANKING_INTENTS[intent]
        
        # Compter les mots-clés présents
        matched_keywords = sum(1 for keyword in keywords if keyword in text_lower)
        
        # Calculer le score de confiance
        confidence = min(matched_keywords / len(keywords) * 2, 1.0)
        
        return confidence