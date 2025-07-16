#!/usr/bin/env python3
"""
Gestionnaire de commandes intégré avec gestion automatique des ruptures de stock
Combine le parser optimisé avec le système de ruptures et l'email manager IA
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .optimized_search import OptimizedProductSearch, CommandeParser
from .gestionnaire_stock import GestionnaireStock, ResultatVerification
from .email_manager import EmailAIManager, ConfigurationEmail
from .settings import settings

logger = logging.getLogger(__name__)

@dataclass
class LigneCommandeAnalysee:
    """Une ligne de commande avec analyse complète des ruptures"""
    # Informations de parsing
    id_produit: str
    designation: str
    quantite: int
    prix_unitaire: float
    prix_total: float
    parsing_success: bool
    
    # Informations produit
    product_found: bool
    product_info: Optional[Dict] = None
    
    # Analyse de rupture
    verification_rupture: Optional[ResultatVerification] = None
    
    # NOUVEAU : Alternatives du RAG
    alternatives_rag: List[Dict] = None
    
    def __post_init__(self):
        if self.alternatives_rag is None:
            self.alternatives_rag = []
    
    # Actions entreprises
    email_envoye: bool = False
    details_email: Optional[Dict] = None
    
    # Commentaires pour l'utilisateur
    commentaire_utilisateur: str = ""
    niveau_alerte: str = "info"  # info, warning, error

class CommandeManagerAvance:
    """Gestionnaire de commandes avancé avec gestion automatique des ruptures"""
    
    def __init__(self, excel_file_path: str = "data/Articles.xlsx"):
        """
        Initialise le gestionnaire de commandes avancé
        
        Args:
            excel_file_path: Chemin vers le fichier Excel des articles (source unique de données)
        """
        # Initialiser les composants avec la même source de données
        self.search_engine = OptimizedProductSearch(excel_file_path)
        self.parser_commande = CommandeParser(self.search_engine)
        self.gestionnaire_stock = GestionnaireStock(excel_file_path)
        
        # Initialiser l'email manager si configuré
        self.email_manager = None
        self._init_email_manager()
        
        logger.info("✅ CommandeManagerAvance initialisé avec source unique: Articles.xlsx")
    
    def _init_email_manager(self):
        """Initialise l'email manager si la configuration est disponible"""
        try:
            if settings.email_actif and settings.email_expediteur and settings.email_commercial:
                config_email = ConfigurationEmail(
                    email_expediteur=settings.email_expediteur,
                    mot_de_passe_expediteur=settings.email_mot_de_passe,
                    email_commercial=settings.email_commercial,
                    nom_commercial=settings.nom_commercial,
                    nom_entreprise=settings.nom_entreprise,
                    smtp_server=settings.smtp_server,
                    smtp_port=settings.smtp_port
                )
                
                self.email_manager = EmailAIManager(config_email)
                logger.info("✅ Email manager configuré et activé")
            else:
                logger.info("ℹ️ Email manager désactivé (configuration incomplète)")
                
        except Exception as e:
            logger.warning(f"⚠️ Email manager non disponible: {str(e)}")
    
    def analyser_ligne_commande_complete(self, 
                                       ligne: str,
                                       date_commande: Optional[datetime] = None,
                                       date_livraison_souhaitee: Optional[datetime] = None) -> LigneCommandeAnalysee:
        """
        Analyse complète d'une ligne de commande avec gestion des ruptures
        
        Args:
            ligne: Ligne de commande à analyser
            date_commande: Date de la commande (défaut: aujourd'hui)
            date_livraison_souhaitee: Date de livraison souhaitée par le client
            
        Returns:
            LigneCommandeAnalysee avec toutes les informations et actions entreprises
        """
        if date_commande is None:
            date_commande = datetime.now()
        
        # Étape 1: Parser la ligne avec le système existant
        parsing_result = self.parser_commande.parse_ligne_commande(ligne)
        
        if not parsing_result['parsing_success']:
            return LigneCommandeAnalysee(
                id_produit="",
                designation="",
                quantite=0,
                prix_unitaire=0.0,
                prix_total=0.0,
                parsing_success=False,
                product_found=False,
                commentaire_utilisateur=f"❌ {parsing_result.get('erreur', 'Format non reconnu')}",
                niveau_alerte="error"
            )
        
        # Étape 2: Créer l'objet de base
        ligne_analysee = LigneCommandeAnalysee(
            id_produit=parsing_result['id_produit'],
            designation=parsing_result['designation'],
            quantite=parsing_result['quantite'],
            prix_unitaire=parsing_result['prix_unitaire'],
            prix_total=parsing_result['prix_total'],
            parsing_success=True,
            product_found=parsing_result['product_found'],
            product_info=parsing_result.get('product_info')
        )
        
        # Étape 3: Si produit non trouvé, pas besoin d'analyser les ruptures
        if not parsing_result['product_found']:
            ligne_analysee.commentaire_utilisateur = f"❌ Produit {ligne_analysee.id_produit} inexistant"
            ligne_analysee.niveau_alerte = "error"
            
            # Envoyer email pour produit inexistant si configuré
            if self.email_manager:
                ligne_analysee.email_envoye, ligne_analysee.details_email = self._traiter_alerte_email_produit_inexistant(
                    ligne_analysee, date_commande
                )
            
            return ligne_analysee
        
        # Étape 4: Analyser les ruptures avec le gestionnaire de stock
        try:
            verification = self.gestionnaire_stock.verifier_produit(
                product_id=ligne_analysee.id_produit,
                quantite_demandee=ligne_analysee.quantite,
                date_commande=date_commande,
                date_livraison_souhaitee=date_livraison_souhaitee
            )
            
            ligne_analysee.verification_rupture = verification
            
            # Étape 5: Générer commentaire utilisateur basé sur la vérification
            ligne_analysee.commentaire_utilisateur = self._generer_commentaire_utilisateur(verification)
            ligne_analysee.niveau_alerte = verification.niveau_alerte
            
            # Étape 6: NOUVEAU - Récupérer les alternatives du RAG si problème détecté
            alternatives_rag = []
            
            # ✅ AMÉLIORATION: Logique plus fine pour le déclenchement du RAG
            # Ne déclencher le RAG que si c'est vraiment nécessaire
            declencher_rag = False
            
            if verification.type_disponibilite == 'rupture':
                # Rupture totale -> RAG nécessaire
                declencher_rag = True
                logger.info(f"🚨 RAG déclenché: Rupture totale pour {ligne_analysee.id_produit}")
                
            elif verification.type_disponibilite == 'avec_commande':
                # Stock avec réapprovisionnement -> Analyser plus finement
                if verification.necessite_alerte_commercial:
                    # Délai dépassé ou autre problème -> RAG nécessaire
                    declencher_rag = True
                    logger.info(f"⚠️ RAG déclenché: Délai dépassé pour {ligne_analysee.id_produit}")
                else:
                    # Stock suffisant avec réapprovisionnement dans les délais -> RAG inutile
                    declencher_rag = False
                    logger.info(f"✅ RAG non déclenché: Stock suffisant avec réapprovisionnement pour {ligne_analysee.id_produit}")
                    
            elif verification.niveau_alerte == 'error':
                # Autres erreurs critiques -> RAG nécessaire
                declencher_rag = True
                logger.info(f"❌ RAG déclenché: Erreur critique pour {ligne_analysee.id_produit}")
            
            # Déclencher le RAG seulement si nécessaire
            if declencher_rag:
                try:
                    # Utiliser la version optimisée pour récupérer les alternatives
                    from .retrieval_optimized import fetch_docs_optimized
                    
                    # Utiliser le nom du produit trouvé (pas l'ID de commande)
                    product_name = ligne_analysee.product_info.get('nom', ligne_analysee.designation) if ligne_analysee.product_info else ligne_analysee.designation
                    
                    rag_result = fetch_docs_optimized(
                        query=f"Alternative pour {product_name}",
                        product_id=product_name,  # Passer le nom du produit, pas l'ID de commande
                        required_qty=ligne_analysee.quantite,
                        prix_propose=ligne_analysee.prix_unitaire
                    )
                    
                    if rag_result and rag_result.get('alternatives'):
                        alternatives_rag = rag_result['alternatives']
                        logger.info(f"🔍 RAG: {len(alternatives_rag)} alternatives trouvées pour {ligne_analysee.id_produit}")
                        
                        # ✅ AMÉLIORATION: Ajouter les alternatives au commentaire (max 4 proposées)
                        if alternatives_rag:
                            nb_proposees = min(4, len(alternatives_rag))
                            ligne_analysee.commentaire_utilisateur += f" | 🔄 {nb_proposees} alternatives proposées"
                            
                except Exception as e:
                    logger.error(f"❌ Erreur récupération alternatives RAG: {str(e)}")
            else:
                logger.info(f"⏭️ RAG non déclenché pour {ligne_analysee.id_produit} - Situation normale avec réapprovisionnement")
            
            ligne_analysee.alternatives_rag = alternatives_rag  # Stocker pour usage ultérieur
            
            # Étape 7: Traiter les alertes email si nécessaire (avec alternatives)
            if verification.necessite_alerte_commercial and self.email_manager:
                email_result = self.email_manager.traiter_alerte_rupture(verification, alternatives_rag)
                ligne_analysee.email_envoye = email_result.get('email_envoye', False)
                ligne_analysee.details_email = email_result
                
                if ligne_analysee.email_envoye:
                    ligne_analysee.commentaire_utilisateur += " | 📧 Commercial alerté"
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse de rupture: {str(e)}")
            ligne_analysee.commentaire_utilisateur = f"⚠️ Erreur analyse stock: {str(e)}"
            ligne_analysee.niveau_alerte = "warning"
        
        return ligne_analysee
    
    def _generer_commentaire_utilisateur(self, verification: ResultatVerification) -> str:
        """Génère un commentaire utilisateur basé sur la vérification"""
        if verification.stock_suffisant and verification.niveau_alerte == 'info':
            return "✅ Commande validée"
        
        elif verification.type_disponibilite == 'avec_commande':
            if verification.niveau_alerte == 'warning':
                # ✅ AMÉLIORATION: Commentaire plus explicite sur la dépendance au réapprovisionnement
                date_str = ""
                if verification.date_livraison_estimee:
                    date_str = f" (livraison {verification.date_livraison_estimee.strftime('%d/%m/%Y')})"
                
                # Calculer les détails de stock pour le commentaire
                produit = verification.produit
                stock_actuel = produit.quantite_stock - produit.commandes_a_livrer
                stock_a_recevoir = produit.stock_a_recevoir
                
                # Commentaire explicite sur la dépendance
                return f"⚠️ Livraison dépend du réapprovisionnement - Stock actuel: {stock_actuel}, En commande: {stock_a_recevoir}{date_str}"
            
            elif verification.niveau_alerte == 'error':
                return "🚨 Délai dépassé - Contact commercial requis"
        
        elif verification.type_disponibilite == 'rupture':
            return "🚨 RUPTURE DE STOCK - Alerte envoyée"
        
        elif verification.type_disponibilite == 'inexistant':
            return "❌ Produit inexistant - Vérifier référence"
        
        return verification.message_principal
    
    def _traiter_alerte_email_produit_inexistant(self, 
                                               ligne: LigneCommandeAnalysee, 
                                               date_commande: datetime) -> tuple[bool, Optional[Dict]]:
        """Traite l'alerte email pour un produit inexistant"""
        try:
            donnees = {
                'product_id': ligne.id_produit,
                'quantite_demandee': ligne.quantite,
                'date_commande': date_commande.strftime('%d/%m/%Y')
            }
            
            email_genere = self.email_manager.generer_email_avec_ia('produit_inexistant', donnees)
            
            email_envoye = False
            if self.email_manager.config.email_commercial:
                email_envoye = self.email_manager.envoyer_email(
                    destinataire=self.email_manager.config.email_commercial,
                    objet=email_genere['objet'],
                    corps=email_genere['corps']
                )
            
            return email_envoye, {
                'email_genere': email_genere,
                'email_envoye': email_envoye,
                'type': 'produit_inexistant'
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur email produit inexistant: {str(e)}")
            return False, {'erreur': str(e)}
    
    def analyser_commande_complete(self, 
                                 commande_text: str,
                                 date_commande: Optional[datetime] = None,
                                 date_livraison_souhaitee: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Analyse une commande complète avec gestion automatique des ruptures
        
        Args:
            commande_text: Texte de la commande complète
            date_commande: Date de la commande
            date_livraison_souhaitee: Date de livraison souhaitée
            
        Returns:
            Dictionnaire avec analyse complète et statistiques
        """
        lignes = [ligne.strip() for ligne in commande_text.split('\n') if ligne.strip()]
        
        resultats = {
            'lignes_analysees': [],
            'statistiques': {
                'total_lignes': len(lignes),
                'lignes_valides': 0,
                'lignes_avec_stock_ok': 0,
                'lignes_avec_rupture': 0,
                'lignes_avec_delai': 0,
                'emails_envoyes': 0,
                'total_quantite': 0,
                'total_prix': 0.0
            },
            'alertes_generees': [],
            'resumé_commande': '',
            'date_analyse': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        for i, ligne in enumerate(lignes):
            try:
                ligne_analysee = self.analyser_ligne_commande_complete(
                    ligne, date_commande, date_livraison_souhaitee
                )
                ligne_analysee.numero_ligne = i + 1
                
                resultats['lignes_analysees'].append(ligne_analysee)
                
                # Mettre à jour les statistiques
                if ligne_analysee.parsing_success:
                    stats = resultats['statistiques']
                    stats['lignes_valides'] += 1
                    stats['total_quantite'] += ligne_analysee.quantite
                    stats['total_prix'] += ligne_analysee.prix_total
                    
                    if ligne_analysee.niveau_alerte == 'info':
                        stats['lignes_avec_stock_ok'] += 1
                    elif ligne_analysee.niveau_alerte == 'warning':
                        stats['lignes_avec_delai'] += 1
                    elif ligne_analysee.niveau_alerte == 'error':
                        stats['lignes_avec_rupture'] += 1
                    
                    if ligne_analysee.email_envoye:
                        stats['emails_envoyes'] += 1
                        resultats['alertes_generees'].append({
                            'ligne': i + 1,
                            'produit': ligne_analysee.id_produit,
                            'type': ligne_analysee.details_email.get('type', 'unknown') if ligne_analysee.details_email else 'unknown'
                        })
                
            except Exception as e:
                logger.error(f"❌ Erreur analyse ligne {i+1}: {str(e)}")
                # Créer une ligne d'erreur
                ligne_erreur = LigneCommandeAnalysee(
                    id_produit="",
                    designation=ligne,
                    quantite=0,
                    prix_unitaire=0.0,
                    prix_total=0.0,
                    parsing_success=False,
                    product_found=False,
                    commentaire_utilisateur=f"❌ Erreur système: {str(e)}",
                    niveau_alerte="error"
                )
                ligne_erreur.numero_ligne = i + 1
                resultats['lignes_analysees'].append(ligne_erreur)
        
        # Générer un résumé
        stats = resultats['statistiques']
        resultats['resumé_commande'] = self._generer_resume_commande(stats)
        
        return resultats
    
    def _generer_resume_commande(self, stats: Dict[str, int]) -> str:
        """Génère un résumé textuel de l'analyse de commande"""
        total = stats['total_lignes']
        valides = stats['lignes_valides']
        ok = stats['lignes_avec_stock_ok']
        warnings = stats['lignes_avec_delai']
        errors = stats['lignes_avec_rupture']
        emails = stats['emails_envoyes']
        
        resume = f"📊 Analyse terminée: {valides}/{total} lignes valides"
        
        if ok == valides:
            resume += " | ✅ Toutes les lignes sont OK"
        else:
            problemes = []
            if warnings > 0:
                problemes.append(f"{warnings} avec délai")
            if errors > 0:
                problemes.append(f"{errors} en rupture")
            
            if problemes:
                resume += f" | ⚠️ Problèmes: {', '.join(problemes)}"
        
        if emails > 0:
            resume += f" | 📧 {emails} alerte(s) envoyée(s)"
        
        return resume
    
    def obtenir_statistiques_globales(self) -> Dict[str, Any]:
        """Retourne les statistiques globales du système"""
        stats_search = self.search_engine.get_cache_stats()
        
        return {
            'search_engine': stats_search,
            'email_actif': self.email_manager is not None,
            'inventaire_produits': len(self.gestionnaire_stock.inventaire),
            'system_status': 'operational'
        }

def tester_commande_manager():
    """Test complet du gestionnaire de commandes avancé"""
    print("=== TEST DU GESTIONNAIRE DE COMMANDES AVANCÉ ===\n")
    
    # CORRECTION: Utiliser uniquement le fichier Excel
    manager = CommandeManagerAvance()
    
    # Test avec une commande qui devrait avoir des ruptures
    print("🔍 Test avec commande potentiellement problématique:")
    commande_test = """76000 00420000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€
7600005 00000000 CAISSE US SC 200X140X140MM Qté 2000 Prix : 0,8€
76000 00330000 CAISSE US SC 200X150X90MM Qté 100 Prix : 0,9€"""
    
    # Date de livraison très proche (dans 3 jours)
    date_livraison_proche = datetime.now() + timedelta(days=3)
    
    resultats = manager.analyser_commande_complete(
        commande_test, 
        date_livraison_souhaitee=date_livraison_proche
    )
    
    print(f"📋 {resultats['resumé_commande']}")
    print(f"📊 Statistiques:")
    for key, value in resultats['statistiques'].items():
        print(f"   • {key}: {value}")
    
    print(f"\n📝 Détail des lignes:")
    for ligne in resultats['lignes_analysees']:
        status_icon = "✅" if ligne.niveau_alerte == 'info' else "⚠️" if ligne.niveau_alerte == 'warning' else "❌"
        email_icon = " 📧" if ligne.email_envoye else ""
        print(f"   {status_icon} {ligne.id_produit}: {ligne.commentaire_utilisateur}{email_icon}")
    
    if resultats['alertes_generees']:
        print(f"\n🚨 Alertes générées:")
        for alerte in resultats['alertes_generees']:
            print(f"   • {alerte['produit']}: {alerte['type']}")
    
    print(f"\n📊 Statistiques système:")
    stats_globales = manager.obtenir_statistiques_globales()
    for key, value in stats_globales.items():
        print(f"   • {key}: {value}")
    
    print("\n✅ Test terminé avec succès !")

if __name__ == "__main__":
    tester_commande_manager() 