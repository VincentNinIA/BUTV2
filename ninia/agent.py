#!/usr/bin/env python3
"""
Agent NINIA - Version Modulaire et Optimisée
===========================================

Agent spécialisé pour l'analyse des commandes utilisant l'architecture modulaire :
- Extraction via ninia.extraction
- Validation via ninia.analysis  
- Alternatives via ninia.alternatives

Priorise la recherche directe par ID exact avant tout appel LLM.
"""

import logging
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate
from rag.core import answer
from rag.retrieval import _inventory_df

# Import des nouveaux modules modulaires
from .extraction.product_parser import ProductParser
from .extraction.text_extractor import extract_product_info
from .analysis.order_validator import OrderValidator
from .analysis.stock_checker import check_stock, check_margin
from .alternatives.manager import AlternativesManager
from .comments.comment_agent import CommentAgent

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NiniaAgent:
    """Agent NINIA modulaire pour l'analyse des commandes"""
    
    def __init__(self, api_key: str):
        """
        Initialise l'agent NINIA avec l'architecture modulaire
        
        Args:
            api_key: Clé API OpenAI
        """
        if not api_key:
            raise ValueError("Une clé API est requise pour initialiser l'agent")
            
        self.llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0,
            api_key=api_key
        )
        
        # Initialisation des modules modulaires
        self.product_parser = ProductParser(_inventory_df)
        self.order_validator = OrderValidator()
        self.alternatives_manager = AlternativesManager(self.llm)
        self.comment_agent = CommentAgent(llm=self.llm)
        
        # Définir les outils disponibles
        self.tools = [
            Tool(
                name="verifier_stock",
                func=self.verifier_stock,
                description="Vérifie le stock disponible pour un produit donné. L'input est une chaîne (str) contenant le nom ou ID du produit."
            ),
            Tool(
                name="analyser_commande",
                func=self.analyser_commande,
                description="Analyse une demande de commande. L'input DOIT être une chaîne contenant la description complète de la commande."
            ),
            Tool(
                name="recherche_documents",
                func=answer,
                description="Recherche des informations détaillées dans la base de connaissances. Argument: query (str)"
            ),
            Tool(
                name="rechercher_alternatives",
                func=self.rechercher_alternatives,
                description="Recherche des alternatives pour un produit. L'input est une chaîne (str) contenant le nom ou ID du produit."
            )
        ]
        
        # Prompt système pour l'agent
        self.system_prompt = """Vous êtes NINIA, un assistant IA spécialisé dans l'analyse des commandes et la gestion d'inventaire.

**Instructions importantes :**
- Utilisez la vérification par ID exact en priorité [[memory:2717753]]
- Pour les commandes, analysez le stock, la marge et les alternatives
- Répondez de manière claire et structurée avec des émojis

**Types de requêtes :**
1. COMMANDE : Demandes d'achat avec produit et quantité
2. INFORMATION : Questions sur stocks, caractéristiques, disponibilité
3. ALTERNATIVES : Recherche de produits de remplacement

**Format de réponse :**
- ✅ OK : Commande réalisable
- ⚠️ ATTENTION : Problèmes mineurs
- ❌ REFUSÉ : Problèmes bloquants
- 🔄 ALTERNATIVES : Suggestions de remplacement

**Outils disponibles :**
- analyser_commande : Pour les demandes d'achat
- verifier_stock : Pour vérifier la disponibilité
- rechercher_alternatives : Pour trouver des remplacements
- recherche_documents : Pour les informations générales
"""
        
        # Créer le prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Créer l'agent et l'executor
        self.agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True
        )
    
    def verifier_stock(self, product_name_or_id: str) -> str:
        """
        Vérifie le stock disponible pour un produit
        
        Args:
            product_name_or_id: Nom ou ID du produit
            
        Returns:
            str: Informations sur le stock
        """
        try:
            logger.info(f"📦 Vérification stock : {product_name_or_id}")
            
            # Utiliser le nouveau module d'analyse
            result = check_stock(product_name_or_id)
            
            if not result["product_found"]:
                return f"❌ Produit '{product_name_or_id}' non trouvé"
            
            status = result["status"]
            stock = result["stock_disponible"]
            
            if status == "OK":
                return f"✅ {product_name_or_id} : {stock} unités disponibles"
            elif status == "RUPTURE":
                return f"❌ {product_name_or_id} : Rupture de stock"
            else:
                return f"❌ Erreur : {result['message']}"
                
        except Exception as e:
            logger.error(f"Erreur vérification stock : {str(e)}")
            return f"❌ Erreur lors de la vérification : {str(e)}"
    
    def analyser_commande(self, user_query_for_order: str) -> str:
        """
        Analyse une commande complète
        
        Args:
            user_query_for_order: Requête de commande de l'utilisateur
            
        Returns:
            str: Résultat de l'analyse
        """
        try:
            logger.info(f"🔍 Analyse commande : {user_query_for_order}")
            
            # Étape 1: Extraction via le nouveau module
            product_id, quantity, proposed_price = self.product_parser.extract_product_info(user_query_for_order)
            
            if not product_id:
                return f"❌ Impossible d'identifier le produit. Format attendu : 'ID_PRODUIT DESCRIPTION Qté QUANTITÉ Prix : PRIX€' [[memory:2717753]]"
            
            if not quantity or quantity <= 0:
                return f"❌ Quantité invalide ou manquante. Veuillez préciser la quantité."
            
            # Étape 2: Validation via le nouveau module
            validation_result = self.order_validator.validate_order(
                product_id, 
                quantity, 
                proposed_price
            )
            
            if validation_result.status == "ERROR":
                return validation_result.message
            
            # Étape 3: Gestion des alternatives si nécessaire
            if validation_result.status in ["ATTENTION", "REFUSED"] and validation_result.alternatives:
                # Déterminer le type de problème détecté
                problem_type = "Non spécifié"
                if validation_result.status == "REFUSED":
                    if "stock" in validation_result.message.lower():
                        problem_type = "Stock insuffisant"
                    elif "marge" in validation_result.message.lower():
                        problem_type = "Marge insuffisante"
                    else:
                        problem_type = "Commande refusée"
                elif validation_result.status == "ATTENTION":
                    problem_type = "Attention requise"
                
                # Préparer le contexte pour le LLM
                context_info = {
                    'quantity': quantity,
                    'proposed_price': proposed_price,
                    'problem_type': problem_type,
                    'original_message': validation_result.message
                }
                
                # Analyser et sélectionner la meilleure alternative avec contexte
                selection = self.alternatives_manager.select_best_alternative(
                    validation_result.product_info,
                    validation_result.alternatives,
                    selection_criteria=["similarité technique", "adaptabilité commerciale", "faisabilité"],
                    context_info=context_info
                )
                
                if selection.get("selected"):
                    alternative = selection["selected"]
                    alt_name = alternative.get("name", "Alternative")
                    reason = selection.get("reason", "Sélection automatique")
                    strategy = selection.get("commercial_strategy", "Approche standard")
                    confidence = selection.get("confidence", 0.8)
                    
                    # Message enrichi avec stratégie commerciale
                    return f"""{validation_result.message}

🔄 **ALTERNATIVE RECOMMANDÉE :**
• Produit : {alt_name}
• Stratégie : {strategy}
• Analyse : {reason}
• Confiance : {confidence:.0%}

💡 Cette recommandation est basée sur une analyse intelligente de la compatibilité technique et de la faisabilité commerciale."""
            
            return validation_result.message
                
        except Exception as e:
            logger.error(f"Erreur analyse commande : {str(e)}")
            return f"❌ Erreur lors de l'analyse : {str(e)}"
    
    def rechercher_alternatives(self, product_name_or_id: str) -> str:
        """
        Recherche des alternatives pour un produit
        
        Args:
            product_name_or_id: Nom ou ID du produit
            
        Returns:
            str: Liste des alternatives disponibles
        """
        try:
            logger.info(f"🔄 Recherche alternatives : {product_name_or_id}")
            
            # Utiliser le gestionnaire d'alternatives
            summary = self.alternatives_manager.get_alternatives_summary(
                product_name_or_id,
                quantity=1,  # Quantité par défaut pour la recherche
                proposed_price=None
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Erreur recherche alternatives : {str(e)}")
            return f"❌ Erreur lors de la recherche : {str(e)}"
    
    def process_message(self, message: str, chat_history: List[Dict[str, Any]] = None) -> str:
        """
        Traite un message utilisateur
        
        Args:
            message: Message de l'utilisateur
            chat_history: Historique des messages
            
        Returns:
            str: Réponse de l'agent
        """
        if not message or not isinstance(message, str):
            raise ValueError("Le message doit être une chaîne non vide")
            
        if chat_history is None:
            chat_history = []
            
        try:
            logger.info(f"📨 Traitement message : {message[:50]}...")
            
            # Détection automatique du type de requête
            message_lower = message.lower()
            
            # 1. Détection des demandes d'alternatives
            if any(keyword in message_lower for keyword in ["alternative", "remplacement", "autre", "similaire"]):
                # Extraire le produit mentionné
                product_id, _, _ = self.product_parser.extract_product_info(message)
                if product_id:
                    return self.rechercher_alternatives(product_id)
                else:
                    return "❌ Je n'ai pas pu identifier le produit pour lequel vous cherchez des alternatives."
            
            # 2. Détection des commandes (avec format spécial [[memory:2717753]])
            command_keywords = ["commande", "commander", "acheter", "prendre", "je veux", "je voudrais"]
            is_command = any(keyword in message_lower for keyword in command_keywords)
            
            # Détection des commandes implicites (quantité + prix)
            import re
            has_quantity = bool(re.search(r'\bqté\s+\d+|\d+\s+(?:unités?|pièces?|caisses?)', message, re.IGNORECASE))
            has_price = bool(re.search(r'\d+[€]|prix\s*:', message, re.IGNORECASE))
            
            if has_quantity and has_price:
                is_command = True
                logger.info("🎯 Commande implicite détectée")
            
            # Détection par format ID exact [[memory:2717753]]
            id_pattern = r'\b\d{5,7}\s+\d{8}\b'
            if re.search(id_pattern, message):
                is_command = True
                logger.info("🎯 Format ID exact détecté, traitement comme commande")
            
            if is_command:
                # Traiter comme commande
                return self.analyser_commande(message)
            
            # 3. Détection des vérifications de stock simples
            if any(keyword in message_lower for keyword in ["stock", "disponible", "dispo"]):
                product_id, _, _ = self.product_parser.extract_product_info(message)
                if product_id:
                    return self.verifier_stock(product_id)
            
            # 4. Traitement par l'agent général (questions, conversations)
            response = self.agent_executor.invoke({
                "input": message,
                "chat_history": chat_history
            })
            return response["output"]
                
        except Exception as e:
            logger.error(f"Erreur traitement message : {str(e)}")
            return f"❌ Désolé, une erreur s'est produite : {str(e)}"
    
    def debug_extraction(self, message: str) -> Dict[str, Any]:
        """
        Version debug pour voir toutes les étapes d'extraction
        Parfait pour identifier où ça plante !
        """
        return self.product_parser.debug_extraction(message)
    
    def debug_validation(self, product_id: str, quantity: int, proposed_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Version debug pour voir toutes les étapes de validation
        """
        return self.order_validator.debug_validation(product_id, quantity, proposed_price)
    
    def debug_alternatives(self, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        Version debug pour voir toutes les étapes de recherche d'alternatives
        """
        return self.alternatives_manager.debug_alternatives(product_id, quantity)
    
    def debug_comment_generation(self, context_info: Dict[str, Any]) -> Dict[str, Any]:
        """Debug de la génération de commentaires"""
        return self.comment_agent.debug_comment_generation(context_info)
    
    def generate_table_comment(self, commande_info: Dict[str, Any], comment_type: str = "auto") -> str:
        """
        Génère un commentaire intelligent pour le tableau de commandes
        
        Args:
            commande_info: Informations complètes sur la commande
            comment_type: Type de commentaire (auto, order, stock_alert, etc.)
            
        Returns:
            str: Commentaire généré par l'IA
        """
        try:
            logger.info(f"💬 Génération commentaire tableau - Type: {comment_type}")
            return self.comment_agent.generate_smart_comment(commande_info, comment_type)
        except Exception as e:
            logger.error(f"Erreur génération commentaire : {str(e)}")
            return "Analyse en cours - Commentaire à compléter"
    
    def generate_alert_email_if_needed(self, commande_info: Dict[str, Any], client_name: str = "Client") -> Optional[Dict[str, str]]:
        """
        Génère automatiquement un mail d'alerte commercial si des problèmes sont détectés.
        
        Args:
            commande_info: Informations complètes sur la commande
            client_name: Nom du client
            
        Returns:
            Optional[Dict[str, str]]: Mail d'alerte avec 'objet' et 'corps' si problème détecté, None sinon
        """
        try:
            logger.info(f"📧 Vérification besoin mail alerte pour {client_name}")
            return self.comment_agent.generate_alert_email_if_needed(commande_info, client_name)
        except Exception as e:
            logger.error(f"Erreur génération mail d'alerte : {str(e)}")
            return None 