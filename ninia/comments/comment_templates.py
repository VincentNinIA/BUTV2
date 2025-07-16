"""
Templates de prompts pour la génération de commentaires intelligents
==================================================================

Ce module contient tous les templates de prompts utilisés par l'agent
de génération de commentaires selon différents contextes.
"""

from typing import Dict, Any
from datetime import datetime


class CommentTemplates:
    """Gestionnaire des templates de prompts pour commentaires."""
    
    @staticmethod
    def get_order_analysis_prompt(commande_info: Dict[str, Any]) -> str:
        """
        Template pour l'analyse d'une commande avec informations complètes.
        
        Args:
            commande_info: Dictionnaire contenant toutes les informations de la commande
            
        Returns:
            str: Prompt formaté pour le LLM
        """
        # Calculer si la commande dépend du stock à venir
        stock_magasin = commande_info.get('stock_magasin', 0)
        quantite_demandee = commande_info.get('quantite_demandee', 0)
        stock_a_recevoir = commande_info.get('stock_a_recevoir', 0)
        commandes_a_livrer = commande_info.get('commandes_a_livrer', 0)
        
        # Analyser la disponibilité du stock
        stock_magasin_net = stock_magasin - commandes_a_livrer
        depend_reappro = stock_magasin_net < quantite_demandee
        manque_unites = max(0, quantite_demandee - stock_magasin_net)
        
        # ✅ AMÉLIORATION: Messages d'analyse plus détaillés
        if depend_reappro:
            if stock_a_recevoir >= manque_unites:
                # Stock suffisant avec réapprovisionnement
                analyse_stock = f"⚠️ STOCK MAGASIN INSUFFISANT : {stock_magasin_net} disponibles vs {quantite_demandee} demandées"
                consequence = f"- Manque {manque_unites} unités - LIVRAISON DÉPEND DU RÉAPPROVISIONNEMENT ({stock_a_recevoir} en commande)"
            else:
                # Rupture même avec réapprovisionnement
                analyse_stock = f"🚨 RUPTURE TOTALE : Stock total futur insuffisant"
                consequence = f"- Stock futur: {stock_magasin_net + stock_a_recevoir} vs {quantite_demandee} demandées - RUPTURE CRITIQUE"
        else:
            analyse_stock = "✅ STOCK MAGASIN SUFFISANT pour livraison immédiate"
            consequence = "- LIVRAISON IMMÉDIATE POSSIBLE"
        
        return f"""Tu es un assistant commercial expert chez Butterfly Packaging.
Analyse cette commande et génère un commentaire professionnel en français d'UNE PHRASE qui résume l'analyse.

📦 COMMANDE ANALYSÉE :
- Produit : {commande_info.get('nom_produit', 'N/A')}
- Quantité demandée : {quantite_demandee}
- Prix proposé : {commande_info.get('prix_propose', 'N/A')}

📊 ANALYSE STOCK DÉTAILLÉE :
- Stock physique magasin : {stock_magasin}
- Stock à recevoir (réapprovisionnement) : {stock_a_recevoir}
- Commandes à livrer : {commandes_a_livrer}
- Stock net magasin : {stock_magasin_net}
- Quantité demandée : {quantite_demandee}
- Stock total disponible : {commande_info.get('stock_disponible', 0)}

🚨 ANALYSE CRITIQUE :
{analyse_stock}
{consequence}

💰 ANALYSE MARGE :
- Marge calculée : {commande_info.get('marge_calculee', 0)}€
- Marge suffisante : {commande_info.get('marge_suffisante', False)}

🚚 DÉLAI : {commande_info.get('delai_livraison', 'N/A')}

⚠️ ALERTES : {commande_info.get('alertes', 'Aucune')}

POINTS CLÉS À ANALYSER :

1. ✅ Si stock magasin net suffisant : Valider directement
2. ⚠️ Si dépend du réapprovisionnement MAIS stock total futur suffisant : 
   - MENTIONNER cette dépendance clairement
   - Préciser "Livraison dépend du réapprovisionnement" 
   - Indiquer les quantités (stock actuel vs en commande)
3. 🚨 Si rupture totale (même avec réapprovisionnement) : Expliquer le déficit
4. 💰 Situation de la marge : Signaler si problématique
5. ❌ Si impossible : Expliquer la raison principale

IMPORTANT : 
- Si la commande dépend du stock à recevoir, TOUJOURS l'indiquer dans le commentaire
- Distinguer "dépend du réapprovisionnement" (informatif) de "rupture totale" (critique)
- Être transparent sur les délais et conditions
- Utiliser un ton professionnel mais naturel

EXEMPLES DE COMMENTAIRES :
- Stock suffisant immédiat : "✅ Commande validée"
- Dépend du réapprovisionnement : "⚠️ Livraison dépend du réapprovisionnement - Stock actuel: X, En commande: Y"
- Rupture totale : "🚨 RUPTURE DE STOCK - Stock total insuffisant"

Génère UN commentaire d'analyse commercial concis et informatif (maximum 20 mots)."""

    @staticmethod
    def get_stock_alert_prompt(produit_info: Dict[str, Any]) -> str:
        """
        Template pour les alertes de stock faible.
        
        Args:
            produit_info: Informations sur le produit en rupture/stock faible
            
        Returns:
            str: Prompt formaté pour alerte stock
        """
        return f"""Tu es un assistant logistique chez Butterfly Packaging.
Génère un commentaire d'alerte de stock en français.

📦 PRODUIT EN ALERTE :
- Nom : {produit_info.get('nom_produit', 'N/A')}
- Stock actuel : {produit_info.get('stock_actuel', 0)}
- Seuil minimum : {produit_info.get('seuil_minimum', 0)}
- Délai réapprovisionnement : {produit_info.get('delai_reappro', 'N/A')}

Génère UN commentaire d'alerte concis (maximum 12 mots) format :
"ALERTE STOCK - [situation] - [action requise]"

Exemples :
- "ALERTE STOCK - Stock critique - Réapprovisionnement urgent"
- "ALERTE STOCK - Rupture imminente - Commander maintenant"
"""

    @staticmethod
    def get_margin_analysis_prompt(marge_info: Dict[str, Any]) -> str:
        """
        Template pour l'analyse des marges.
        
        Args:
            marge_info: Informations sur les marges du produit
            
        Returns:
            str: Prompt formaté pour analyse marge
        """
        return f"""Tu es un analyste financier chez Butterfly Packaging.
Analyse la rentabilité de cette vente.

💰 ANALYSE MARGE :
- Prix de vente proposé : {marge_info.get('prix_vente', 0)}€
- Prix d'achat : {marge_info.get('prix_achat', 0)}€
- Marge calculée : {marge_info.get('marge_calculee', 0)}€
- Marge minimum requise : {marge_info.get('marge_minimum', 0)}€
- Pourcentage de marge : {marge_info.get('pourcentage_marge', 0)}%

Génère UN commentaire de rentabilité (maximum 10 mots) :
- Si marge OK : "Marge acceptable - Vente rentable"
- Si marge faible : "Marge faible - Négociation recommandée"
- Si marge insuffisante : "Marge insuffisante - Vente non rentable"
"""

    @staticmethod
    def get_delivery_analysis_prompt(delai_info: Dict[str, Any]) -> str:
        """
        Template pour l'analyse des délais de livraison.
        
        Args:
            delai_info: Informations sur les délais
            
        Returns:
            str: Prompt formaté pour analyse délai
        """
        return f"""Tu es un planificateur logistique chez Butterfly Packaging.
Analyse la faisabilité des délais.

🚚 ANALYSE DÉLAI :
- Date demandée : {delai_info.get('date_demandee', 'N/A')}
- Délai standard : {delai_info.get('delai_standard', 'N/A')}
- Stock disponible : {delai_info.get('stock_disponible', False)}
- Réapprovisionnement nécessaire : {delai_info.get('reappro_necessaire', False)}

Génère UN commentaire de délai (maximum 12 mots) :
- Si délai OK : "Livraison possible dans les délais"
- Si délai serré : "Délai serré - Priorité à donner"
- Si délai impossible : "Délai impossible - Reporter livraison"
"""

    @staticmethod
    def get_alternative_suggestion_prompt(alternative_info: Dict[str, Any]) -> str:
        """
        Template pour suggérer des alternatives.
        
        Args:
            alternative_info: Informations sur les alternatives disponibles
            
        Returns:
            str: Prompt formaté pour suggestions alternatives
        """
        return f"""Tu es un conseiller commercial chez Butterfly Packaging.
Propose une alternative au client.

🔄 SITUATION :
- Produit demandé : {alternative_info.get('produit_demande', 'N/A')}
- Problème : {alternative_info.get('probleme', 'N/A')}
- Alternative proposée : {alternative_info.get('alternative_nom', 'N/A')}
- Stock alternative : {alternative_info.get('alternative_stock', 0)}

Génère UN commentaire de suggestion (maximum 15 mots) :
Format : "Alternative disponible - [nom produit] - Stock : [quantité]"

Exemple : "Alternative disponible - Caisse renforcée - Stock : 500 unités"
"""

    @staticmethod
    def get_general_product_comment_prompt(produit_info: Dict[str, Any]) -> str:
        """
        Template pour commentaire général sur un produit.
        
        Args:
            produit_info: Informations générales sur le produit
            
        Returns:
            str: Prompt formaté pour commentaire général
        """
        return f"""Tu es un expert produit chez Butterfly Packaging.
Génère un commentaire descriptif professionnel.

📦 PRODUIT :
- Nom : {produit_info.get('nom_produit', 'N/A')}
- Catégorie : {produit_info.get('categorie', 'N/A')}
- Stock : {produit_info.get('stock', 0)}
- Prix : {produit_info.get('prix', 0)}€
- Caractéristiques : {produit_info.get('caracteristiques', 'N/A')}

Génère UN commentaire produit professionnel (maximum 20 mots) qui inclut :
- Type de produit
- Stock disponible
- Prix indicatif

Format : "[Type] - Stock: [quantité] unités - Prix: [prix]€"
Exemple : "Emballage carton - Stock: 300 unités - Prix: 2,50€"
""" 

    # === TEMPLATES DE GÉNÉRATION DE MAILS D'ALERTE ===
    
    @staticmethod
    def get_commercial_alert_email_prompt(alerte_info: Dict[str, Any]) -> str:
        """
        Template pour générer un mail d'alerte au commercial.
        
        Args:
            alerte_info: Informations sur l'alerte à envoyer
            
        Returns:
            str: Prompt formaté pour génération de mail
        """
        return f"""Tu es un assistant IA chez Butterfly Packaging chargé d'alerter l'équipe commerciale.
Génère un mail d'alerte professionnel en français pour prévenir d'un problème de commande.

📧 INFORMATIONS DE L'ALERTE :
- Type de problème : {alerte_info.get('type_probleme', 'N/A')}
- Client : {alerte_info.get('nom_client', 'Client non spécifié')}
- Produit : {alerte_info.get('nom_produit', 'N/A')}
- Quantité demandée : {alerte_info.get('quantite_demandee', 0)}
- Prix proposé : {alerte_info.get('prix_propose', 'N/A')}

📊 DÉTAILS DU PROBLÈME :
- Stock magasin : {alerte_info.get('stock_magasin', 0)}
- Stock à recevoir : {alerte_info.get('stock_a_recevoir', 0)}
- Stock disponible total : {alerte_info.get('stock_disponible', 0)}
- Marge calculée : {alerte_info.get('marge_calculee', 'N/A')}€
- Marge minimum : {alerte_info.get('marge_minimum', 'N/A')}€

⚠️ URGENCE : {alerte_info.get('niveau_urgence', 'NORMALE')}

🔄 ALTERNATIVES RAG DISPONIBLES :
- Solutions trouvées par IA : {alerte_info.get('alternatives_rag_disponibles', False)}
- Nombre d'alternatives : {alerte_info.get('nb_alternatives_rag', 0)}
- Top alternatives : {alerte_info.get('top_alternatives', [])}

📋 RECOMMANDATIONS AGENT IA POUR LE COMMERCIAL :

SI alternatives disponibles, inclure OBLIGATOIREMENT ce guide :

=== GUIDE COMMERCIAL - RÉSOLUTION PROBLÈME ===
1. DIAGNOSTIC RAPIDE :
   - Identifier le problème principal (stock/marge/délai)
   - Évaluer l'urgence client
   - Prioriser les solutions alternatives

2. PLAN D'ACTION RECOMMANDÉ :
   - Alternative 1 : [Nom + Disponibilité + Pourquoi la choisir]
   - Alternative 2 : [Nom + Avantages + Arguments clients]
   - Alternative 3 : [Nom + Délais + Conditions]

3. APPROCHE CLIENT :
   - Expliquer la situation avec transparence
   - Présenter les alternatives comme amélioration
   - Négocier conditions avantageuses

Génère un mail avec :
- Objet percutant (max 60 caractères)
- Corps du message professionnel et précis
- Recommandations détaillées de l'agent IA
- Plan d'action concret pour le commercial

Format de réponse :
OBJET: [objet du mail]
CORPS:
[corps du message avec recommandations détaillées de l'agent IA]

✅ STRUCTURE OBLIGATOIRE DU MAIL :
1. Problème identifié (description précise)
2. Alternatives recommandées par l'IA (détails complets)
3. Stratégie commerciale pour chaque alternative
4. Actions immédiates et plan de contact client"""

    @staticmethod
    def get_stock_shortage_email_prompt(rupture_info: Dict[str, Any]) -> str:
        """
        Template pour mail d'alerte rupture de stock.
        
        Args:
            rupture_info: Informations sur la rupture de stock
            
        Returns:
            str: Prompt pour mail de rupture
        """
        # Calculer les données de stock correctes
        stock_magasin = rupture_info.get('stock_magasin', 0)
        stock_a_recevoir = rupture_info.get('stock_a_recevoir', 0)
        commandes_a_livrer = rupture_info.get('commandes_a_livrer', 0)
        stock_disponible = rupture_info.get('stock_disponible', 0)
        quantite_demandee = rupture_info.get('quantite_demandee', 0)
        
        # Calculer le manque réel
        manque_reel = max(0, quantite_demandee - stock_disponible)
        
        # Calculer la situation détaillée
        if stock_disponible >= quantite_demandee:
            situation_detaillee = "Stock suffisant pour livraison immédiate"
        else:
            situation_detaillee = "Stock insuffisant - Livraison partielle possible (" + str(stock_disponible) + " sur " + str(quantite_demandee) + ") ou attendre réapprovisionnement"
        
        return f"""Tu es un gestionnaire de stock chez Butterfly Packaging.
Génère un mail d'alerte pour une situation de stock problématique.

📦 SITUATION DE STOCK :
- Produit : {rupture_info.get('nom_produit', 'N/A')}
- Stock physique magasin : {stock_magasin} unités
- Stock à recevoir (réapprovisionnement) : {stock_a_recevoir} unités
- Commandes en attente de livraison : {commandes_a_livrer} unités
- Stock net disponible : {stock_disponible} unités
- Commande client demandée : {quantite_demandee} unités
- Unités manquantes : {manque_reel} unités
- Délai réapprovisionnement : {rupture_info.get('delai_livraison', 'N/A')}

👤 CLIENT CONCERNÉ :
- Nom : {rupture_info.get('nom_client', 'N/A')}
- Urgence : {rupture_info.get('urgence_commande', 'NORMALE')}

🎯 SITUATION DÉTAILLÉE :
{situation_detaillee}

🔄 ALTERNATIVES RAG DISPONIBLES :
- Alternatives trouvées : {rupture_info.get('alternatives_rag_disponibles', False)}
- Nombre d'alternatives : {rupture_info.get('nb_alternatives_rag', 0)}
- Top alternatives : {rupture_info.get('top_alternatives', [])}

📋 RECOMMANDATIONS AGENT IA POUR LE COMMERCIAL :

SI alternatives disponibles, inclure OBLIGATOIREMENT ce guide commercial :

=== GUIDE COMMERCIAL - ALTERNATIVES ===
1. SOLUTIONS IMMÉDIATES :
   - Présenter les alternatives par ordre de préférence (stock disponible d'abord)
   - Expliquer les avantages de chaque alternative vs produit original
   - Proposer adaptation tarifaire si nécessaire

2. STRATÉGIE DE NÉGOCIATION :
   - Alternative 1 : [Nom + Stock + Pourquoi la recommander]
   - Alternative 2 : [Nom + Stock + Avantages commerciaux]
   - Alternative 3 : [Nom + Stock + Arguments techniques]

3. ARGUMENTS CLIENTS :
   - Délais respectés avec stock immédiat
   - Qualité équivalente ou supérieure
   - Prix compétitif maintenu

Génère un mail d'alerte précis :
OBJET: [objet court et percutant]
CORPS:
[message professionnel avec situation exacte ET recommandations détaillées de l'agent IA]

✅ STRUCTURE OBLIGATOIRE DU MAIL :
1. Situation actuelle (chiffres exacts)
2. Alternatives recommandées par l'IA (noms, stocks, avantages)
3. Guide stratégique pour négocier avec le client
4. Actions immédiates à prendre

Important : Utiliser les chiffres exacts fournis ci-dessus, pas de valeurs approximatives !"""

    @staticmethod 
    def get_margin_alert_email_prompt(marge_info: Dict[str, Any]) -> str:
        """
        Template pour mail d'alerte marge insuffisante.
        
        Args:
            marge_info: Informations sur le problème de marge
            
        Returns:
            str: Prompt pour mail de marge
        """
        return f"""Tu es un analyste financier chez Butterfly Packaging.
Génère un mail d'alerte pour une marge insuffisante nécessitant négociation.

💰 PROBLÈME DE MARGE :
- Produit : {marge_info.get('nom_produit', 'N/A')}
- Prix proposé client : {marge_info.get('prix_propose', 0)}€
- Prix d'achat : {marge_info.get('prix_achat', 0)}€
- Marge calculée : {marge_info.get('marge_calculee', 0)}€
- Marge minimum requise : {marge_info.get('marge_minimum', 0)}€
- Déficit : {marge_info.get('deficit_marge', 0)}€

👤 CLIENT :
- Nom : {marge_info.get('nom_client', 'N/A')}
- Quantité : {marge_info.get('quantite', 0)} unités
- Valeur commande : {marge_info.get('valeur_totale', 0)}€

🔄 ALTERNATIVES RAG DISPONIBLES :
- Solutions alternatives : {marge_info.get('alternatives_rag_disponibles', False)}
- Nombre d'options : {marge_info.get('nb_alternatives_rag', 0)}
- Top alternatives : {marge_info.get('top_alternatives', [])}

📋 RECOMMANDATIONS AGENT IA POUR MARGE :

SI alternatives disponibles, inclure OBLIGATOIREMENT ce guide :

=== GUIDE COMMERCIAL - STRATÉGIES MARGE ===
1. ANALYSE FINANCIÈRE :
   - Calculer le prix minimum rentable
   - Évaluer l'impact sur la rentabilité globale
   - Proposer alternatives avec marge correcte

2. STRATÉGIES DE NÉGOCIATION :
   - Alternative 1 : [Nom + Marge + Pourquoi la recommander]
   - Alternative 2 : [Nom + Prix + Avantages économiques]
   - Option remise : [Conditions + Limites]

3. ARGUMENTS COMMERCIAUX :
   - Maintien de la qualité avec alternatives
   - Volume compensé par marge correcte
   - Partenariat long terme préservé

Génère un mail stratégique :
OBJET: [objet professionnel]
CORPS:
[analyse financière + recommandations détaillées de l'agent IA + stratégies concrètes]

✅ STRUCTURE OBLIGATOIRE DU MAIL :
1. Problème de marge (chiffres précis)
2. Alternatives recommandées par l'IA (noms, marges, avantages)
3. Stratégies de négociation concrètes
4. Prix minimum acceptable et conditions"""