"""Account query handler for processing banking-related questions."""

from typing import Dict, Any, Optional
from decimal import Decimal
from chatbot.database import (
    get_account_by_number, get_account_by_name, get_all_accounts_info,
    get_account_transactions, search_accounts, get_account_balance,
    get_total_balance
)
from chatbot.intent_detector import IntentDetector


class AccountQueryHandler:
    """Handles banking queries and returns formatted responses."""
    
    def __init__(self):
        self.intent_detector = IntentDetector()
    
    def handle_query(self, user_message: str, user_id: str = None) -> str:
        """
        Traite une requête utilisateur sur les comptes bancaires.
        
        :param user_message: Message de l'utilisateur
        :return: Réponse formatée
        """
        # Détecter l'intention et extraire les informations
        intent, extracted_info = self.intent_detector.detect_banking_intent(user_message)
        
        if not intent:
            return "Je n'ai pas compris votre demande concernant les comptes. Pouvez-vous reformuler ?"
        
        # Router vers la méthode appropriée
        try:
            if intent == "account_balance":
                return self._handle_balance_query(extracted_info, user_id)
            elif intent == "account_info":
                return self._handle_account_info_query(extracted_info, user_id)
            elif intent == "account_list":
                return self._handle_account_list_query(user_id)
            elif intent == "transactions":
                return self._handle_transactions_query(extracted_info, user_id)
            elif intent == "transfer":
                return self._handle_transfer_info(extracted_info)
            else:
                return f"Je ne peux pas encore traiter les requêtes de type '{intent}'."
        except Exception as e:
            return f"Une erreur s'est produite lors du traitement de votre demande : {str(e)}"
    
    def _handle_balance_query(self, info: Dict[str, Any], user_id: str = None) -> str:
        """Traite les requêtes de solde."""
        account_id = info.get('account_id')
        account_type = info.get('account_type')
        
        # Si on a un ID de compte spécifique
        if account_id:
            account = get_account_by_number(account_id, user_id)
            if account:
                return f"💰 Le solde du compte {account['account_name']} ({account_id}) est de {account['balance']:.2f} €."
            else:
                return f"❌ Aucun compte trouvé avec le numéro {account_id}."
        
        # Si on a un type de compte
        elif account_type:
            account = get_account_by_name(account_type, user_id)
            if account:
                return f"💰 Le solde de votre compte {account['account_name']} est de {account['balance']:.2f} €."
            else:
                return f"❌ Aucun compte trouvé de type '{account_type}'."
        
        # Sinon, afficher le solde total
        else:
            total_balance = get_total_balance(user_id)
            return f"💰 Votre solde total sur tous vos comptes est de {total_balance:.2f} €."
    
    def _handle_account_info_query(self, info: Dict[str, Any], user_id: str = None) -> str:
        """Traite les demandes d'informations sur un compte."""
        account_id = info.get('account_id')
        account_type = info.get('account_type')
        
        account = None
        if account_id:
            account = get_account_by_number(account_id, user_id)
        elif account_type:
            account = get_account_by_name(account_type, user_id)
        
        if account:
            return f"""📋 **Informations du compte**
            
🏦 **Nom du compte :** {account['account_name']}
🔢 **Numéro :** {account['account_number']}
💰 **Solde actuel :** {account['balance']:.2f} €"""
        else:
            search_term = account_id or account_type or "demandé"
            return f"❌ Aucun compte trouvé pour '{search_term}'."
    
    def _handle_account_list_query(self, user_id: str = None) -> str:
        """Traite les demandes de liste des comptes."""
        accounts = get_all_accounts_info(user_id)
        
        if not accounts:
            return "❌ Aucun compte trouvé dans la base de données."
        
        response = "📋 **Vos comptes :**\n\n"
        total_balance = Decimal('0.00')
        
        for i, account in enumerate(accounts, 1):
            response += f"{i}. **{account['account_name']}**\n"
            response += f"   🔢 Numéro : {account['account_number']}\n"
            response += f"   💰 Solde : {account['balance']:.2f} €\n\n"
            total_balance += account['balance']
        
        response += f"💎 **Solde total :** {total_balance:.2f} €"
        return response
    
    def _handle_transactions_query(self, info: Dict[str, Any], user_id: str = None) -> str:
        """Traite les demandes d'historique des transactions."""
        account_id = info.get('account_id')
        account_type = info.get('account_type')
        
        # Trouver le compte
        account = None
        if account_id:
            account = get_account_by_number(account_id, user_id)
        elif account_type:
            account = get_account_by_name(account_type, user_id)
        
        if not account:
            search_term = account_id or account_type or "demandé"
            return f"❌ Aucun compte trouvé pour '{search_term}'."
        
        # Récupérer les transactions
        transactions = get_account_transactions(account['account_number'], user_id, limit=5)
        
        if not transactions:
            return f"📊 Aucune transaction trouvée pour le compte {account['account_name']}."
        
        response = f"📊 **Dernières transactions - {account['account_name']}**\n\n"
        
        for transaction in transactions:
            emoji = "📤" if transaction['type'] == 'DEBIT' else "📥"
            sign = "-" if transaction['type'] == 'DEBIT' else "+"
            
            response += f"{emoji} **{transaction['type']}**\n"
            response += f"   💰 Montant : {sign}{transaction['amount']:.2f} €\n"
            response += f"   🔄 Autre compte : {transaction['other_account']}\n"
            response += f"   📅 Date : {transaction['date_time']}\n"
            response += f"   💳 Solde après : {transaction['balance_after']:.2f} €\n\n"
        
        return response
    
    def _handle_transfer_info(self, info: Dict[str, Any]) -> str:
        """Fournit des informations sur les virements."""
        return """💸 **Informations sur les virements**

Pour effectuer un virement, vous devez utiliser la commande de virement avec :
- Le compte source
- Le compte destination  
- Le montant

Exemple : "Virer 100€ de mon compte épargne vers mon compte courant"

Pour voir vos comptes disponibles, demandez : "Liste mes comptes"
"""
    
    def is_banking_query(self, message: str) -> bool:
        """Vérifie si le message est une requête bancaire."""
        return self.intent_detector.is_banking_query(message)
    
    def get_quick_account_info(self, account_identifier: str) -> Optional[str]:
        """
        Récupère rapidement les informations d'un compte.
        
        :param account_identifier: Numéro ou nom du compte
        :return: Informations formatées ou None
        """
        account = get_account_by_number(account_identifier)
        if not account:
            account = get_account_by_name(account_identifier)
        
        if account:
            return f"{account['account_name']} ({account['account_number']}) : {account['balance']:.2f} €"
        return None