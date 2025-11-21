import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

# Handle imports whether called directly or from MCP
try:
    from chatbot.rag.vector_store import load_vector_store, create_vector_store
    from chatbot.rag.document_loader import load_documents, split_documents
    from chatbot.user_intelligence import UserIntelligence
    from chatbot.behavior_tracker import BehaviorTracker
    from chatbot.enhanced_intent_detector import EnhancedIntentDetector
except ImportError:
    from chatbot.rag.vector_store import load_vector_store, create_vector_store
    from document_loader import load_documents, split_documents
    from user_intelligence import UserIntelligence
    from behavior_tracker import BehaviorTracker
    from enhanced_intent_detector import EnhancedIntentDetector

load_dotenv()

class S2MChatbot:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one instance is created"""
        if cls._instance is None:
            cls._instance = super(S2MChatbot, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, persist_directory=None):
        from chatbot.config import VECTOR_DB_DIR
        
        # Use config value if persist_directory is not provided
        if persist_directory is None:
            persist_directory = VECTOR_DB_DIR
        # Only initialize once
        if getattr(self, '_initialized', False):
            return
            
        # Initialize the vector store
        self._ensure_vector_store_exists(persist_directory)
        self.vector_store = load_vector_store(persist_directory)
        
        # Initialize the LLM with OpenAI
        api_key = "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"
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # LLM pour les questions bancaires (avec RAG)
        self.banking_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            openai_api_key=api_key
        )
        
        # LLM complètement séparé pour les questions générales (SANS RAG)
        self.general_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=api_key
        )
        
        # Create the retrieval chain SEULEMENT pour les questions bancaires
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.banking_llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 5}),
            return_source_documents=True
        )
        
        # Initialize intelligence components
        self.user_intelligence = UserIntelligence()
        self.behavior_tracker = BehaviorTracker()
        self.enhanced_intent_detector = EnhancedIntentDetector()
        
        # User session tracking
        self.user_sessions = {}
        
        self._initialized = True
   
    def _ensure_vector_store_exists(self, persist_directory):
        """Make sure the vector store exists, create it if it doesn't"""
        from chatbot.config import DOCS_DIRECTORY
        if not os.path.exists(persist_directory):
            print("Vector store not found. Creating new vector store...")
            if os.path.exists(DOCS_DIRECTORY):
                documents = load_documents(DOCS_DIRECTORY)
                chunks = split_documents(documents)
                if not chunks:
                    print("No document chunks found. Adding a placeholder document.")
                    chunks = ["Initial placeholder document"]
                create_vector_store(chunks, persist_directory)
            else:
                print(f"Warning: Documents directory {DOCS_DIRECTORY} not found.")
                print("Creating vector store with placeholder document.")
                create_vector_store(["Initial placeholder document"], persist_directory)

def _is_banking_related(self, question):
    """Enhanced check if a question is related to banking/finance or document content"""
    banking_keywords = [
        # Mots bancaires français
        'banque', 'bancaire', 'compte', 'prêt', 'crédit', 'hypothèque', 'investissement',
        'épargne', 'chèque', 'dépôt', 'retrait', 'virement', 'paiement', 'solde',
        'transaction', 'historique', 'carte', 'débit', 'intérêt', 'taux', 'succursale',
        
        # Mots bancaires anglais
        'bank', 'banking', 'account', 'loan', 'credit', 'mortgage', 'investment',
        'savings', 'checking', 'deposit', 'withdrawal', 'transfer', 'payment',
        'balance', 'transaction', 'history', 'card', 'debit', 'interest', 'rate',
        
        
        # Références aux documents
        'document', 'pdf', 'fichier', 'file', 'contenu', 'content',
        'document1', 'document2', 'doc', 'rapport', 'report',
        
        # Services financiers
        'finance', 'financial', 'money', 'argent', 'euro', 'dollar',
        'atm', 'guichet', 'online banking', 'mobile banking', 'banque en ligne',
        
        # Produits bancaires
        'tfsa', 'reer', 'rrsp', 'gic', 'mutual fund', 'fonds commun',
        'assurance', 'insurance', 'placement', 'portefeuille', 'portfolio'
    ]
    
    question_lower = question.lower()
    
    # Vérification directe des mots-clés
    keyword_found = any(keyword in question_lower for keyword in banking_keywords)
    
    # Vérification des patterns de questions sur documents
    document_patterns = [
        'dans le document',
        'selon le document', 
        'le document dit',
        'document1',
        'document2',
        'pdf',
        'fichier',
        'rapport',
        'what does the document say',
        'according to the document'
    ]
    
    document_question = any(pattern in question_lower for pattern in document_patterns)
    
    # Si c'est une question sur un document, on considère que c'est bancaire
    # car vos documents sont bancaires
    if document_question:
        print(f"🔍 Question détectée comme liée aux documents: {question}")
        return True
    
    if keyword_found:
        print(f"🔍 Question détectée comme bancaire: {question}")
        return True
    
    # Si aucun mot-clé trouvé, logger pour debug
    print(f"🔍 Question NON détectée comme bancaire: {question}")
    return False

def answer_question(self, question, user_id=None, session_id=None):
    """Modified answer_question with better debugging"""
    try:
        print(f"\n🤔 Traitement de la question: '{question}'")
        
        # Initialize session if provided
        if user_id and session_id:
            self._initialize_session(user_id, session_id)
        
        # DEBUG: Force banking detection for document questions
        is_banking = self._is_banking_related(question)
        print(f"🎯 Question classée comme: {'BANCAIRE' if is_banking else 'GÉNÉRALE'}")
        
        # Enhanced intent detection with user preferences
        if user_id:
            intent_result = self.enhanced_intent_detector.detect_intent_with_preferences(
                user_id=user_id,
                message=question,
                context={
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                }
            )
        else:
            # Fallback to basic detection for anonymous users
            intent_result = {
                'intent': 'banking' if is_banking else 'general',
                'confidence': 0.9 if is_banking else 0.7,
                'response_style': 'neutral',
                'personalized_suggestions': []
            }
        
        print(f"🎯 Intent détecté: {intent_result['intent']} (confiance: {intent_result['confidence']})")
        
        # MODIFICATION CRITIQUE: Force banking route for document questions
        question_lower = question.lower()
        force_banking = any(pattern in question_lower for pattern in [
            'document', 'pdf', 'fichier', 'rapport', 'contenu',
            'selon le document', 'dans le document'
        ])
        
        if force_banking:
            print("🔧 FORCAGE: Question redirigée vers le système bancaire/RAG")
            is_banking = True
            intent_result['intent'] = 'document_query'
        
        # Process question based on intent and user intelligence
        if is_banking or intent_result['intent'] in [
            'balance_inquiry', 'transfer', 'transaction_history', 'product_inquiry', 
            'investment', 'banking', 'document_query'
        ]:
            # BANKING: Use RAG system with personalization
            print("📚 Utilisation du système RAG...")
            result = self._handle_banking_question(question, user_id, intent_result)
        else:
            # NON-BANKING: Bypass RAG completely
            print("💭 Utilisation du LLM général...")
            result = self._handle_general_question(question, user_id, intent_result)
        
        # Apply user intelligence personalization
        if user_id and result.get("answer"):
            personalized_answer = self.user_intelligence.personalize_response(
                user_id=user_id,
                base_response=result["answer"],
                context={
                    'intent': intent_result['intent'],
                    'confidence': intent_result['confidence'],
                    'session_id': session_id,
                    'question_type': result.get("type", "unknown")
                }
            )
            result["answer"] = personalized_answer
            result["personalized"] = True
            result["suggestions"] = intent_result.get('personalized_suggestions', [])
            result["response_style"] = intent_result.get('response_style', 'neutral')
        
        # Use the formatter to format the response
        from chatbot.response_formatter import ResponseFormatter
        formatted_response = ResponseFormatter.format_answer_banking_question(result)
        
        # Log interaction for learning
        if user_id:
            self._log_interaction(user_id, question, result, intent_result, session_id)
        
        # Return enhanced response with intelligence data
        return {
            "formatted_answer": formatted_response,
            "raw_result": result,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "type": result.get("type", "unknown"),
            "personalized": result.get("personalized", False),
            "suggestions": result.get("suggestions", []),
            "response_style": result.get("response_style", "neutral"),
            "user_profile": self._get_user_context(user_id) if user_id else None
        }
            
    except Exception as e:
        error_response = f"Merci De poser une autre question, je ne peux t'aider en cela"
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "formatted_answer": error_response,
            "raw_result": {"error": str(e)},
            "answer": error_response,
            "sources": [],
            "type": "error",
            "personalized": False,
            "suggestions": [],
            "response_style": "neutral"
        }
def _initialize_session(self, user_id, session_id):
        """Initialize user session for tracking"""
        if session_id not in self.user_sessions:
            self.user_sessions[session_id] = {
                'user_id': user_id,
                'start_time': datetime.now(),
                'message_count': 0,
                'context': {},
                'last_intent': None
            }
        
        self.user_sessions[session_id]['message_count'] += 1
    
def _handle_banking_question(self, question, user_id=None, intent_result=None):
        """Handle banking questions using RAG with user intelligence"""
        try:
            # Enhance question based on user preferences
            enhanced_question = self._enhance_question_with_preferences(question, user_id, intent_result)
            
            banking_prompt = f"""
            Vous êtes un assistant spécialisé dans les services bancaires S2M.
            Utilisez le contexte fourni pour répondre à cette question bancaire.
            Si l'information n'est pas disponible dans le contexte, utilisez vos 
            connaissances générales sur les services bancaires.
            
            Question: {enhanced_question}
            
            Style de réponse souhaité: {intent_result.get('response_style', 'neutral') if intent_result else 'neutral'}
            """
            
            result = self.qa_chain.invoke({"query": banking_prompt})
            
            sources = []
            for doc in result["source_documents"]:
                if hasattr(doc, "metadata") and "source" in doc.metadata:
                    sources.append(doc.metadata["source"])
            
            # Add intelligent suggestions if user provided
            banking_result = {
                "answer": result["result"],
                "sources": list(set(sources)),
                "type": "banking"
            }
            
            # Add personalized quick actions for banking operations
            if user_id and intent_result:
                quick_actions = self._get_banking_quick_actions(user_id, intent_result['intent'])
                if quick_actions:
                    banking_result["quick_actions"] = quick_actions
            
            return banking_result
            
        except Exception as e:
            return {
                "answer": f"Erreur lors du traitement de la question bancaire: {str(e)}",
                "sources": [],
                "type": "error"
            }
    
def _handle_general_question(self, question, user_id=None, intent_result=None):
        """Handle general questions WITHOUT using RAG at all"""
        try:
            # Adapt response style based on user preferences
            response_style = intent_result.get('response_style', 'neutral') if intent_result else 'neutral'
            
            style_instructions = {
                'detailed': "Répondez de manière détaillée avec des exemples et des explications approfondies.",
                'concise': "Répondez de manière concise et directe, en allant à l'essentiel.",
                'neutral': "Répondez de manière équilibrée et informative."
            }
            
            general_prompt = f"""
            Vous êtes un assistant IA utile et compétent. 
            {style_instructions.get(response_style, style_instructions['neutral'])}
            
            Question: {question}
            """
            
            # Direct LLM call - NO RAG, NO retrieval, NO vector store
            from langchain_core.messages import HumanMessage
            messages = [HumanMessage(content=general_prompt)]
            response = self.general_llm.invoke(messages)
            
            return {
                "answer": response.content,
                "sources": [],
                "type": "general"
            }
            
        except Exception as e:
            # Fallback response si même l'appel direct échoue
            return {
                "answer": f"""
                Je peux répondre à votre question: {question}
                
                Cependant, j'ai rencontré une erreur technique ({str(e)}). 
                Pour une réponse plus précise sur ce sujet non-bancaire, 
                je vous recommande de consulter des sources spécialisées.
                """,
                "sources": [],
                "type": "fallback"
            }
    
def _enhance_question_with_preferences(self, question, user_id, intent_result):
        """Enhance question based on user preferences and context"""
        if not user_id or not intent_result:
            return question
        
        enhanced_question = question
        preferences = self.user_intelligence.get_user_preferences(user_id)
        
        # Add context based on user's primary account
        if intent_result['intent'] == 'balance_inquiry':
            primary_account = preferences.get('account', {}).get('primary_account', {}).get('value')
            if primary_account:
                enhanced_question += f" (L'utilisateur utilise principalement le compte {primary_account})"
        
        # Add context for transfers
        elif intent_result['intent'] == 'transfer':
            preferred_amount = preferences.get('transaction', {}).get('preferred_amount', {}).get('value')
            if preferred_amount:
                enhanced_question += f" (L'utilisateur effectue habituellement des virements de {preferred_amount}€)"
        
        return enhanced_question
    
def _get_banking_quick_actions(self, user_id, intent):
        """Generate quick actions based on user preferences and intent"""
        preferences = self.user_intelligence.get_user_preferences(user_id)
        quick_actions = []
        
        if intent == 'balance_inquiry':
            primary_account = preferences.get('account', {}).get('primary_account', {}).get('value')
            if primary_account:
                quick_actions.append(f"Consulter le solde de {primary_account}")
            quick_actions.append("Voir tous les comptes")
        
        elif intent == 'transfer':
            preferred_amount = preferences.get('transaction', {}).get('preferred_amount', {}).get('value')
            if preferred_amount:
                quick_actions.append(f"Virement rapide de {preferred_amount}€")
            quick_actions.append("Nouveau virement personnalisé")
        
        elif intent == 'transaction_history':
            quick_actions.extend([
                "Historique des 7 derniers jours",
                "Rechercher une transaction",
                "Exporter l'historique"
            ])
        
        return quick_actions[:3]  # Limit to 3 actions
    
def _log_interaction(self, user_id, question, result, intent_result, session_id):
        """Log interaction for user intelligence learning"""
        interaction_data = {
            'action_type': 'chat_interaction',
            'details': {
                'message': question,
                'intent': intent_result['intent'],
                'response_length': len(result.get('answer', '')),
                'confidence': intent_result['confidence'],
                'response_type': result.get('type', 'unknown'),
                'sources_count': len(result.get('sources', []))
            },
            'context': {
                'session_id': session_id,
                'response_personalized': result.get('personalized', False),
                'suggestions_count': len(result.get('suggestions', [])),
                'timestamp': datetime.now().isoformat()
            },
            'session_id': session_id
        }
        
        self.user_intelligence.learn_from_interaction(user_id, interaction_data)
    
def _get_user_context(self, user_id):
        """Get user context for response enhancement"""
        if not user_id:
            return None
        
        try:
            profile = self.user_intelligence.get_user_profile_summary(user_id)
            return {
                'activity_level': profile.get('activity_level', 'Occasionnel'),
                'primary_account': profile.get('primary_account', 'Non défini'),
                'communication_style': profile.get('communication_style', 'neutral'),
                'preferences_learned': profile.get('preferences_count', 0) > 0
            }
        except Exception:
            return None
    
def get_user_dashboard(self, user_id):
        """Generate personalized dashboard for user"""
        if not user_id:
            return None
        
        try:
            profile = self.user_intelligence.get_user_profile_summary(user_id)
            recent_activity = self.behavior_tracker.get_user_activity_pattern(user_id, days_back=7)
            
            dashboard = {
                'welcome_message': f"Bonjour ! Vous êtes un utilisateur {profile.get('activity_level', 'occasionnel').lower()}.",
                'quick_actions': self._get_personalized_quick_actions(user_id),
                'recent_patterns': {
                    'most_used_feature': profile.get('most_frequent_action', 'Non défini'),
                    'preferred_time': f"Vous utilisez généralement nos services vers {profile.get('peak_usage_hour', 'Variable')}h"
                },
                'recommendations': self._get_personalized_recommendations(user_id),
                'preferences_status': f"{profile.get('preferences_count', 0)} préférences apprises",
                'stats': {
                    'total_interactions': recent_activity.get('total_activity', 0),
                    'last_update': profile.get('last_preference_update', 'Jamais')
                }
            }
            
            return dashboard
        except Exception as e:
            return {
                'error': f"Erreur lors de la génération du dashboard: {str(e)}",
                'quick_actions': ["Consulter le solde", "Faire un virement", "Voir l'historique"],
                'welcome_message': "Bonjour ! Comment puis-je vous aider aujourd'hui ?"
            }
    
def _get_personalized_quick_actions(self, user_id):
        """Generate personalized quick actions"""
        try:
            preferences = self.user_intelligence.get_user_preferences(user_id)
            actions = []
            
            primary_account = preferences.get('account', {}).get('primary_account', {}).get('value')
            if primary_account:
                actions.append(f"Consulter le solde de {primary_account}")
            
            preferred_amount = preferences.get('transaction', {}).get('preferred_amount', {}).get('value')
            if preferred_amount:
                actions.append(f"Virement rapide de {preferred_amount}€")
            
            actions.extend([
                "Voir l'historique récent",
                "Explorer nos produits"
            ])
            
            return actions[:4]  # Limit to 4 actions
        except Exception:
            return ["Consulter le solde", "Faire un virement", "Voir l'historique", "Aide"]
    
def _get_personalized_recommendations(self, user_id):
        """Generate personalized recommendations"""
        try:
            activity = self.behavior_tracker.get_user_activity_pattern(user_id, days_back=30)
            recommendations = []
            
            top_actions = activity.get('top_actions', {})
            if any('investment' in str(action).lower() for action in top_actions.keys()):
                recommendations.append("Découvrir nos nouvelles options d'investissement")
            
            if activity.get('total_activity', 0) > 20:
                recommendations.append("Activer les notifications intelligentes")
            
            recommendations.append("Personnaliser davantage vos préférences")
            
            return recommendations[:3]
        except Exception:
            return ["Découvrir nos services", "Optimiser votre épargne", "Consulter nos offres"]
    
def reset_user_preferences(self, user_id):
        """Reset user preferences and learning data"""
        if user_id:
            try:
                self.user_intelligence.reset_user_preferences(user_id)
                # Also clear session data
                sessions_to_remove = [sid for sid, session in self.user_sessions.items() 
                                    if session.get('user_id') == user_id]
                for sid in sessions_to_remove:
                    del self.user_sessions[sid]
                return {"success": True, "message": "Préférences utilisateur réinitialisées"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "ID utilisateur requis"}
    
def test_general_response(self, question):
        """Method specifically for testing general responses"""
        return self._handle_general_question(question)
    
def get_relevant_documents(self, query):
        """Retrieve relevant documents for a query without generating an answer"""
        try:
            docs = self.vector_store.similarity_search(query, k=5)
            sources = []
            for doc in docs:
                if hasattr(doc, "metadata") and "source" in doc.metadata:
                    sources.append(doc.metadata["source"])
            return {
                "documents": docs,
                "sources": list(set(sources))
            }
        except Exception as e:
            return {
                "documents": [],
                "sources": [],
                "error": str(e)
            }
    
    # Legacy method for backward compatibility
def answer_question_legacy(self, question):
        """Legacy method without user intelligence for backward compatibility"""
        return self.answer_question(question, user_id=None, session_id=None)