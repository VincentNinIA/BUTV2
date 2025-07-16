#!/usr/bin/env python3
"""
Sélecteur d'alternatives
=======================

Module responsable de la sélection intelligente d'alternatives :
- Sélection par LLM avec prompts optimisés
- Sélection par règles de fallback
- Parsing et validation des réponses
"""

import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AlternativesSelector:
    """Sélecteur intelligent d'alternatives de produits"""
    
    def __init__(self, llm_client=None):
        """
        Initialise le sélecteur
        
        Args:
            llm_client: Client LLM optionnel pour la sélection intelligente
        """
        self.llm_client = llm_client
        
    def select_best_alternative(
        self,
        original_product: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        selection_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sélectionne la meilleure alternative via LLM ou fallback
        
        Args:
            original_product: Produit original demandé
            alternatives: Liste des alternatives disponibles
            selection_criteria: Critères de sélection prioritaires
            
        Returns:
            Dict contenant la sélection et l'analyse
        """
        if not alternatives:
            return self._no_alternatives_result()
        
        if len(alternatives) == 1:
            return self._single_alternative_result(alternatives[0])
        
        # Essayer d'abord la sélection LLM
        if self.llm_client:
            try:
                return self._llm_selection(original_product, alternatives, selection_criteria)
            except Exception as e:
                logger.warning(f"⚠️ Sélection LLM échouée, fallback sur règles : {e}")
        
        # Fallback sur la sélection par règles
        return self._rule_based_selection(original_product, alternatives)
    
    def _llm_selection(
        self,
        original_product: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        selection_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sélection intelligente par LLM"""
        prompt = self._create_selection_prompt(original_product, alternatives, selection_criteria)
        
        logger.info(f"🤖 Sélection LLM pour {len(alternatives)} alternatives")
        
        # Appel au LLM
        response = self.llm_client.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parser la réponse
        try:
            selection_result = self._parse_llm_response(response_text, alternatives)
            selection_result["method"] = "llm"
            return selection_result
        except Exception as e:
            logger.error(f"❌ Erreur parsing réponse LLM : {e}")
            # Fallback sur règles en cas d'erreur de parsing
            fallback = self._rule_based_selection(original_product, alternatives)
            fallback["llm_error"] = str(e)
            return fallback
    
    def _create_selection_prompt(
        self,
        original_product: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        selection_criteria: Optional[List[str]] = None
    ) -> str:
        """Crée le prompt pour la sélection LLM"""
        if selection_criteria is None:
            selection_criteria = ["similarité technique", "adaptabilité au contexte", "stock disponible", "marge"]
        
        prompt = f"""Vous êtes un expert commercial chez Butterfly Packaging, spécialisé dans l'analyse contextuelle des alternatives d'emballage.

**CONTEXTE DE LA DEMANDE :**
Le client demande : {original_product.get('name', 'N/A')}
- Stock disponible : {original_product.get('stock_disponible', 'N/A')} unités
- Marge actuelle : {original_product.get('marge_actuelle', 'N/A')}€
- Problème détecté : {original_product.get('probleme_detecte', 'Non spécifié')}

**VOTRE MISSION :**
Analyser INTELLIGEMMENT chaque alternative selon le contexte commercial :
- Peut-on proposer une livraison partielle si stock insuffisant ?
- Peut-on négocier le prix si marge faible mais produit adapté ?
- Y a-t-il des avantages techniques compensant les inconvénients ?

**ALTERNATIVES DISPONIBLES :**
"""
        
        for i, alt in enumerate(alternatives, 1):
            similarite = alt.get('similarite_technique', 0)
            similarite_display = f"{similarite:.1%}" if isinstance(similarite, (int, float)) else "À analyser"
            
            stock_suffisant = alt.get('stock_suffisant', False)
            marge_suffisante = alt.get('marge_suffisante', False)
            analyse_requise = alt.get('analyse_requise', False)
            
            # Indicateurs visuels
            stock_icon = "✅" if stock_suffisant else "⚠️"
            marge_icon = "✅" if marge_suffisante else "⚠️"
            analyse_icon = "🔍" if analyse_requise else "✅"
            
            prompt += f"""
{i}. **{alt.get('name', 'Produit inconnu')}** {analyse_icon}
   • Compatibilité technique : {similarite_display}
   • Stock : {stock_icon} {alt.get('stock_disponible', 'N/A')} unités (requis: {original_product.get('quantite_demandee', 'N/A')})
   • Marge : {marge_icon} {alt.get('marge', 'N/A')}€ (min: {alt.get('marge_minimum', 'N/A')}€)
   • Prix conseillé : {alt.get('prix_vente_conseille', 'N/A')}€
   • Délai livraison : {alt.get('delai', 'N/A')}
   • Description : {alt.get('description', 'Non disponible')[:100]}...
"""

        prompt += f"""
**CRITÈRES D'ANALYSE INTELLIGENTE :**
1. **Similarité technique** (40%) : Compatibilité fonctionnelle avec le besoin
2. **Adaptabilité commerciale** (30%) : Peut-on s'adapter aux contraintes (stock partiel, négociation prix) ?
3. **Avantages/inconvénients** (20%) : Bénéfices techniques compensant les problèmes ?
4. **Faisabilité** (10%) : Solution réaliste pour le client ?

**RÈGLES D'EXPERTISE :**
- ✅ Si compatibilité technique > 70% : Recommander même si contraintes mineures
- ⚠️ Si stock insuffisant mais produit parfait : Proposer livraison partielle + délai
- 💰 Si marge faible mais excellente compatibilité : Proposer négociation prix
- ❌ Si compatibilité < 30% : Rejeter même si stock/marge OK
- 🔄 Privilégier les solutions créatives aux rejets systématiques

**RÉPONSE JSON OBLIGATOIRE :**
{{
    "selected": "Nom exact du produit choisi ou null",
    "reason": "Explication détaillée du choix avec stratégie commerciale",
    "confidence": 0.8,
    "commercial_strategy": "Approche recommandée (livraison immédiate/partielle/négociation/etc.)",
    "analysis": [
        {{
            "name": "Produit 1", 
            "score": 0.85, 
            "technical_fit": "Excellente compatibilité",
            "commercial_viability": "Livraison partielle possible",
            "pros": ["Compatibilité parfaite", "Client satisfait"], 
            "cons": ["Stock partiel", "Délai 2 semaines"]
        }}
    ]
}}

**ANALYSEZ et choisissez la MEILLEURE solution commerciale :**"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str, alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse la réponse JSON du LLM"""
        # Extraire le JSON de la réponse
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("Aucun JSON trouvé dans la réponse")
        
        json_str = response_text[json_start:json_end]
        result = json.loads(json_str)
        
        # Valider et transformer le résultat
        selected_name = result.get("selected")
        
        if selected_name and selected_name.lower() != "null":
            # Trouver l'alternative correspondante
            selected_alt = None
            for alt in alternatives:
                if alt.get("name") == selected_name:
                    selected_alt = alt
                    break
            
            if selected_alt:
                return {
                    "selected": selected_alt,
                    "reason": result.get("reason", "Sélection LLM"),
                    "confidence": result.get("confidence", 0.8),
                    "analysis": result.get("analysis", []),
                    "method": "llm"
                }
        
        # Aucune sélection valide
        return {
            "selected": None,
            "reason": result.get("reason", "Aucune alternative appropriée"),
            "confidence": result.get("confidence", 0.5),
            "analysis": result.get("analysis", []),
            "method": "llm"
        }
    
    def _rule_based_selection(
        self,
        original_product: Dict[str, Any],
        alternatives: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Sélection par règles de fallback"""
        logger.info(f"🔧 Sélection par règles pour {len(alternatives)} alternatives")
        
        # Scoring des alternatives
        scored_alternatives = []
        
        for alt in alternatives:
            score = self._calculate_rule_score(alt, original_product)
            scored_alternatives.append((alt, score))
        
        # Trier par score décroissant
        scored_alternatives.sort(key=lambda x: x[1], reverse=True)
        
        if scored_alternatives and scored_alternatives[0][1] > 0:
            best_alt, best_score = scored_alternatives[0]
            return {
                "selected": best_alt,
                "reason": f"Meilleure alternative selon les règles (score: {best_score:.2f})",
                "confidence": min(best_score, 0.9),
                "method": "rules",
                "scoring": [(alt.get("name"), score) for alt, score in scored_alternatives]
            }
        
        return {
            "selected": None,
            "reason": "Aucune alternative ne satisfait les critères minimaux",
            "confidence": 0.0,
            "method": "rules"
        }
    
    def _calculate_rule_score(self, alternative: Dict[str, Any], original_product: Dict[str, Any]) -> float:
        """Calcule un score pour une alternative selon des règles"""
        score = 0.0
        
        # Score stock (30% du total)
        stock_score = min(alternative.get("stock_disponible", 0) / 100, 1.0) * 0.3
        score += stock_score
        
        # Score marge (25% du total)
        marge_actuelle = alternative.get("marge", 0)
        marge_minimum = alternative.get("marge_minimum", 0)
        if marge_minimum > 0:
            marge_ratio = marge_actuelle / marge_minimum
            marge_score = min(marge_ratio, 1.5) * 0.25  # Cap à 1.5x la marge minimum
            score += marge_score
        
        # Score similarité technique (35% du total)
        similarite = alternative.get("similarite_technique")
        if isinstance(similarite, (int, float)):
            if similarite >= 0.3:  # Seuil minimum
                tech_score = similarite * 0.35
                score += tech_score
            else:
                # Pénalité forte pour similarité trop faible
                score *= 0.1
        
        # Score délai (10% du total)
        delai = alternative.get("delai", "standard")
        if delai in ["immediate", "24h", "rapide"]:
            score += 0.1
        elif delai in ["standard", "normal"]:
            score += 0.05
        
        return score
    
    def _no_alternatives_result(self) -> Dict[str, Any]:
        """Résultat quand aucune alternative"""
        return {
            "selected": None,
            "reason": "Aucune alternative disponible",
            "confidence": 0.0,
            "method": "none"
        }
    
    def _single_alternative_result(self, alternative: Dict[str, Any]) -> Dict[str, Any]:
        """Résultat avec une seule alternative"""
        return {
            "selected": alternative,
            "reason": "Seule alternative disponible",
            "confidence": 0.8,
            "method": "single"
        }

def select_best_alternative(
    original_product: Dict[str, Any],
    alternatives: List[Dict[str, Any]],
    llm_client=None,
    selection_criteria: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Interface simplifiée pour la sélection d'alternatives
    
    Args:
        original_product: Produit original
        alternatives: Liste des alternatives
        llm_client: Client LLM optionnel
        selection_criteria: Critères de sélection
        
    Returns:
        Dict: Résultat de la sélection
    """
    selector = AlternativesSelector(llm_client)
    return selector.select_best_alternative(original_product, alternatives, selection_criteria) 