"""
Agent de génération de commentaires intelligents pour NINIA
=========================================================

Agent spécialisé dans la génération automatique de commentaires
pour les tableaux de traitement des commandes.
"""

import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from .comment_templates import CommentTemplates


class CommentAgent:
    """
    Agent spécialisé dans la génération de commentaires intelligents.
    
    Cet agent utilise différents templates de prompts selon le contexte
    pour générer des commentaires professionnels et pertinents.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, api_key: Optional[str] = None):
        """
        Initialise l'agent de commentaires.
        
        Args:
            llm: Instance LLM existante (optionnel)
            api_key: Clé API OpenAI si LLM n'est pas fourni
        """
        self.logger = logging.getLogger(__name__)
        
        if llm:
            self.llm = llm
        elif api_key:
            self.llm = ChatOpenAI(
                model="gpt-4.1",
                temperature=0.3,  # Moins de créativité pour des commentaires précis
                api_key=api_key,
            )
        else:
            raise ValueError("Veuillez fournir soit un LLM, soit une clé API")
        
        self.templates = CommentTemplates()
        self.logger.info("✅ CommentAgent initialisé avec succès")
    
    def generate_order_comment(self, commande_info: Dict[str, Any]) -> str:
        """
        Génère un commentaire pour l'analyse d'une commande.
        
        Args:
            commande_info: Informations complètes sur la commande
            
        Returns:
            str: Commentaire généré par l'IA
        """
        try:
            prompt = self.templates.get_order_analysis_prompt(commande_info)
            response = self.llm.invoke(prompt)
            comment = response.content.strip()
            
            self.logger.info(f"💬 Commentaire commande généré: {comment[:50]}...")
            return comment
            
        except Exception as e:
            self.logger.error(f"Erreur génération commentaire commande: {str(e)}")
            return self._get_fallback_order_comment(commande_info)
    
    def generate_stock_alert_comment(self, produit_info: Dict[str, Any]) -> str:
        """
        Génère un commentaire d'alerte de stock.
        
        Args:
            produit_info: Informations sur le produit en alerte
            
        Returns:
            str: Commentaire d'alerte généré
        """
        try:
            prompt = self.templates.get_stock_alert_prompt(produit_info)
            response = self.llm.invoke(prompt)
            comment = response.content.strip()
            
            self.logger.info(f"🚨 Alerte stock générée: {comment[:50]}...")
            return comment
            
        except Exception as e:
            self.logger.error(f"Erreur génération alerte stock: {str(e)}")
            return f"ALERTE STOCK - {produit_info.get('nom_produit', 'Produit')} - Action requise"
    
    def generate_margin_comment(self, marge_info: Dict[str, Any]) -> str:
        """
        Génère un commentaire d'analyse de marge.
        
        Args:
            marge_info: Informations sur les marges
            
        Returns:
            str: Commentaire de marge généré
        """
        try:
            prompt = self.templates.get_margin_analysis_prompt(marge_info)
            response = self.llm.invoke(prompt)
            comment = response.content.strip()
            
            self.logger.info(f"💰 Commentaire marge généré: {comment[:50]}...")
            return comment
            
        except Exception as e:
            self.logger.error(f"Erreur génération commentaire marge: {str(e)}")
            marge_ok = marge_info.get('marge_calculee', 0) >= marge_info.get('marge_minimum', 0)
            return "Marge acceptable - Vente rentable" if marge_ok else "Marge insuffisante - Vente non rentable"
    
    def generate_delivery_comment(self, delai_info: Dict[str, Any]) -> str:
        """
        Génère un commentaire d'analyse de délai de livraison.
        
        Args:
            delai_info: Informations sur les délais
            
        Returns:
            str: Commentaire de délai généré
        """
        try:
            prompt = self.templates.get_delivery_analysis_prompt(delai_info)
            response = self.llm.invoke(prompt)
            comment = response.content.strip()
            
            self.logger.info(f"🚚 Commentaire délai généré: {comment[:50]}...")
            return comment
            
        except Exception as e:
            self.logger.error(f"Erreur génération commentaire délai: {str(e)}")
            return "Délai en cours d'analyse"
    
    def generate_alternative_comment(self, alternative_info: Dict[str, Any]) -> str:
        """
        Génère un commentaire de suggestion d'alternative.
        
        Args:
            alternative_info: Informations sur les alternatives
            
        Returns:
            str: Commentaire d'alternative généré
        """
        try:
            prompt = self.templates.get_alternative_suggestion_prompt(alternative_info)
            response = self.llm.invoke(prompt)
            comment = response.content.strip()
            
            self.logger.info(f"🔄 Commentaire alternative généré: {comment[:50]}...")
            return comment
            
        except Exception as e:
            self.logger.error(f"Erreur génération commentaire alternative: {str(e)}")
            alt_name = alternative_info.get('alternative_nom', 'Alternative')
            alt_stock = alternative_info.get('alternative_stock', 0)
            return f"Alternative disponible - {alt_name} - Stock : {alt_stock}"
    
    def generate_order_with_alternatives_comment(self, commande_info: Dict[str, Any]) -> str:
        """
        ✅ NOUVEAU: Génère un commentaire de commande intégrant les alternatives RAG.
        
        Args:
            commande_info: Informations complètes avec alternatives RAG
            
        Returns:
            str: Commentaire enrichi avec alternatives
        """
        try:
            # Récupérer les informations de base
            stock_ok = commande_info.get('stock_suffisant', False)
            marge_ok = commande_info.get('marge_suffisante', False)
            nb_alternatives = commande_info.get('alternatives_disponibles', 0)
            
            # Déterminer le statut principal
            if stock_ok and marge_ok:
                statut_principal = "✅ Commande validée"
            elif not stock_ok and not marge_ok:
                statut_principal = "❌ Stock et marge insuffisants"
            elif not stock_ok:
                statut_principal = "🚨 RUPTURE DE STOCK - Alerte envoyée"
            else:
                statut_principal = "⚠️ Marge insuffisante - Négociation requise"
            
            # ✅ AMÉLIORATION: Afficher "4 alternatives proposées" (les meilleures)
            nb_proposees = min(4, nb_alternatives)
            commentaire_final = f"{statut_principal} | 🔄 {nb_proposees} alternatives proposées"
            
            self.logger.info(f"🔄 Commentaire avec {nb_proposees} alternatives proposées: {commentaire_final}")
            return commentaire_final
            
        except Exception as e:
            self.logger.error(f"Erreur génération commentaire avec alternatives: {str(e)}")
            nb_alt = min(4, commande_info.get('alternatives_disponibles', 0))
            return f"Analyse en cours | 🔄 {nb_alt} alternatives proposées"
    
    def generate_product_comment(self, produit_info: Dict[str, Any]) -> str:
        """
        Génère un commentaire général sur un produit.
        
        Args:
            produit_info: Informations générales sur le produit
            
        Returns:
            str: Commentaire produit généré
        """
        try:
            prompt = self.templates.get_general_product_comment_prompt(produit_info)
            response = self.llm.invoke(prompt)
            comment = response.content.strip()
            
            self.logger.info(f"📦 Commentaire produit généré: {comment[:50]}...")
            return comment
            
        except Exception as e:
            self.logger.error(f"Erreur génération commentaire produit: {str(e)}")
            nom = produit_info.get('nom_produit', 'Produit')
            stock = produit_info.get('stock', 0)
            prix = produit_info.get('prix', 0)
            return f"Emballage - Stock: {stock} unités - Prix: {prix:.2f}€"
    
    def generate_smart_comment(self, context_info: Dict[str, Any], comment_type: str = "auto") -> str:
        """
        Génère un commentaire intelligent en détectant automatiquement le type.
        
        Args:
            context_info: Toutes les informations disponibles
            comment_type: Type spécifique ou "auto" pour détection automatique
            
        Returns:
            str: Commentaire intelligent généré
        """
        try:
            # Détection automatique du type si non spécifié
            if comment_type == "auto":
                comment_type = self._detect_comment_type(context_info)
            
            # Génération selon le type détecté
            if comment_type == "order_with_alternatives":
                return self.generate_order_with_alternatives_comment(context_info)
            elif comment_type == "order":
                return self.generate_order_comment(context_info)
            elif comment_type == "stock_alert":
                return self.generate_stock_alert_comment(context_info)
            elif comment_type == "margin":
                return self.generate_margin_comment(context_info)
            elif comment_type == "delivery":
                return self.generate_delivery_comment(context_info)
            elif comment_type == "alternative":
                return self.generate_alternative_comment(context_info)
            elif comment_type == "product":
                return self.generate_product_comment(context_info)
            else:
                # Type non reconnu, utiliser le commentaire de commande par défaut
                return self.generate_order_comment(context_info)
        
        except Exception as e:
            self.logger.error(f"Erreur génération commentaire intelligent: {str(e)}")
            return "Analyse en cours - Commentaire à compléter"
    
    def _detect_comment_type(self, context_info: Dict[str, Any]) -> str:
        """
        Détecte automatiquement le type de commentaire à générer.
        
        Args:
            context_info: Informations de contexte
            
        Returns:
            str: Type de commentaire détecté
        """
        # ✅ PRIORITÉ 1: Si alternatives RAG disponibles → Toujours mentionner les alternatives
        if context_info.get('alternatives_disponibles', 0) > 0:
            self.logger.info(f"🔄 Alternatives RAG détectées: {context_info.get('alternatives_disponibles')} alternatives")
            return "order_with_alternatives"
        
        # Si c'est une commande complète avec quantité
        if context_info.get('quantite_demandee', 0) > 0:
            return "order"
        
        # Si stock très faible
        stock = context_info.get('stock_disponible', 0)
        if stock <= 0 or (stock < context_info.get('seuil_minimum', 10)):
            return "stock_alert"
        
        # Si problème de marge mentionné
        if 'marge_calculee' in context_info and 'marge_minimum' in context_info:
            return "margin"
        
        # Si délai mentionné
        if 'delai_livraison' in context_info or 'date_demandee' in context_info:
            return "delivery"
        
        # Si alternative mentionnée (ancienne détection)
        if 'alternative_nom' in context_info:
            return "alternative"
        
        # Sinon, commentaire produit général
        return "product"
    
    def _get_fallback_order_comment(self, commande_info: Dict[str, Any]) -> str:
        """
        Génère un commentaire de fallback en cas d'erreur LLM.
        
        Args:
            commande_info: Informations sur la commande
            
        Returns:
            str: Commentaire de fallback
        """
        stock_ok = commande_info.get('stock_suffisant', False)
        marge_ok = commande_info.get('marge_suffisante', False)
        
        if stock_ok and marge_ok:
            return "✅ Commande validée - Stock et marge conformes"
        elif not stock_ok and not marge_ok:
            return "❌ Commande refusée - Stock et marge insuffisants"
        elif not stock_ok:
            return "⚠️ Stock insuffisant - Alternative recommandée"
        else:
            return "⚠️ Marge faible - Négociation nécessaire"
    
    def debug_comment_generation(self, context_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fonction de debug pour tester la génération de commentaires.
        
        Args:
            context_info: Informations de contexte
            
        Returns:
            Dict contenant les résultats de debug
        """
        debug_result = {
            "context_received": context_info,
            "detected_type": self._detect_comment_type(context_info),
            "generated_comments": {},
            "llm_status": "OK" if self.llm else "NOK"
        }
        
        # Tester tous les types de commentaires
        comment_types = ["order", "stock_alert", "margin", "delivery", "alternative", "product"]
        
        for comment_type in comment_types:
            try:
                comment = self.generate_smart_comment(context_info, comment_type)
                debug_result["generated_comments"][comment_type] = comment
            except Exception as e:
                debug_result["generated_comments"][comment_type] = f"Erreur: {str(e)}"
        
        self.logger.info(f"🔍 Debug commentaires - Type détecté: {debug_result['detected_type']}")
        return debug_result
    
    # === GÉNÉRATION DE MAILS D'ALERTE ===
    
    def generate_commercial_alert_email(self, alerte_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Génère un mail d'alerte pour l'équipe commerciale.
        
        Args:
            alerte_info: Informations sur l'alerte
            
        Returns:
            Dict[str, str]: Dictionnaire avec 'objet' et 'corps' du mail
        """
        try:
            prompt = self.templates.get_commercial_alert_email_prompt(alerte_info)
            response = self.llm.invoke(prompt)
            email_content = response.content.strip()
            
            # Parser le contenu pour extraire objet et corps
            parsed_email = self._parse_email_content(email_content)
            
            self.logger.info(f"📧 Mail commercial généré: {parsed_email['objet'][:50]}...")
            return parsed_email
            
        except Exception as e:
            self.logger.error(f"Erreur génération mail commercial: {str(e)}")
            return self._get_fallback_commercial_email(alerte_info)
    
    def generate_stock_alert_email(self, rupture_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Génère un mail d'alerte pour rupture de stock.
        
        Args:
            rupture_info: Informations sur la rupture
            
        Returns:
            Dict[str, str]: Dictionnaire avec 'objet' et 'corps' du mail
        """
        try:
            prompt = self.templates.get_stock_shortage_email_prompt(rupture_info)
            response = self.llm.invoke(prompt)
            email_content = response.content.strip()
            
            parsed_email = self._parse_email_content(email_content)
            
            self.logger.info(f"📦 Mail rupture stock généré: {parsed_email['objet'][:50]}...")
            return parsed_email
            
        except Exception as e:
            self.logger.error(f"Erreur génération mail rupture: {str(e)}")
            return self._get_fallback_stock_email(rupture_info)
    
    def generate_margin_alert_email(self, marge_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Génère un mail d'alerte pour problème de marge.
        
        Args:
            marge_info: Informations sur la marge
            
        Returns:
            Dict[str, str]: Dictionnaire avec 'objet' et 'corps' du mail
        """
        try:
            prompt = self.templates.get_margin_alert_email_prompt(marge_info)
            response = self.llm.invoke(prompt)
            email_content = response.content.strip()
            
            parsed_email = self._parse_email_content(email_content)
            
            self.logger.info(f"💰 Mail marge généré: {parsed_email['objet'][:50]}...")
            return parsed_email
            
        except Exception as e:
            self.logger.error(f"Erreur génération mail marge: {str(e)}")
            return self._get_fallback_margin_email(marge_info)
    
    def generate_alert_email_if_needed(self, commande_info: Dict[str, Any], client_name: str = "Client") -> Optional[Dict[str, str]]:
        """
        Analyse une commande et génère automatiquement un mail d'alerte si nécessaire.
        
        Args:
            commande_info: Informations complètes sur la commande
            client_name: Nom du client
            
        Returns:
            Optional[Dict[str, str]]: Mail d'alerte si problème détecté, None sinon
        """
        try:
            # Analyser si des problèmes nécessitent une alerte
            problemes_detectes = self._detect_problems(commande_info)
            
            if not problemes_detectes['has_problems']:
                self.logger.info("✅ Aucun problème détecté - Pas de mail d'alerte nécessaire")
                return None
            
            # ✅ NOUVEAU: Enrichir avec les alternatives RAG si disponibles
            alerte_info = {**commande_info, 'nom_client': client_name}
            
            # Ajouter les alternatives RAG aux informations d'email
            if commande_info.get('alternatives_disponibles', 0) > 0:
                alerte_info['alternatives_rag_disponibles'] = True
                alerte_info['nb_alternatives_rag'] = commande_info.get('alternatives_disponibles', 0)
                alerte_info['top_alternatives'] = commande_info.get('alternatives_rag', [])[:3]
                self.logger.info(f"📧 Email avec {alerte_info['nb_alternatives_rag']} alternatives RAG")
            else:
                alerte_info['alternatives_rag_disponibles'] = False
            
            # Générer le mail selon le type de problème principal
            if problemes_detectes['rupture_stock']:
                return self.generate_stock_alert_email(alerte_info)
            elif problemes_detectes['marge_insuffisante']:
                return self.generate_margin_alert_email(alerte_info)
            else:
                # Problème général
                alerte_info['type_probleme'] = problemes_detectes['description']
                return self.generate_commercial_alert_email(alerte_info)
                
        except Exception as e:
            self.logger.error(f"Erreur analyse alerte automatique: {str(e)}")
            return None
    
    # === MÉTHODES UTILITAIRES POUR MAILS ===
    
    def _parse_email_content(self, email_content: str) -> Dict[str, str]:
        """Parse le contenu du mail généré par le LLM."""
        try:
            lines = email_content.split('\n')
            objet = ""
            corps = ""
            
            # Chercher l'objet
            for i, line in enumerate(lines):
                if line.upper().startswith('OBJET:'):
                    objet = line.replace('OBJET:', '').strip()
                    # Le corps commence après "CORPS:"
                    for j in range(i+1, len(lines)):
                        if lines[j].upper().startswith('CORPS:'):
                            corps = '\n'.join(lines[j+1:]).strip()
                            break
                    break
            
            # Fallback si parsing échoue
            if not objet or not corps:
                objet = "Alerte commande - Action requise"
                corps = email_content
            
            return {'objet': objet, 'corps': corps}
            
        except Exception as e:
            self.logger.warning(f"Erreur parsing email: {str(e)}")
            return {
                'objet': "Alerte commande - Action requise", 
                'corps': email_content
            }
    
    def _detect_problems(self, commande_info: Dict[str, Any]) -> Dict[str, Any]:
        """Détecte les problèmes dans une commande."""
        problemes = {
            'has_problems': False,
            'rupture_stock': False,
            'marge_insuffisante': False,
            'delai_problematique': False,
            'description': ""
        }
        
        # Vérifier le stock
        stock_suffisant = commande_info.get('stock_suffisant', True)
        if not stock_suffisant:
            problemes['rupture_stock'] = True
            problemes['has_problems'] = True
            problemes['description'] = "Rupture de stock"
        
        # Vérifier la marge
        marge_suffisante = commande_info.get('marge_suffisante', True)
        if not marge_suffisante:
            problemes['marge_insuffisante'] = True
            problemes['has_problems'] = True
            if problemes['description']:
                problemes['description'] += " + Marge insuffisante"
            else:
                problemes['description'] = "Marge insuffisante"
        
        return problemes
    
    def _get_fallback_commercial_email(self, alerte_info: Dict[str, Any]) -> Dict[str, str]:
        """Mail de fallback pour alerte commerciale."""
        return {
            'objet': f"🚨 ALERTE - Commande {alerte_info.get('nom_produit', 'produit')} - Action requise",
            'corps': f"""Bonjour,

Une commande nécessite votre attention immédiate :

Client : {alerte_info.get('nom_client', 'N/A')}
Produit : {alerte_info.get('nom_produit', 'N/A')} 
Quantité : {alerte_info.get('quantite_demandee', 0)}
Problème : {alerte_info.get('type_probleme', 'À analyser')}

Merci de traiter cette demande rapidement.

Assistant IA Butterfly Packaging"""
        }
    
    def _get_fallback_stock_email(self, rupture_info: Dict[str, Any]) -> Dict[str, str]:
        """Mail de fallback pour rupture stock."""
        return {
            'objet': f"📦 RUPTURE STOCK - {rupture_info.get('nom_produit', 'Produit')}",
            'corps': f"""Alerte rupture de stock :

Produit : {rupture_info.get('nom_produit', 'N/A')}
Stock disponible : {rupture_info.get('stock_disponible', 0)}
Quantité demandée : {rupture_info.get('quantite_demandee', 0)}
Client : {rupture_info.get('nom_client', 'N/A')}

Action recommandée : Contacter le client pour négocier délai ou alternative.

Assistant Stock Butterfly Packaging"""
        }
    
    def _get_fallback_margin_email(self, marge_info: Dict[str, Any]) -> Dict[str, str]:
        """Mail de fallback pour problème marge."""
        return {
            'objet': f"💰 MARGE INSUFFISANTE - {marge_info.get('nom_produit', 'Produit')}",
            'corps': f"""Alerte marge insuffisante :

Produit : {marge_info.get('nom_produit', 'N/A')}
Prix proposé : {marge_info.get('prix_propose', 0)}€
Marge calculée : {marge_info.get('marge_calculee', 0)}€
Marge minimum : {marge_info.get('marge_minimum', 0)}€
Client : {marge_info.get('nom_client', 'N/A')}

Action recommandée : Négocier le prix avec le client.

Assistant Financier Butterfly Packaging"""
        } 