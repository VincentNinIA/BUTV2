"""
Chatbot Butterfly Packaging - Version Modulaire NINIA
====================================================

Interface de chat pour interagir avec le système de RAG (Retrieval Augmented Generation).
Le chatbot utilise la nouvelle architecture modulaire NINIA avec LLM intégré.

Le chatbot permet aux utilisateurs de :
- Poser des questions sur les produits (Mode Prise de commande)
- Analyser les produits dans un tableau de commentaires (Mode Tableau)
- Commander des produits en spécifiant une quantité
- Obtenir des informations sur les stocks
- Recevoir des suggestions d'alternatives si un produit est en rupture
- Discuter de tout et de rien avec l'agent IA

Exemple d'utilisation :
    "Commande 10 caisses américaines double cannelure"
    "Quelles sont les caractéristiques des caisses Galia ?"
    "Je cherche une alternative aux étuis fourreau mousse"
    "Quel jour sommes-nous ?"
    "Comment vas-tu aujourd'hui ?"
"""

import sys, os
# ajoute la racine du projet dans le chemin des modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from ninia.agent import NiniaAgent  # Import de la nouvelle architecture modulaire
import re
from rag.retrieval import _inventory_df  # Pour accéder à la liste des produits
import unidecode  # Pour gérer les accents
from datetime import datetime, timedelta
from rag.inventory_watcher import start_inventory_watcher
import threading
from dotenv import load_dotenv
import pandas as pd
import logging
# Anciens imports supprimés - logique migrée vers l'agent modulaire
from rag.retrieval import _inventory_df, fetch_docs
from rag.optimized_search import parse_commande, search_product_by_id, get_search_stats
from rag.commande_manager import CommandeManagerAvance
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la page
st.set_page_config(
    page_title="NINIA - RAG Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS pour améliorer l'apparence
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #4CAF50, #2E7D32);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
    }
    
    .tab-container {
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
    }
    
    .user-message {
        border-left-color: #2196F3;
    }
    
    .assistant-message {
        border-left-color: #4CAF50;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background: rgba(128, 128, 128, 0.1);
        border: 2px solid rgba(128, 128, 128, 0.3);
        border-radius: 8px;
        padding: 0 20px;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(76, 175, 80, 0.2);
        border-color: #4CAF50;
        transform: translateY(-1px);
    }
    
    .stTabs [aria-selected="true"] {
        background: #4CAF50;
        color: white;
        border-color: #388e3c;
        box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
    }
    
    .bottom-section {
        padding: 2rem;
        border-radius: 10px;
        margin-top: 2rem;
        border: 1px solid rgba(128, 128, 128, 0.3);
    }
    
    .info-expander {
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Fonction pour analyser les commandes avec gestion complète des ruptures et emails IA
def analyser_commande_pour_tableau(message: str, agent: NiniaAgent, user_id: str = "IA butterfly") -> dict:
    """
    Analyse une commande avec gestion complète des ruptures de stock et emails IA automatiques.
    """
    resultats = {
        "produits_analyses": [],
        "message_confirmation": "",
        "erreurs": []
    }
    
    try:
        # Utiliser le gestionnaire de commandes avancé avec ruptures et emails
        logger.info(f"🚀 Analyse avec gestion ruptures : {message}")
        
        # Utiliser les dates sélectionnées par l'utilisateur
        date_commande = st.session_state.get('date_commande', datetime.now().date())
        date_livraison_souhaitee = st.session_state.get('date_livraison', datetime.now().date() + timedelta(days=7))
        
        # Convertir en datetime pour le gestionnaire
        date_commande_dt = datetime.combine(date_commande, datetime.min.time())
        date_livraison_dt = datetime.combine(date_livraison_souhaitee, datetime.min.time())
        
        # Analyser avec le gestionnaire avancé
        analyse_complete = commande_manager.analyser_commande_complete(
            commande_text=message,
            date_livraison_souhaitee=date_livraison_dt
        )
        
        # Traiter chaque ligne analysée
        for ligne_analysee in analyse_complete['lignes_analysees']:
            if ligne_analysee.parsing_success:
                # Calculer les informations de base
                stock_ok_initial = ligne_analysee.niveau_alerte == 'info'
                
                # Créer une ligne pour le tableau avec gestion ruptures - valeurs par défaut
                ligne_tableau = {
                    'id_commentaire': st.session_state.commentaire_counter,
                    'id_produit': ligne_analysee.id_produit,
                    'nom_produit': ligne_analysee.designation,
                    'quantite_demandee': ligne_analysee.quantite,
                    'stock_disponible': 0,
                    'stock_suffisant': '✅' if stock_ok_initial else '❌',
                    'marge_actuelle': "N/A",
                    'marge_suffisante': '✅',
                    'prix_propose': f"{ligne_analysee.prix_unitaire:.2f}€",
                    'delai_livraison': "N/A",
                    'statut_commande': '✅ OK' if stock_ok_initial else '⚠️ PROBLÈME',
                    'commentaire': ligne_analysee.commentaire_utilisateur,  # Temporaire
                    'date_creation': datetime.now().strftime("%Y-%m-%d"),
                    'heure_creation': datetime.now().strftime("%H:%M:%S"),
                    'date_commande': st.session_state.get('date_commande', datetime.now().date()).strftime("%Y-%m-%d"),
                    'date_livraison': st.session_state.get('date_livraison', datetime.now().date() + timedelta(days=7)).strftime("%Y-%m-%d"),
                    'id_utilisateur': user_id
                }
                
                # Variables pour le CommentAgent (enrichies avec les calculs de marge)
                stock_ok_final = stock_ok_initial
                marge_ok_final = True
                stock_disponible_final = 0
                marge_calculee_final = 0
                delai_final = "N/A"
                
                # Compléter avec les informations de vérification si disponibles
                if ligne_analysee.verification_rupture:
                    verif = ligne_analysee.verification_rupture
                    # Calculer le stock disponible correctement (stock + commandes achat - commandes vente)
                    stock_disponible_final = (verif.produit.quantite_stock + 
                                              verif.produit.stock_a_recevoir - 
                                              verif.produit.commandes_a_livrer)
                    
                    # Calculer la marge avec le prix proposé par le client
                    marge_calculee_final = ligne_analysee.prix_unitaire - verif.produit.prix_achat
                    
                    # Vérifier si stock et marge sont suffisants
                    stock_ok_final = stock_disponible_final >= ligne_analysee.quantite
                    marge_ok_final = marge_calculee_final >= verif.produit.marge_minimum
                    delai_final = verif.produit.delai_livraison
                    
                    ligne_tableau.update({
                        'stock_disponible': stock_disponible_final,
                        'stock_suffisant': '✅' if stock_ok_final else '❌',
                        'delai_livraison': delai_final,
                        'marge_actuelle': f"{marge_calculee_final:.2f}€",
                        'marge_suffisante': '✅' if marge_ok_final else '❌',
                        'statut_commande': '✅ OK' if (stock_ok_final and marge_ok_final) else '❌ REFUSÉ'
                    })
                
                # MAINTENANT générer le commentaire intelligent avec TOUTES les données
                commande_info_complete = {
                    'nom_produit': ligne_analysee.designation,
                    'quantite_demandee': ligne_analysee.quantite,
                    'prix_propose': ligne_analysee.prix_unitaire,
                    'stock_disponible': stock_disponible_final,
                    'stock_suffisant': stock_ok_final,
                    'marge_calculee': marge_calculee_final,
                    'marge_suffisante': marge_ok_final,
                    'delai_livraison': delai_final,
                    'alertes': 'Aucune' if (stock_ok_final and marge_ok_final) else 'Stock ou marge insuffisant'
                }
                
                # Ajouter les détails de stock si disponibles
                if ligne_analysee.verification_rupture:
                    verif = ligne_analysee.verification_rupture
                    commande_info_complete.update({
                        'stock_magasin': verif.produit.quantite_stock,
                        'stock_a_recevoir': verif.produit.stock_a_recevoir,
                        'commandes_a_livrer': verif.produit.commandes_a_livrer,
                        'prix_achat': verif.produit.prix_achat,
                        'marge_minimum': verif.produit.marge_minimum
                    })
                
                # ✅ NOUVEAU : Ajouter les alternatives RAG aux informations
                if ligne_analysee.alternatives_rag and len(ligne_analysee.alternatives_rag) > 0:
                    commande_info_complete.update({
                        'alternatives_disponibles': len(ligne_analysee.alternatives_rag),
                        'alternatives_rag': ligne_analysee.alternatives_rag[:3]  # Top 3 alternatives
                    })
                    logger.info(f"🔄 {len(ligne_analysee.alternatives_rag)} alternatives RAG disponibles pour {ligne_analysee.designation}")
                else:
                    commande_info_complete.update({
                        'alternatives_disponibles': 0,
                        'alternatives_rag': []
                    })
                
                # Générer le commentaire intelligent avec vérification de sécurité
                try:
                    # Vérifier que la méthode existe (pour éviter les erreurs de rechargement)
                    if hasattr(agent, 'generate_table_comment'):
                        # ✅ CORRECTION: Utiliser "auto" pour détecter les alternatives RAG automatiquement
                        commentaire_intelligent = agent.generate_table_comment(
                            commande_info_complete, 
                            comment_type="auto"  # Laisser le système détecter les alternatives RAG
                        )
                    else:
                        logger.warning("⚠️ generate_table_comment non disponible - Redémarrez Streamlit")
                        commentaire_intelligent = ligne_analysee.commentaire_utilisateur
                except Exception as e:
                    logger.error(f"Erreur CommentAgent pour ruptures : {str(e)}")
                    commentaire_intelligent = ligne_analysee.commentaire_utilisateur
                
                # Mettre à jour le commentaire avec la version intelligente
                ligne_tableau['commentaire'] = commentaire_intelligent
                
                # NOUVEAU : Générer automatiquement un mail d'alerte si problème détecté
                try:
                    if hasattr(agent, 'generate_alert_email_if_needed'):
                        email_alerte = agent.generate_alert_email_if_needed(
                            commande_info_complete, 
                            client_name=f"Client_{user_id}"
                        )
                        if email_alerte:
                            # Initialiser la liste des mails automatiques si elle n'existe pas
                            if "mails_automatiques" not in st.session_state:
                                st.session_state.mails_automatiques = []
                            
                            # Créer le mail d'alerte pour l'onglet Mail
                            mail_alerte = {
                                "id": len(st.session_state.mails_automatiques) + 1,
                                "type": "🚨 Alerte commande",
                                "objet": email_alerte['objet'],
                                "contenu": email_alerte['corps'],
                                "destinataire": "commercial@butterfly.com",
                                "date": datetime.now().strftime('%Y-%m-%d'),
                                "statut": "Généré automatiquement par IA"
                            }
                            
                            # Ajouter à la liste des mails automatiques
                            st.session_state.mails_automatiques.append(mail_alerte)
                            
                            # Mettre à jour le commentaire pour indiquer l'envoi d'alerte
                            ligne_tableau['commentaire'] += " | 🚨 Alerte commercial générée"
                            logger.info(f"📧 Mail d'alerte généré: {email_alerte['objet']}")
                except Exception as e:
                    logger.error(f"Erreur génération mail alerte automatique: {str(e)}")
                
                # Ajouter une note sur l'email si envoyé par le système de ruptures
                if ligne_analysee.email_envoye:
                    ligne_tableau['commentaire'] += " | 📧 Commercial alerté"
                
                resultats["produits_analyses"].append(ligne_tableau)
                st.session_state.commentaire_counter += 1
            
            else:
                # Ligne non parsée, ajouter une erreur
                resultats["erreurs"].append(f"Format non reconnu : {ligne_analysee.designation}")
        
        # Utiliser le résumé généré par le système
        resultats["message_confirmation"] = analyse_complete['resumé_commande']
        
        # Ajouter les alertes générées
        if analyse_complete['alertes_generees']:
            for alerte in analyse_complete['alertes_generees']:
                resultats["erreurs"].append(f"Alerte {alerte['type']} envoyée pour {alerte['produit']}")
        
        # Si aucune ligne valide, fallback vers l'ancienne méthode
        if not resultats["produits_analyses"]:
            logger.warning("Aucune ligne valide, essai avec l'ancienne méthode")
            
            # Utiliser la nouvelle méthode d'extraction optimisée
            product_id, quantite, prix_propose = agent._extract_product_with_fallback(message)
            
            if product_id:
                # Utiliser la nouvelle logique optimisée avec vérification par ID exact
                response = agent.process_message(message, [])
                
                # Extraire les informations du produit depuis l'inventaire
                produit_row = _inventory_df[_inventory_df['product_id'] == product_id].iloc[0] if len(_inventory_df[_inventory_df['product_id'] == product_id]) > 0 else None
                
                if produit_row is not None:
                    # Utiliser OptimizedProductSearch pour les calculs corrects
                    product_detail = agent.product_search.get_product_info(product_id)
                    
                    if product_detail:
                        # Calculer la marge avec le prix proposé par le client
                        prix_retenu = prix_propose if prix_propose else product_detail['prix_vente_conseille']
                        marge_calculee = prix_retenu - product_detail['prix_achat']
                        
                        # Créer une structure similaire à l'ancienne pour compatibilité
                        analyse_result = {
                            "status": "OK",
                            "produit": {
                                "product_id": product_id,
                                "nom": product_detail['nom'],
                                "name": product_detail['nom'],
                                "delai_livraison": product_detail['delai_livraison']
                            },
                            "analyse": {
                                "quantite_demandee": quantite,
                                "stock_disponible": product_detail['stock_disponible'],  # Stock correct avec commandes
                                "stock_suffisant": product_detail['stock_disponible'] >= quantite,
                                "marge_actuelle": marge_calculee,
                                "marge_suffisante": marge_calculee >= product_detail['marge_minimum'],
                                "prix_propose_retenu": prix_retenu
                            }
                        }
                    else:
                        analyse_result = {"status": "ERROR"}
                else:
                    analyse_result = {"status": "ERROR"}
                
                if analyse_result.get("status") != "ERROR":
                    produit_info = analyse_result.get("produit")
                    analyse_data = analyse_result.get("analyse", {})
                    
                    if produit_info:
                        # Générer le commentaire avec le nouvel agent de commentaires
                        stock_ok = analyse_data.get('stock_suffisant', False)
                        marge_ok = analyse_data.get('marge_suffisante', False)
                        
                        # Récupérer les informations détaillées du stock depuis l'agent
                        product_detail = agent.product_search.get_product_info(produit_info.get('product_id', '')) if hasattr(agent, 'product_search') else None
                        
                        # Préparer les informations pour le CommentAgent
                        commande_info = {
                            'nom_produit': produit_info.get('nom', 'N/A'),
                            'quantite_demandee': analyse_data.get('quantite_demandee', 0),
                            'stock_magasin': product_detail.get('stock_magasin', 0) if product_detail else 0,
                            'stock_a_recevoir': product_detail.get('qte_sur_commande_achat', 0) if product_detail else 0,
                            'commandes_a_livrer': product_detail.get('qte_sur_commande_vente', 0) if product_detail else 0,
                            'stock_disponible': analyse_data.get('stock_disponible', 0),
                            'stock_suffisant': stock_ok,
                            'marge_calculee': analyse_data.get('marge_actuelle', 0),
                            'marge_suffisante': marge_ok,
                            'prix_propose': analyse_data.get('prix_propose_retenu', 0),
                            'prix_achat': product_detail.get('prix_achat', 0) if product_detail else 0,
                            'marge_minimum': product_detail.get('marge_minimum', 0) if product_detail else 0,
                            'delai_livraison': produit_info.get('delai_livraison', 'N/A'),
                            'alertes': 'Aucune' if stock_ok and marge_ok else 'Stock ou marge insuffisant'
                        }
                        
                        # Utiliser le nouvel agent de commentaires modulaire avec vérification
                        try:
                            # Vérifier que la méthode existe (pour éviter les erreurs de rechargement)
                            if hasattr(agent, 'generate_table_comment'):
                                # ✅ CORRECTION: Utiliser "auto" pour détecter les alternatives RAG automatiquement
                                commentaire = agent.generate_table_comment(commande_info, comment_type="auto")
                            else:
                                logger.warning("⚠️ generate_table_comment non disponible - Redémarrez Streamlit")
                                commentaire = f"Analyse stock: {'✅ OK' if stock_ok and marge_ok else '⚠️ ATTENTION'}"
                        except Exception as e:
                            logger.error(f"Erreur CommentAgent, fallback : {str(e)}")
                            commentaire = f"Analyse stock: {'✅ OK' if stock_ok and marge_ok else '⚠️ ATTENTION'}"
                        
                        ligne_tableau = {
                            'id_commentaire': st.session_state.commentaire_counter,
                            'id_produit': produit_info.get('product_id', product_id),
                            'nom_produit': produit_info.get('nom', produit_info.get('name', product_id)),
                            'quantite_demandee': analyse_data.get('quantite_demandee', quantite),
                            'stock_disponible': analyse_data.get('stock_disponible', 0),
                            'stock_suffisant': '✅' if stock_ok else '❌',
                            'marge_actuelle': f"{analyse_data.get('marge_actuelle', 0):.2f}€",
                            'marge_suffisante': '✅' if marge_ok else '❌',
                            'prix_propose': f"{analyse_data.get('prix_propose_retenu', 0):.2f}€" if analyse_data.get('prix_propose_retenu') else "N/A",
                            'delai_livraison': produit_info.get('delai_livraison', 'N/A'),
                            'statut_commande': '✅ OK' if (stock_ok and marge_ok) else '⚠️ ATTENTION',
                            'commentaire': commentaire,
                            'date_creation': datetime.now().strftime("%Y-%m-%d"),
                            'heure_creation': datetime.now().strftime("%H:%M:%S"),
                            'id_utilisateur': user_id
                        }
                        
                        resultats["produits_analyses"].append(ligne_tableau)
                        st.session_state.commentaire_counter += 1
                        resultats["message_confirmation"] = f"✅ Analyse fallback réussie ! 1 produit ajouté."
            
            if not resultats["produits_analyses"]:
                resultats["message_confirmation"] = "❓ Aucun produit identifié. Format supporté : '76000 00420000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€'"
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse avec ruptures : {str(e)}")
        resultats["erreurs"].append(f"Erreur système : {str(e)}")
    
    return resultats

# Fonction pour ajouter les produits analysés au tableau
def ajouter_au_tableau(produits_analyses):
    """
    Ajoute les produits analysés au DataFrame du tableau.
    """
    for produit in produits_analyses:
        nouveau_df = pd.DataFrame([produit])
        st.session_state.df_commentaires = pd.concat(
            [st.session_state.df_commentaires, nouveau_df], 
            ignore_index=True
        )

# Chargement des variables d'environnement
load_dotenv()

# Configuration de page déjà définie plus haut

# Titre principal
st.title("Cliclick : Agent IA pour Butterfly Packaging")

# Initialisation de l'agent avec la nouvelle architecture
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("⚠️ La clé API OpenAI n'est pas configurée. Veuillez définir OPENAI_API_KEY dans le fichier .env")
    st.stop()

try:
    agent = NiniaAgent(api_key=api_key)
    
    # Vérifier que le nouveau CommentAgent est disponible
    if hasattr(agent, 'generate_table_comment'):
        st.success("✅ Agent NINIA initialisé avec succès ! (Module commentaires inclus)")
    else:
        st.warning("⚠️ Agent NINIA initialisé mais module commentaires manquant - Redémarrez l'application")
        st.info("💡 Pressez Ctrl+C dans le terminal puis relancez : `streamlit run app_streamlit/chatbot_ninia.py`")
    
    # Initialiser le gestionnaire de commandes avancé avec gestion des ruptures
    commande_manager = CommandeManagerAvance()
    st.success("✅ Gestionnaire de ruptures initialisé avec IA email !")
    
except Exception as e:
    st.error(f"❌ Erreur lors de l'initialisation de l'agent : {str(e)}")
    st.error("Veuillez vérifier votre connexion internet et la validité de votre clé API.")
    st.stop()

# Gestion du thread de surveillance d'inventaire
if not hasattr(st.session_state, 'inventory_watcher_started'):
    try:
        inventory_watcher_thread = threading.Thread(target=start_inventory_watcher, daemon=True)
        inventory_watcher_thread.start()
        st.session_state.inventory_watcher_started = True
        st.session_state.inventory_watcher_thread = inventory_watcher_thread
        print("Surveillance de l'inventaire démarrée (première initialisation)")
    except Exception as e:
        st.error(f"Erreur lors du démarrage de la surveillance de l'inventaire : {str(e)}")
        print(f"Erreur détaillée : {str(e)}")
        st.session_state.inventory_watcher_started = False

# Initialisation de l'historique de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialisation du DataFrame pour les commentaires
if "df_commentaires" not in st.session_state:
    st.session_state.df_commentaires = pd.DataFrame(columns=[
        'id_commentaire', 'id_produit', 'nom_produit', 'quantite_demandee', 
        'stock_disponible', 'stock_suffisant', 'marge_actuelle', 'marge_suffisante',
        'prix_propose', 'delai_livraison', 'statut_commande', 'commentaire', 
        'date_creation', 'heure_creation', 'id_utilisateur'
    ])

# Initialisation du compteur d'ID
if "commentaire_counter" not in st.session_state:
    st.session_state.commentaire_counter = 1

# Initialisation du DataFrame pour les mails
if "df_mails" not in st.session_state:
    st.session_state.df_mails = pd.DataFrame(columns=[
        'id_mail', 'destinataire', 'objet', 'corps_message', 'type_mail',
        'date_creation', 'heure_creation', 'date_envoi_prevue', 'statut', 'id_utilisateur'
    ])

# Initialisation du compteur d'ID mails
if "mail_counter" not in st.session_state:
    st.session_state.mail_counter = 1

# Sidebar réduite au minimum (pas de contenu visible)

# Création des onglets
tab_chat, tab_tableau, tab_mail = st.tabs(["🛒 Prise de commande", "📋 Mode Tableau", "📧 Mode Mail"])

# ==================== ONGLET PRISE DE COMMANDE ====================
with tab_chat:
    st.header("🛒 Prise de Commande Butterfly Packaging")
    st.markdown("**Passez vos commandes en toute simplicité avec l'agent IA NINIA**")
    
    # Statistiques du catalogue
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.metric("📊 Catalogue", f"{len(_inventory_df)}" if _inventory_df is not None else "0")
    
    st.markdown("---")
    
    # Section des dates de commande et livraison
    st.subheader("📅 Dates de Commande")
    
    # Initialisation des dates dans session_state si pas encore définies
    if "date_commande" not in st.session_state:
        st.session_state.date_commande = datetime.now().date()
    if "date_livraison" not in st.session_state:
        st.session_state.date_livraison = (datetime.now() + timedelta(days=7)).date()
    
    # Boutons pour fixer les dates
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**📋 Date de Commande**")
        date_commande = st.date_input(
            "Sélectionnez la date de commande",
            value=st.session_state.date_commande,
            key="date_commande_input"
        )
        if date_commande != st.session_state.date_commande:
            st.session_state.date_commande = date_commande
            st.success(f"✅ Date de commande fixée au {date_commande.strftime('%d/%m/%Y')}")
    
    with col2:
        st.markdown("**🚚 Date de Livraison**")
        date_livraison = st.date_input(
            "Sélectionnez la date de livraison souhaitée",
            value=st.session_state.date_livraison,
            min_value=datetime.now().date(),
            key="date_livraison_input"
        )
        if date_livraison != st.session_state.date_livraison:
            st.session_state.date_livraison = date_livraison
            st.success(f"✅ Date de livraison fixée au {date_livraison.strftime('%d/%m/%Y')}")
    
    # Affichage des dates sélectionnées
    col1, col2 = st.columns([1, 1])
    with col1:
        st.info(f"📋 **Date de commande** : {st.session_state.date_commande.strftime('%d/%m/%Y')}")
    with col2:
        st.info(f"🚚 **Date de livraison** : {st.session_state.date_livraison.strftime('%d/%m/%Y')}")
    
    st.markdown("---")
    st.info("💡 **Nouveau système optimisé** : Supportez le format ID précis (ex: '76000 00420000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€') ou les commandes textuelles classiques.")
    
    ### Prise de commande :

    # Affichage de l'historique des messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Zone de saisie du message
    if prompt := st.chat_input("Tapez votre commande ici... (ex: 'Je veux commander 200 Film machine Polytech 9 µm' ou '76000 00420000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€')"):
        # Ajout du message utilisateur à l'historique
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Affichage du message utilisateur
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Traitement de la commande
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyse de votre commande en cours..."):
                try:
                    # Analyser la commande pour le tableau
                    resultat_analyse = analyser_commande_pour_tableau(prompt, agent)
                    
                    # Ajouter les produits analysés au tableau
                    if resultat_analyse["produits_analyses"]:
                        ajouter_au_tableau(resultat_analyse["produits_analyses"])
                    
                    # Afficher le message de confirmation
                    if resultat_analyse["message_confirmation"]:
                        st.markdown(resultat_analyse["message_confirmation"])
                        response = resultat_analyse["message_confirmation"]
                    
                    # Afficher les erreurs s'il y en a
                    if resultat_analyse["erreurs"]:
                        for erreur in resultat_analyse["erreurs"]:
                            st.error(f"❌ {erreur}")
                        response = "❌ Erreur lors de l'analyse de la commande."
                    
                    # Si aucun produit analysé et pas d'erreur, traiter comme question générale
                    if not resultat_analyse["produits_analyses"] and not resultat_analyse["erreurs"]:
                        response = agent.process_message(prompt, [])
                    
                    st.markdown(response)
                        
                except Exception as e:
                    error_message = f"❌ Désolé, une erreur s'est produite : {str(e)}"
                    st.error(error_message)
                    response = error_message
                
            # Ajout de la réponse à l'historique
            st.session_state.messages.append({"role": "assistant", "content": response})

    # Bouton pour effacer l'historique en dessous du chat
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🗑️ Effacer l'historique", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()

# ==================== ONGLET TABLEAU ====================
with tab_tableau:
    st.header("📋 Feuille de Commentaires")
    st.markdown("**Tableau d'analyse automatique des produits par l'IA**")
    
    # Vérification de la disponibilité de l'inventaire
    if _inventory_df is None or _inventory_df.empty:
        st.error("❌ Aucun inventaire disponible. Veuillez vérifier le fichier data/Articles.xlsx")
    else:
        # Contrôles principaux
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            user_id = st.text_input("👤 ID Utilisateur", value="user_001", key="user_input_tableau")
        
        with col2:
            if st.button("🤖 Générer analyse complète", key="generate_sheet", type="primary"):
                if user_id:
                    # Vider le tableau existant
                    st.session_state.df_commentaires = pd.DataFrame(columns=[
                        'id_commentaire', 'id_produit', 'nom_produit', 'quantite_demandee', 
                        'stock_disponible', 'stock_suffisant', 'marge_actuelle', 'marge_suffisante',
                        'prix_propose', 'delai_livraison', 'statut_commande', 'commentaire', 
                        'date_creation', 'heure_creation', 'date_commande', 'date_livraison', 'id_utilisateur'
                    ])
                    st.session_state.commentaire_counter = 1
                    
                    with st.spinner("🔍 Génération de l'analyse complète par l'IA..."):
                        try:
                            produits_disponibles = _inventory_df['nom'].tolist()
                            progress_bar = st.progress(0)
                            total_produits = len(produits_disponibles)
                            
                            for i, produit in enumerate(produits_disponibles):
                                # Mise à jour de la barre de progression
                                progress_bar.progress((i + 1) / total_produits)
                                
                                # Récupération des informations du produit
                                produit_info = _inventory_df[_inventory_df['nom'] == produit].iloc[0]
                                
                                # Analyse du produit
                                nouveau_commentaire = {
                                    'id_commentaire': st.session_state.commentaire_counter,
                                    'id_produit': produit_info.get('product_id', f"PROD_{st.session_state.commentaire_counter}"),
                                    'nom_produit': produit,
                                    'quantite_demandee': 0,
                                    'stock_disponible': produit_info.get('quantite_stock', 0),
                                    'stock_suffisant': '✅' if produit_info.get('quantite_stock', 0) > 0 else '❌',
                                    'marge_actuelle': f"{produit_info.get('prix_vente_conseille', 0) - produit_info.get('prix_achat', 0):.2f}€",
                                    'marge_suffisante': '✅' if (produit_info.get('prix_vente_conseille', 0) - produit_info.get('prix_achat', 0)) >= produit_info.get('marge_minimum', 0) else '❌',
                                    'prix_propose': f"{produit_info.get('prix_vente_conseille', 0):.2f}€",
                                    'delai_livraison': produit_info.get('delai_livraison', 'N/A'),
                                    'statut_commande': '✅ DISPONIBLE' if produit_info.get('quantite_stock', 0) > 0 else '❌ RUPTURE',
                                    'commentaire': f"Produit d'emballage - Stock: {produit_info.get('quantite_stock', 0)} unités, Prix: {produit_info.get('prix_vente_conseille', 0):.2f}€",
                                    'date_creation': datetime.now().strftime("%Y-%m-%d"),
                                    'heure_creation': datetime.now().strftime("%H:%M:%S"),
                                    'date_commande': st.session_state.get('date_commande', datetime.now().date()).strftime("%Y-%m-%d"),
                                    'date_livraison': st.session_state.get('date_livraison', datetime.now().date() + timedelta(days=7)).strftime("%Y-%m-%d"),
                                    'id_utilisateur': user_id
                                }
                                
                                # Conversion en DataFrame et concaténation
                                nouveau_df = pd.DataFrame([nouveau_commentaire])
                                st.session_state.df_commentaires = pd.concat(
                                    [st.session_state.df_commentaires, nouveau_df], 
                                    ignore_index=True
                                )
                                st.session_state.commentaire_counter += 1
                            
                            progress_bar.empty()
                            st.success(f"✅ Analyse complète générée avec {total_produits} produits !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la génération : {str(e)}")
                else:
                    st.error("❌ Veuillez saisir un ID utilisateur.")
        
        with col3:
            if st.button("🗑️ Vider", key="clear_table_tableau"):
                st.session_state.df_commentaires = pd.DataFrame(columns=[
                    'id_commentaire', 'id_produit', 'nom_produit', 'quantite_demandee', 
                    'stock_disponible', 'stock_suffisant', 'marge_actuelle', 'marge_suffisante',
                    'prix_propose', 'delai_livraison', 'statut_commande', 'commentaire', 
                    'date_creation', 'heure_creation', 'date_commande', 'date_livraison', 'id_utilisateur'
                ])
                st.session_state.commentaire_counter = 1
                st.success("✅ Tableau vidé !")
                st.rerun()
        
        # Séparateur
        st.markdown("---")
        
        # Affichage du tableau principal
        st.subheader("📊 Analyses des Commandes")
        
        if st.session_state.df_commentaires.empty:
            # Tableau vierge avec structure visible
            st.info("📝 **Tableau vierge** - Envoyez des commandes dans l'onglet '🛒 Prise de commande' pour voir les analyses automatiques ici.")
            
            # Affichage de la structure du tableau vide
            tableau_vide = pd.DataFrame(columns=[
                'id_commentaire', 'id_produit', 'nom_produit', 'quantite_demandee', 
                'stock_disponible', 'stock_suffisant', 'marge_actuelle', 'marge_suffisante',
                'prix_propose', 'delai_livraison', 'statut_commande', 'commentaire', 
                'date_creation', 'heure_creation', 'date_commande', 'date_livraison', 'id_utilisateur'
            ])
            
            st.dataframe(
                tableau_vide,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id_commentaire": st.column_config.NumberColumn("ID", width="small"),
                    "id_produit": st.column_config.TextColumn("ID Produit", width="small"),
                    "nom_produit": st.column_config.TextColumn("Nom du Produit", width="medium"),
                    "quantite_demandee": st.column_config.NumberColumn("Qté Demandée", width="small"),
                    "stock_disponible": st.column_config.NumberColumn("Stock Dispo", width="small"),
                    "stock_suffisant": st.column_config.TextColumn("Stock OK", width="small"),
                    "marge_actuelle": st.column_config.TextColumn("Marge", width="small"),
                    "marge_suffisante": st.column_config.TextColumn("Marge OK", width="small"),
                    "prix_propose": st.column_config.TextColumn("Prix", width="small"),
                    "delai_livraison": st.column_config.TextColumn("Délai", width="small"),
                    "statut_commande": st.column_config.TextColumn("Statut", width="medium"),
                    "commentaire": st.column_config.TextColumn("Commentaire", width="large"),
                    "date_creation": st.column_config.DateColumn("Date", width="small"),
                    "heure_creation": st.column_config.TimeColumn("Heure", width="small"),
                    "date_commande": st.column_config.DateColumn("Date Commande", width="small"),
                    "date_livraison": st.column_config.DateColumn("Date Livraison", width="small"),
                    "id_utilisateur": st.column_config.TextColumn("Utilisateur", width="small")
                }
            )
            
        else:
            # Tableau rempli avec données
            st.dataframe(
                st.session_state.df_commentaires,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id_commentaire": st.column_config.NumberColumn("ID", width="small"),
                    "id_produit": st.column_config.TextColumn("ID Produit", width="small"),
                    "nom_produit": st.column_config.TextColumn("Nom du Produit", width="medium"),
                    "quantite_demandee": st.column_config.NumberColumn("Qté Demandée", width="small"),
                    "stock_disponible": st.column_config.NumberColumn("Stock Dispo", width="small"),
                    "stock_suffisant": st.column_config.TextColumn("Stock OK", width="small"),
                    "marge_actuelle": st.column_config.TextColumn("Marge", width="small"),
                    "marge_suffisante": st.column_config.TextColumn("Marge OK", width="small"),
                    "prix_propose": st.column_config.TextColumn("Prix", width="small"),
                    "delai_livraison": st.column_config.TextColumn("Délai", width="small"),
                    "statut_commande": st.column_config.TextColumn("Statut", width="medium"),
                    "commentaire": st.column_config.TextColumn("Commentaire", width="large"),
                    "date_creation": st.column_config.DateColumn("Date", width="small"),
                    "heure_creation": st.column_config.TimeColumn("Heure", width="small"),
                    "date_commande": st.column_config.DateColumn("Date Commande", width="small"),
                    "date_livraison": st.column_config.DateColumn("Date Livraison", width="small"),
                    "id_utilisateur": st.column_config.TextColumn("Utilisateur", width="small")
                }
            )
            
            # Actions sur le tableau rempli
            st.markdown("### 📊 Actions")
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # Export CSV
                csv_data = st.session_state.df_commentaires.to_csv(index=False)
                st.download_button(
                    label="📥 Télécharger CSV",
                    data=csv_data,
                    file_name=f"analyses_commandes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="download_csv_tableau"
                )
            
            with col2:
                st.metric("📝 Total analyses", len(st.session_state.df_commentaires))
            
            with col3:
                if len(st.session_state.df_commentaires) > 0:
                    utilisateurs_uniques = st.session_state.df_commentaires['id_utilisateur'].nunique()
                    st.metric("👥 Utilisateurs", utilisateurs_uniques)

# ==================== ONGLET MAIL ====================
with tab_mail:
    st.header("📧 Boîte Mail")
    
    # Initialisation d'une liste vide de mails (pas de mails d'exemple)
    if "mails_automatiques" not in st.session_state:
        st.session_state.mails_automatiques = []
    
    # Affichage simple des mails reçus
    if st.session_state.mails_automatiques:
        st.subheader(f"📨 Vous avez {len(st.session_state.mails_automatiques)} message(s)")
        
        for mail in st.session_state.mails_automatiques:
            # Affichage simple adapté au mode sombre
            with st.expander(f"📧 {mail['objet']}", expanded=False):
                st.write(f"**De :** {mail.get('expediteur', 'Système IA')}")
                st.write(f"**À :** {mail.get('destinataire', 'Vous')}")
                st.write(f"**Date :** {mail.get('date', 'Aujourd\'hui')}")
                st.write(f"**Type :** {mail.get('type', 'Message')}")
                st.markdown("---")
                st.write("**Message :**")
                st.write(mail.get('contenu', ''))
    else:
        # Interface vide et simple
        st.info("📭 Aucun nouveau message")
        st.write("Les mails générés automatiquement par l'IA apparaîtront ici.")
    
    # Actions simples
    if st.session_state.mails_automatiques:
        st.markdown("---")
        if st.button("🗑️ Supprimer tous les mails", key="clear_all_mails"):
            st.session_state.mails_automatiques = []
            st.success("✅ Tous les mails ont été supprimés")
            st.rerun()

# ==================== INFORMATIONS ET STATISTIQUES ====================
st.markdown("---")
st.markdown('<div class="bottom-section">', unsafe_allow_html=True)
st.header("ℹ️ Informations et Statistiques")

# Section informations sur les modes
with st.expander("📖 Guide d'utilisation des modes", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🛒 Prise de commande**
        - 📦 **Commandes** : "Je veux commander 10 caisses américaines"
        - 📊 **Stock** : "Quel est le stock des films étirables ?"
        - 🔄 **Alternatives** : "Alternative aux caisses Galia"
        - 💬 **Questions produits** : "Caractéristiques des films étirables"
        """)
    
    with col2:
        st.markdown("""
        **📋 Mode Tableau**
        - 🔍 **Analyse automatique** : Commentaires IA sur les produits
        - 📊 **Export CSV** : Téléchargement des données
        - 📈 **Suivi des commandes** : Historique détaillé
        """)
    
    with col3:
        st.markdown("""
        **📧 Mode Mail**
        - 📧 **Génération automatique** : Mails créés par l'IA
        - 📋 **Boîte d'envoi** : Visualisation des mails préparés
        - 📤 **Export** : Sauvegarde des mails
        """)

# Statistiques globales
st.subheader("📊 Statistiques Globales")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if _inventory_df is not None:
        st.metric("📦 Produits disponibles", len(_inventory_df), help="Nombre total de produits dans l'inventaire")
    else:
        st.metric("📦 Produits disponibles", "0", help="Inventaire non chargé")

with col2:
    if not st.session_state.df_commentaires.empty:
        st.metric("📝 Total commentaires", len(st.session_state.df_commentaires), help="Nombre d'analyses dans le tableau")
    else:
        st.metric("📝 Total commentaires", "0", help="Aucune analyse dans le tableau")

with col3:
    if not st.session_state.df_commentaires.empty:
        utilisateurs_uniques = st.session_state.df_commentaires['id_utilisateur'].nunique()
        st.metric("🆔 Utilisateurs uniques", utilisateurs_uniques, help="Nombre d'utilisateurs différents")
    else:
        st.metric("🆔 Utilisateurs uniques", "0", help="Aucun utilisateur dans le tableau")

with col4:
    if "mails_automatiques" in st.session_state and st.session_state.mails_automatiques:
        st.metric("📨 Total mails", len(st.session_state.mails_automatiques), help="Mails générés par l'IA")
    else:
        st.metric("📨 Total mails", "0", help="Aucun mail généré")

with col5:
    # Compter les alertes critiques
    if "mails_automatiques" in st.session_state and st.session_state.mails_automatiques:
        alertes_critiques = len([mail for mail in st.session_state.mails_automatiques if mail['type'].startswith('🚨')])
        delta_color = "inverse" if alertes_critiques > 0 else "normal"
        st.metric("🚨 Alertes critiques", alertes_critiques, 
                 delta=f"+{alertes_critiques}" if alertes_critiques > 0 else None,
                 help="Mails d'alerte générés automatiquement")
    else:
        st.metric("🚨 Alertes critiques", "0", help="Aucune alerte générée")

# Statistiques détaillées par mode
if not st.session_state.df_commentaires.empty or ("mails_automatiques" in st.session_state and st.session_state.mails_automatiques):
    st.subheader("📈 Statistiques Détaillées")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.df_commentaires.empty:
            st.markdown("**📋 Analyses du Tableau**")
            statuts = st.session_state.df_commentaires['statut_commande'].value_counts()
            for statut, count in statuts.items():
                st.write(f"• {statut}: {count}")
    
    with col2:
        if "mails_automatiques" in st.session_state and st.session_state.mails_automatiques:
            st.markdown("**📧 Types de Mails**")
            types_mails = {}
            for mail in st.session_state.mails_automatiques:
                type_mail = mail.get('type', 'Non défini')
                types_mails[type_mail] = types_mails.get(type_mail, 0) + 1
            for type_mail, count in types_mails.items():
                st.write(f"• {type_mail}: {count}")

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🦋 <strong>NINIA</strong> - Assistant IA Butterfly Packaging</p>
    <p>Version modulaire avec Prise de commande, Tableau et Mail</p>
    <p style='font-size: 0.8em; margin-top: 10px;'>Interface optimisée pour une expérience client fluide</p>
</div>
""", unsafe_allow_html=True) 