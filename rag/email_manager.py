#!/usr/bin/env python3
"""
Gestionnaire d'emails intelligent avec IA pour la rédaction automatique
Utilise GPT-4.1 pour générer des emails d'alerte commercial personnalisés
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import logging

from langchain_openai import ChatOpenAI
from .settings import settings
from .gestionnaire_stock import ResultatVerification

logger = logging.getLogger(__name__)

@dataclass
class ConfigurationEmail:
    """Configuration pour l'envoi d'emails"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_expediteur: str = ""
    mot_de_passe_expediteur: str = ""
    email_commercial: str = ""
    nom_commercial: str = "Commercial"
    nom_entreprise: str = "Butterfly Packaging"
    
    # Configuration avancée
    use_tls: bool = True
    timeout: int = 30

@dataclass
class PromptTemplate:
    """Template de prompt pour la génération d'email"""
    nom: str
    description: str
    prompt_system: str
    prompt_user: str
    tone: str = "professionnel"  # professionnel, urgent, informatif, amical
    
    def format_prompt_user(self, **kwargs) -> str:
        """Formate le prompt utilisateur avec les variables"""
        return self.prompt_user.format(**kwargs)

class EmailAIManager:
    """Gestionnaire d'emails intelligent avec IA"""
    
    def __init__(self, configuration: ConfigurationEmail):
        self.config = configuration
        
        # Initialisation du LLM avec la même configuration que le projet
        self.llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.7,  # Un peu de créativité pour les emails
            api_key=settings.openai_api_key
        )
        
        # Templates de prompts prédéfinis
        self.templates = self._initialiser_templates()
        
        logger.info("✅ EmailAIManager initialisé avec GPT-4.1")
    
    def _initialiser_templates(self) -> Dict[str, PromptTemplate]:
        """Initialise les templates de prompts prédéfinis"""
        
        templates = {
            "rupture_stock": PromptTemplate(
                nom="Alerte Rupture de Stock",
                description="Email d'alerte pour rupture de stock critique",
                tone="urgent",
                prompt_system="""Tu es un assistant IA spécialisé dans la rédaction d'emails commerciaux professionnels. 
                Tu travailles pour Butterfly Packaging, une entreprise spécialisée dans l'emballage.
                
                Ton rôle est de rédiger des emails d'alerte pour informer les commerciaux des ruptures de stock 
                qui impactent les commandes clients. L'email doit être :
                - URGENT mais professionnel
                - Factuel et précis
                - Orienté solution
                - Respectueux du client
                
                Structure attendue :
                1. Objet : Clair et urgent
                2. Contexte : Situation client
                3. Problème : Description précise de la rupture
                4. Impact : Conséquences pour le client
                5. Actions : Recommandations concrètes
                6. Contact : Informations pour le suivi""",
                
                prompt_user="""RUPTURE DE STOCK DÉTECTÉE
                
                Informations client :
                - Date de commande : {date_commande}
                - Produit demandé : {nom_produit} (ID: {product_id})
                - Quantité demandée : {quantite_demandee}
                - Date de livraison souhaitée : {date_livraison_souhaitee}
                
                Situation stock :
                - Stock actuel : {stock_actuel}
                - Stock à recevoir : {stock_a_recevoir}
                - Déficit : {deficit} unités
                - Délai de réapprovisionnement : {delai_reappro}
                
                Type de problème : {type_probleme}
                
                {alternatives_disponibles}
                
                Nombre d'alternatives trouvées : {nb_alternatives}
                
                Rédige un email d'alerte professionnel et urgent pour informer le commercial de cette rupture de stock.
                IMPORTANT : Si des alternatives sont disponibles, mentionne-les clairement dans l'email comme solutions immédiates.
                L'email doit inclure l'objet et le corps du message."""
            ),
            
            "delai_depasse": PromptTemplate(
                nom="Alerte Délai Dépassé",
                description="Email pour délai de livraison dépassé",
                tone="professionnel",
                prompt_system="""Tu es un assistant IA spécialisé dans la rédaction d'emails commerciaux professionnels.
                Tu travailles pour Butterfly Packaging.
                
                Ton rôle est d'informer les commerciaux quand une commande ne peut pas être livrée dans les délais souhaités
                par le client, même si le stock sera disponible avec les réapprovisionnements.
                
                L'email doit être :
                - Informatif et transparent
                - Proposer des solutions alternatives
                - Maintenir la relation client
                - Donner des éléments pour négocier""",
                
                prompt_user="""DÉLAI DE LIVRAISON DÉPASSÉ
                
                Informations commande :
                - Produit : {nom_produit} (ID: {product_id})
                - Quantité : {quantite_demandee}
                - Date souhaitée : {date_livraison_souhaitee}
                - Date estimée possible : {date_livraison_estimee}
                - Retard estimé : {retard_jours} jours
                
                Situation :
                - Stock actuel : {stock_actuel}
                - Stock avec réappro : {stock_total}
                - Délai réappro : {delai_reappro}
                
                {alternatives_disponibles}
                
                Nombre d'alternatives trouvées : {nb_alternatives}
                
                Rédige un email pour informer le commercial de ce décalage de planning et proposer des solutions.
                IMPORTANT : Si des alternatives sont disponibles, présente-les comme solutions pour respecter les délais."""
            ),
            
            "condition_requise": PromptTemplate(
                nom="Validation Requise",
                description="Email pour délai conditionnel nécessitant validation",
                tone="informatif",
                prompt_system="""Tu es un assistant IA pour Butterfly Packaging.
                
                Certains produits ont des délais conditionnels (exemple: "2 semaines après validation BAT").
                Ton rôle est d'informer le commercial qu'une action spécifique est requise pour déclencher
                la production/livraison d'un produit.""",
                
                prompt_user="""VALIDATION REQUISE POUR COMMANDE
                
                Produit : {nom_produit} (ID: {product_id})
                Quantité : {quantite_demandee}
                Condition requise : {condition}
                Délai après validation : {nombre_semaines} semaines
                
                Stock situation :
                - Stock actuel : {stock_actuel} (insuffisant)
                - Stock après réappro : {stock_total}
                
                Rédige un email pour informer le commercial de la procédure de validation nécessaire."""
            ),
            
            "produit_inexistant": PromptTemplate(
                nom="Produit Inexistant",
                description="Email pour référence produit incorrecte",
                tone="informatif",
                prompt_system="""Tu es un assistant IA pour Butterfly Packaging.
                
                Parfois, les clients demandent des produits avec des références incorrectes ou inexistantes.
                Ton rôle est d'alerter le commercial pour qu'il vérifie avec le client et propose des alternatives.""",
                
                prompt_user="""RÉFÉRENCE PRODUIT INTROUVABLE
                
                Référence demandée : {product_id}
                Quantité demandée : {quantite_demandee}
                Date de commande : {date_commande}
                
                Cette référence n'existe pas dans notre catalogue.
                
                Rédige un email pour alerter le commercial de vérifier la référence avec le client."""
            )
        }
        
        return templates
    
    def generer_email_avec_ia(self, 
                             template_nom: str, 
                             donnees: Dict[str, Any],
                             prompt_personnalise: Optional[str] = None) -> Dict[str, str]:
        """
        Génère un email en utilisant l'IA avec un template ou un prompt personnalisé
        
        Args:
            template_nom: Nom du template à utiliser (ou "custom" pour prompt personnalisé)
            donnees: Données à injecter dans le template
            prompt_personnalise: Prompt personnalisé (si template_nom = "custom")
            
        Returns:
            Dict avec 'objet' et 'corps' de l'email
        """
        try:
            if template_nom == "custom" and prompt_personnalise:
                # Utilisation d'un prompt personnalisé
                prompt_system = """Tu es un assistant IA spécialisé dans la rédaction d'emails commerciaux 
                pour Butterfly Packaging. Rédige un email professionnel selon les instructions données."""
                prompt_user = prompt_personnalise.format(**donnees)
            
            elif template_nom in self.templates:
                # Utilisation d'un template prédéfini
                template = self.templates[template_nom]
                prompt_system = template.prompt_system
                prompt_user = template.format_prompt_user(**donnees)
            
            else:
                raise ValueError(f"Template '{template_nom}' inexistant. Templates disponibles: {list(self.templates.keys())}")
            
            # Construction du prompt complet
            messages = [
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user}
            ]
            
            logger.info(f"🤖 Génération email avec IA - Template: {template_nom}")
            
            # Appel à l'IA
            response = self.llm.invoke(messages)
            contenu_email = response.content
            
            # Parser la réponse pour extraire objet et corps
            objet, corps = self._parser_reponse_ia(contenu_email)
            
            logger.info(f"✅ Email généré avec succès - Objet: {objet[:50]}...")
            
            return {
                'objet': objet,
                'corps': corps,
                'template_utilise': template_nom,
                'genere_le': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération d'email: {str(e)}")
            return self._email_fallback(template_nom, donnees)
    
    def _parser_reponse_ia(self, contenu: str) -> tuple[str, str]:
        """Parse la réponse de l'IA pour extraire objet et corps"""
        lines = contenu.strip().split('\n')
        
        objet = "Alerte - Action requise"  # Défaut
        corps = contenu
        
        # Chercher "Objet:" ou "Subject:" dans les premières lignes
        for i, line in enumerate(lines[:5]):
            line_lower = line.lower().strip()
            if line_lower.startswith(('objet:', 'subject:', 'sujet:')):
                objet = line.split(':', 1)[1].strip()
                # Le corps commence après l'objet
                corps = '\n'.join(lines[i+1:]).strip()
                break
        
        # Nettoyer le corps (supprimer lignes vides au début)
        corps = '\n'.join(line for line in corps.split('\n') if line.strip())
        
        return objet, corps
    
    def _email_fallback(self, template_nom: str, donnees: Dict[str, Any]) -> Dict[str, str]:
        """Email de fallback en cas d'erreur IA"""
        objet = f"[URGENT] Alerte automatique - {template_nom}"
        
        corps = f"""Alerte automatique générée le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

Une situation nécessite votre attention immédiate :

Type d'alerte : {template_nom}
Données de la situation :
{json.dumps(donnees, indent=2, ensure_ascii=False)}

Veuillez traiter cette alerte rapidement.

---
Message généré automatiquement par le système Butterfly Packaging
"""
        
        return {
            'objet': objet,
            'corps': corps,
            'template_utilise': f"{template_nom}_fallback",
            'genere_le': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
    
    def envoyer_email(self, 
                     destinataire: str,
                     objet: str, 
                     corps: str,
                     copie_carbone: Optional[List[str]] = None,
                     pieces_jointes: Optional[List[str]] = None) -> bool:
        """
        Envoie un email via SMTP
        
        Args:
            destinataire: Email du destinataire principal
            objet: Objet de l'email
            corps: Corps du message
            copie_carbone: Liste d'emails en copie (optionnel)
            pieces_jointes: Liste de chemins vers fichiers à joindre (optionnel)
            
        Returns:
            bool: True si envoyé avec succès, False sinon
        """
        try:
            # Création du message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_expediteur
            msg['To'] = destinataire
            msg['Subject'] = objet
            
            if copie_carbone:
                msg['Cc'] = ', '.join(copie_carbone)
            
            # Ajout du corps du message
            msg.attach(MIMEText(corps, 'plain', 'utf-8'))
            
            # Ajout des pièces jointes si présentes
            if pieces_jointes:
                for fichier in pieces_jointes:
                    self._ajouter_piece_jointe(msg, fichier)
            
            # Configuration du serveur SMTP
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=self.config.timeout) as server:
                if self.config.use_tls:
                    server.starttls(context=context)
                
                server.login(self.config.email_expediteur, self.config.mot_de_passe_expediteur)
                
                # Liste complète des destinataires
                tous_destinataires = [destinataire]
                if copie_carbone:
                    tous_destinataires.extend(copie_carbone)
                
                server.sendmail(self.config.email_expediteur, tous_destinataires, msg.as_string())
            
            logger.info(f"✅ Email envoyé avec succès à {destinataire}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi d'email: {str(e)}")
            return False
    
    def _ajouter_piece_jointe(self, msg: MIMEMultipart, chemin_fichier: str):
        """Ajoute une pièce jointe au message"""
        try:
            with open(chemin_fichier, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            
            # Ajouter l'en-tête de pièce jointe
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {chemin_fichier.split("/")[-1]}'
            )
            
            msg.attach(part)
            logger.info(f"Pièce jointe ajoutée: {chemin_fichier}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la pièce jointe {chemin_fichier}: {str(e)}")
    
    def traiter_alerte_rupture(self, resultat_verification: ResultatVerification, alternatives_rag: List[Dict] = None) -> Dict[str, Any]:
        """
        Traite une alerte de rupture en générant et envoyant automatiquement l'email avec alternatives RAG
        
        Args:
            resultat_verification: Résultat de la vérification de stock
            alternatives_rag: Liste des alternatives trouvées par le RAG (optionnel)
            
        Returns:
            Dict avec le résultat du traitement
        """
        try:
            # Déterminer le type de template selon le problème
            details = resultat_verification.details_pour_commercial
            type_probleme = details.get('type_probleme', 'rupture_totale')
            
            template_map = {
                'rupture_totale': 'rupture_stock',
                'delai_livraison': 'delai_depasse', 
                'condition_requise': 'condition_requise',
                'produit_inexistant': 'produit_inexistant'
            }
            
            template_nom = template_map.get(type_probleme, 'rupture_stock')
            
            # Préparer les données pour l'IA
            donnees = {
                'date_commande': details.get('date_commande', 'Non spécifiée'),
                'nom_produit': details.get('nom_produit', resultat_verification.produit.nom),
                'product_id': details.get('product_id', resultat_verification.produit.product_id),
                'quantite_demandee': details.get('quantite_demandee', resultat_verification.quantite_demandee),
                'date_livraison_souhaitee': details.get('date_livraison_souhaitee', 'Non spécifiée'),
                'stock_actuel': details.get('stock_actuel', resultat_verification.produit.quantite_stock),
                'stock_a_recevoir': details.get('stock_a_recevoir', resultat_verification.produit.commandes_a_livrer),
                'stock_total': details.get('stock_actuel', 0) + details.get('stock_a_recevoir', 0),
                'deficit': details.get('deficit', 0),
                'delai_reappro': details.get('delai_reappro', resultat_verification.produit.delai_livraison),
                'type_probleme': type_probleme,
                'date_livraison_estimee': details.get('date_livraison_estimee', 'Inconnue'),
                'condition': details.get('condition', ''),
                'nombre_semaines': details.get('nombre_semaines', 0),
                'retard_jours': 0  # Calculé si nécessaire
            }
            
            # Calculer le retard en jours si applicable
            if 'date_livraison_souhaitee' in details and 'date_livraison_estimee' in details:
                try:
                    from datetime import datetime
                    date_souhaitee = datetime.strptime(details['date_livraison_souhaitee'], '%d/%m/%Y')
                    date_estimee = datetime.strptime(details['date_livraison_estimee'], '%d/%m/%Y')
                    retard = (date_estimee - date_souhaitee).days
                    donnees['retard_jours'] = max(0, retard)
                except:
                    donnees['retard_jours'] = 0
            
            # NOUVEAU : Ajouter les alternatives RAG si disponibles
            if alternatives_rag:
                logger.info(f"📋 Intégration de {len(alternatives_rag)} alternatives RAG dans l'email")
                
                # Formater les alternatives pour l'email
                alternatives_text = "ALTERNATIVES DISPONIBLES :\n\n"
                for i, alt in enumerate(alternatives_rag[:5], 1):  # Max 5 alternatives dans l'email
                    alternatives_text += f"{i}. {alt.get('name', 'N/A')}\n"
                    alternatives_text += f"   • Stock disponible : {alt.get('stock_disponible', 'N/A')} unités\n"
                    alternatives_text += f"   • Prix de vente conseillé : {alt.get('prix_vente_conseille', 'N/A')}€\n"
                    alternatives_text += f"   • Délai de livraison : {alt.get('delai_livraison', 'N/A')}\n"
                    
                    # Ajouter similarité technique si disponible
                    if alt.get('similarite_technique'):
                        alternatives_text += f"   • Compatibilité technique : {alt['similarite_technique']:.1%}\n"
                    
                    alternatives_text += "\n"
                
                donnees['alternatives_disponibles'] = alternatives_text
                donnees['nb_alternatives'] = len(alternatives_rag)
            else:
                donnees['alternatives_disponibles'] = "Aucune alternative trouvée dans le système."
                donnees['nb_alternatives'] = 0
            
            # Générer l'email avec l'IA
            email_genere = self.generer_email_avec_ia(template_nom, donnees)
            
            # Envoyer l'email si configuration complète
            email_envoye = False
            if self.config.email_commercial and self.config.email_expediteur:
                email_envoye = self.envoyer_email(
                    destinataire=self.config.email_commercial,
                    objet=email_genere['objet'],
                    corps=email_genere['corps']
                )
            
            return {
                'email_genere': email_genere,
                'email_envoye': email_envoye,
                'destinataire': self.config.email_commercial,
                'template_utilise': template_nom,
                'traite_le': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement de l'alerte: {str(e)}")
            return {
                'erreur': str(e),
                'email_genere': None,
                'email_envoye': False
            }
    
    def lister_templates(self) -> Dict[str, str]:
        """Retourne la liste des templates disponibles"""
        return {nom: template.description for nom, template in self.templates.items()}
    
    def ajouter_template_personnalise(self, nom: str, template: PromptTemplate):
        """Ajoute un template personnalisé"""
        self.templates[nom] = template
        logger.info(f"✅ Template personnalisé '{nom}' ajouté")

def tester_email_manager():
    """Fonction de test pour le gestionnaire d'emails"""
    print("=== TEST DU GESTIONNAIRE D'EMAILS IA ===\n")
    
    # Configuration de test
    config = ConfigurationEmail(
        email_expediteur="test@butterfly-packaging.com",
        email_commercial="commercial@butterfly-packaging.com",
        nom_commercial="Jean Dupont"
    )
    
    email_manager = EmailAIManager(config)
    
    # Test des templates disponibles
    print("📋 Templates disponibles:")
    for nom, description in email_manager.lister_templates().items():
        print(f"   • {nom}: {description}")
    print()
    
    # Test de génération d'email pour rupture
    print("🤖 Test génération email - Rupture de stock:")
    donnees_rupture = {
        'date_commande': '15/01/2024',
        'nom_produit': 'Caisses américaines double cannelure',
        'product_id': 'id5',
        'quantite_demandee': 100,
        'date_livraison_souhaitee': '20/01/2024',
        'stock_actuel': 50,
        'stock_a_recevoir': 15,
        'deficit': 35,
        'delai_reappro': '4 semaines',
        'type_probleme': 'rupture_totale'
    }
    
    email_rupture = email_manager.generer_email_avec_ia('rupture_stock', donnees_rupture)
    print(f"   📧 Objet: {email_rupture['objet']}")
    print(f"   📝 Corps (aperçu): {email_rupture['corps'][:200]}...")
    print()
    
    # Test avec délai dépassé
    print("🤖 Test génération email - Délai dépassé:")
    donnees_delai = {
        'nom_produit': 'Film étirable standard 17 µm',
        'product_id': 'produit_016_2',
        'quantite_demandee': 80,
        'date_livraison_souhaitee': '25/01/2024',
        'date_livraison_estimee': '05/02/2024',
        'stock_actuel': 30,
        'stock_total': 95,
        'delai_reappro': '3 semaines',
        'retard_jours': 11
    }
    
    email_delai = email_manager.generer_email_avec_ia('delai_depasse', donnees_delai)
    print(f"   📧 Objet: {email_delai['objet']}")
    print(f"   📝 Corps (aperçu): {email_delai['corps'][:200]}...")
    print()
    
    print("✅ Tests terminés avec succès !")

if __name__ == "__main__":
    tester_email_manager() 