#!/usr/bin/env python3
"""
Script d'alimentation RAG selon le schéma défini par l'utilisateur
- Description complète pour les "CAISSE US SC + dimensions"
- Description simple pour les autres produits
"""

import os
import json
import pandas as pd
import re
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone

def detect_caisse_us_sc(nom_produit):
    """Détecte si le produit suit la nomenclature CAISSE US SC + dimensions"""
    pattern = r"CAISSE US SC\s+\d+X\d+X\d+"
    return bool(re.match(pattern, nom_produit.upper()))

def detect_caisse_us_dc(nom_produit):
    """Détecte si le produit suit la nomenclature CAISSE US DC + dimensions"""
    pattern = r"CAISSE US DC\s+\d+X\d+X\d+"
    return bool(re.match(pattern, nom_produit.upper()))

def detect_caisse_archive(nom_produit):
    """Détecte les caisses d'archivage"""
    return "ARCHIVE" in nom_produit.upper()

def detect_caisse_kraft(nom_produit):
    """Détecte les caisses kraft"""
    nom_upper = nom_produit.upper()
    return "KRAFT" in nom_upper and "CAISSE" in nom_upper

def detect_caisse_variable(nom_produit):
    """Détecte les caisses à hauteur variable"""
    nom_upper = nom_produit.upper()
    return ("VARIABLE" in nom_upper or "HAUT VARIABLE" in nom_upper) and "CAISSE" in nom_upper

def detect_caisse_standard(nom_produit):
    """Détecte les caisses standard (FEFCO, US B20, BC...)"""
    nom_upper = nom_produit.upper()
    # Caisses qui contiennent CAISSE mais ne sont pas SC, DC, archive, kraft ou variable
    if "CAISSE" not in nom_upper:
        return False
    # Exclure les SAC qui contiennent CAISSE
    if "SAC" in nom_upper:
        return False
    if any(detect_func(nom_produit) for detect_func in [detect_caisse_us_sc, detect_caisse_us_dc, 
                                                        detect_caisse_archive, detect_caisse_kraft, 
                                                        detect_caisse_variable]):
        return False
    # Toutes les autres caisses sont considérées comme standard
    return True

def detect_sac(nom_produit):
    """Détecte les sacs d'emballage"""
    return "SAC" in nom_produit.upper()

def get_description_template(nom_produit, couleur):
    """Retourne la description selon le type de produit"""
    
    if detect_caisse_us_sc(nom_produit):
        # Description complète pour CAISSE US SC
        return {
            "description": """Caisses américaines simple cannelure standard

Butterfly Packaging, groupe français de production, d'impression et de distribution de produits d'emballage, met à votre disposition les caisses américaines simple cannelure.

Fonctionnalités et avantages
Les caisses américaines simple cannelure sont des emballages polyvalents et robustes, idéaux pour le transport et le stockage de vos produits. Dotées de rabats supérieurs et inférieurs, elles offrent une protection efficace contre les chocs, les vibrations et les dommages pendant la manipulation et l'expédition. Personnalisables avec votre logo et vos couleurs, elles peuvent être adaptées à vos besoins spécifiques en matière d'emballage et de branding.

Polyvalence d'utilisation
Grâce à leur conception modulaire, les caisses américaines simple cannelure peuvent être utilisées pour une grande variété de produits, des articles légers aux produits plus lourds, jusqu'à 20 kg. Leur qualité en kraft et leur certification LNE et ECT garantissent une résistance optimale et une protection fiable pour vos marchandises, quel que soit leur poids ou leur fragilité.

Respect de l'environnement
Soucieux de l'impact environnemental, Butterfly Packaging utilise des matériaux recyclables à 100% pour la fabrication de ses caisses américaines simple cannelure. En optant pour nos solutions d'emballage écologiques, vous contribuez à la préservation de l'environnement tout en bénéficiant d'une protection efficace pour vos produits.""",
            
            "avantages": [
                "Protègent vos produits jusqu'à 20 kg",
                "Logo, couleurs, tailles et options sur mesure", 
                "Fabriquées en matériaux 100% recyclables",
                "Résistance garantie avec certifications LNE et ECT",
                "Large choix de tailles standard"
            ],
            
            "utilisations": [
                "Transport et stockage de produits légers à moyens (jusqu'à 20kg)",
                "Expédition sécurisée avec protection anti-chocs",
                "Emballage personnalisable pour le branding",
                "Solutions écologiques pour entreprises responsables"
            ]
        }
    
    elif detect_caisse_us_dc(nom_produit):
        # Description complète pour CAISSE US DC
        return {
            "description": """Caisses américaines double cannelure

Butterfly Packaging, groupe français de production, fabricant et fournisseur de produits d'emballage logistique, met à votre disposition les caisses américaines double cannelure.

Fonctionnalités et avantages
Les caisses américaines double cannelure sont des emballages polyvalents et résistants, conçus pour assurer une protection optimale de vos produits lors du transport et du stockage. Dotées de rabats supérieurs et inférieurs, elles offrent une grande stabilité et une résistance accrue aux chocs et aux vibrations. Personnalisables avec vos couleurs et votre logo, elles peuvent être adaptées à vos besoins spécifiques en matière d'emballage et de branding.

Polyvalence d'utilisation
Grâce à leur double cannelure, ces caisses conviennent parfaitement pour des produits plus lourds ou plus fragiles, pesant 20 kg ou plus. Leur qualité en kraft et leur certification LNE et ECT garantissent une résistance exceptionnelle et une protection fiable pour vos marchandises, même dans les conditions les plus exigeantes.

Respect de l'environnement
Chez Butterfly Packaging, nous nous engageons à utiliser des matériaux recyclables à 100% pour la fabrication de nos emballages, y compris nos caisses américaines double cannelure. En choisissant nos solutions d'emballage écologiques, vous contribuez à la préservation de l'environnement tout en bénéficiant d'une protection optimale pour vos produits.

Personnalisation et disponibilité
Nos caisses américaines double cannelure sont disponibles dans une large gamme de tailles standard pour répondre à vos besoins d'emballage. De plus, nous proposons des options de personnalisation avancées, telles que des rabats sur mesure, des bandes d'arrachage et des compartiments, pour créer des emballages sur mesure parfaitement adaptés à vos produits.""",
            
            "avantages": [
                "Idéales pour les produits lourds ou fragiles (20 kg et plus)",
                "Fabriquées en kraft et certifiées LNE et ECT pour une résistance exceptionnelle",
                "100% recyclables, contribuent à la préservation de la planète",
                "Disponibles en différentes tailles et personnalisables avec vos couleurs et logo",
                "Options de personnalisation avancées (rabats sur mesure, bandes d'arrachage, compartiments)"
            ],
            
            "utilisations": [
                "Transport et stockage de produits lourds ou fragiles (20 kg et plus)",
                "Applications exigeantes nécessitant une résistance exceptionnelle",
                "Emballage personnalisable pour le branding avancé",
                "Solutions écologiques pour entreprises responsables"
                         ]
         }
    
    elif detect_caisse_archive(nom_produit):
        # Description pour CAISSE ARCHIVE
        return {
            "description": """Caisses d'archivage professionnelles Butterfly Packaging

Spécialement conçues pour l'archivage et le stockage longue durée de documents, dossiers et fichiers. Construction renforcée pour supporter le poids des archives tout en préservant vos documents importants.

Fonctionnalités d'archivage
Nos caisses d'archivage offrent une protection optimale contre la poussière, l'humidité et les manipulations. Dotées de rabats sécurisés et d'une structure renforcée, elles garantissent l'intégrité de vos archives sur le long terme.

Solutions professionnelles
Idéales pour bureaux, administrations et entreprises nécessitant un archivage méthodique et sécurisé de leurs documents importants.""",
            
            "avantages": [
                "Protection longue durée des documents",
                "Résistance aux manipulations répétées", 
                "Construction renforcée pour archives lourdes",
                "Empilement sécurisé pour optimiser l'espace",
                "Matériaux respectueux de l'environnement"
            ],
            
            "utilisations": [
                "Archivage de documents administratifs",
                "Stockage longue durée de dossiers",
                "Organisation professionnelle des bureaux",
                "Conservation sécurisée d'archives importantes"
            ]
        }
    
    elif detect_caisse_kraft(nom_produit):
        # Description pour CAISSE KRAFT
        return {
            "description": """Caisses en kraft naturel Butterfly Packaging

Fabriquées en kraft naturel non blanchi, nos caisses offrent une solution d'emballage écologique et résistante. Le kraft naturel conserve ses propriétés mécaniques tout en respectant l'environnement.

Avantages du kraft naturel
Le kraft non traité présente d'excellentes propriétés de résistance et de recyclabilité. Sa teinte naturelle convient parfaitement aux entreprises soucieuses de leur image environnementale.

Solutions écologiques
Nos caisses kraft s'inscrivent dans une démarche de développement durable, alliant performance et respect de l'environnement.""",
            
            "avantages": [
                "Kraft naturel 100% recyclable",
                "Résistance mécanique élevée",
                "Image écologique et naturelle",
                "Excellent rapport qualité-prix",
                "Certification environnementale"
            ],
            
            "utilisations": [
                "Emballage écologique de produits",
                "Transport respectueux de l'environnement",
                "Solutions pour entreprises engagées",
                "Conditionnement naturel et durable"
            ]
        }
    
    elif detect_caisse_variable(nom_produit):
        # Description pour CAISSE VARIABLE
        return {
            "description": """Caisses à hauteur variable Butterfly Packaging

Solutions innovantes pour l'emballage de produits de tailles différentes. La hauteur ajustable permet d'optimiser l'emballage selon le contenu, réduisant les coûts de stockage et transport.

Flexibilité d'emballage
Grâce à leur conception modulaire, ces caisses s'adaptent parfaitement à vos produits, évitant le gaspillage d'espace et de matériau tout en assurant une protection optimale.

Innovation logistique
Nos caisses variables représentent l'avenir de l'emballage adaptatif, permettant une optimisation maximale des coûts et de l'efficacité.""",
            
            "avantages": [
                "Hauteur ajustable selon les besoins",
                "Optimisation de l'espace de transport",
                "Réduction des coûts d'emballage", 
                "Solution polyvalente multi-produits",
                "Personnalisation sur mesure disponible"
            ],
            
            "utilisations": [
                "Emballage de produits de tailles variées",
                "Optimisation des coûts de transport",
                "Solutions flexibles pour e-commerce",
                "Adaptation aux besoins saisonniers"
            ]
        }
    
    elif detect_caisse_standard(nom_produit):
        # Description pour CAISSE STANDARD
        return {
            "description": """Caisses carton standard Butterfly Packaging

Large gamme de caisses aux formats standardisés (FEFCO, US B20, BC...) pour répondre à tous vos besoins d'emballage. Fabriquées selon les normes industrielles pour garantir qualité et compatibilité.

Formats certifiés
Nos caisses respectent les standards internationaux d'emballage, assurant une parfaite intégration dans vos chaînes logistiques existantes.

Fiabilité industrielle
Conçues pour répondre aux exigences les plus strictes de l'industrie, nos caisses standard garantissent une performance constante et prévisible.""",
            
            "avantages": [
                "Formats standardisés certifiés", 
                "Compatible avec les systèmes existants",
                "Large choix de dimensions",
                "Qualité industrielle constante",
                "Livraison rapide sur formats stock"
            ],
            
            "utilisations": [
                "Intégration dans chaînes logistiques",
                "Emballage industriel standardisé",
                "Solutions compatibles multi-fournisseurs",
                "Optimisation des processus existants"
            ]
        }
    
    elif detect_sac(nom_produit):
        # Description pour SAC
        return {
            "description": """Sacs d'emballage professionnel Butterfly Packaging

Solutions flexibles pour l'emballage et la protection de vos produits. Disponibles en différents matériaux et épaisseurs selon vos besoins spécifiques.

Flexibilité d'emballage
Nos sacs s'adaptent aux formes les plus variées, offrant une protection optimale pour des produits aux géométries complexes ou irrégulières.

Solutions adaptées
Large gamme de matériaux et de formats pour répondre à tous vos besoins d'emballage flexible et économique.""",
            
            "avantages": [
                "Solutions flexibles d'emballage",
                "Différents matériaux disponibles", 
                "Adapté aux formes irrégulières",
                "Économique et pratique",
                "Options étanches disponibles"
            ],
            
            "utilisations": [
                "Emballage de produits irréguliers",
                "Protection flexible et légère",
                "Solutions économiques de conditionnement",
                "Emballage temporaire et transport"
            ]
        }
    
    else:
        # Description simple pour autres produits
        couleur_text = f" couleur {couleur}" if couleur and couleur.strip() else ""
        return {
            "description": f"Produit d'emballage professionnel Butterfly Packaging{couleur_text}. Solution adaptée pour vos besoins logistiques et de protection des marchandises.",
            "avantages": [
                "Qualité professionnelle Butterfly Packaging",
                "Adapté aux besoins logistiques",
                "Protection efficace des marchandises"
            ],
            "utilisations": [
                "Applications logistiques et d'emballage",
                "Protection et transport de marchandises"
            ]
        }

def determine_category(nom_produit):
    """Détermine la catégorie du produit selon son nom"""
    nom_upper = nom_produit.upper()
    
    if "CAISSE" in nom_upper:
        return "caisse carton"
    elif "FILM" in nom_upper:
        return "film emballage"
    elif "PALETTE" in nom_upper:
        return "palette"
    elif "BOITE" in nom_upper or "BOÎTE" in nom_upper:
        return "boîte carton"
    elif "SAC" in nom_upper:
        return "sac emballage"
    else:
        return "emballage logistique"

def load_and_convert_excel():
    """Charge et convertit les données Excel selon le schéma défini"""
    print("📊 Chargement des données Excel...")
    
    try:
        df = pd.read_excel("data/Articles.xlsx")
        print(f"✅ {len(df)} produits chargés")
        
        documents = []
        
        for index, row in df.iterrows():
            try:
                # Extraction des données de base
                id_produit = str(row.get('N°', f'PROD_{index+1:04d}')).strip()
                nom = str(row.get('Description', 'Produit inconnu')).strip()
                couleur = str(row.get('Couleur Support', '')).strip() if pd.notna(row.get('Couleur Support')) else ''
                
                # FILTRAGE : Traiter SEULEMENT les nouvelles familles (pas SC/DC déjà présents)
                nouvelles_familles = [
                    detect_caisse_archive(nom),
                    detect_caisse_kraft(nom),
                    detect_caisse_variable(nom),
                    detect_caisse_standard(nom),
                    detect_sac(nom)
                ]
                
                if not any(nouvelles_familles):
                    continue  # Ignorer ce produit (y compris SC/DC déjà présents)
                
                # Déterminer la catégorie
                categorie = determine_category(nom)
                
                # Obtenir le template de description (forcément complet pour CAISSE US SC)
                template = get_description_template(nom, couleur)
                
                # Construire le document JSON
                product_data = {
                    "id": id_produit,
                    "nom": nom,
                    "categorie": categorie,
                    "type": "Emballage logistique",
                    "description": template["description"],
                    "avantages": template["avantages"],
                    "utilisations": template["utilisations"]
                }
                
                # Ajouter la couleur si disponible
                if couleur:
                    product_data["couleur"] = couleur
                
                # Créer le document Pinecone
                page_content = json.dumps(product_data, ensure_ascii=False, indent=2)
                
                doc = Document(
                    page_content=page_content,
                    metadata={
                        "source": f"Articles.xlsx - ligne {index+1}",
                        "id": id_produit,
                        "nom": nom,
                        "categorie": categorie,
                        "type_description": "complete" if detect_caisse_us_sc(nom) else "simple"
                    }
                )
                
                documents.append(doc)
                
                if (index + 1) % 25 == 0:
                    print(f"   📦 {index + 1} produits convertis...")
                    
            except Exception as e:
                print(f"❌ Erreur ligne {index+1}: {e}")
                continue
        
        print(f"✅ {len(documents)} documents créés")
        
        # Afficher les statistiques des NOUVELLES familles ajoutées
        families_stats = {}
        for doc in documents:
            nom = json.loads(doc.page_content)["nom"]
            if detect_caisse_archive(nom):
                families_stats["CAISSE ARCHIVE"] = families_stats.get("CAISSE ARCHIVE", 0) + 1
            elif detect_caisse_kraft(nom):
                families_stats["CAISSE KRAFT"] = families_stats.get("CAISSE KRAFT", 0) + 1
            elif detect_caisse_variable(nom):
                families_stats["CAISSE VARIABLE"] = families_stats.get("CAISSE VARIABLE", 0) + 1
            elif detect_caisse_standard(nom):
                families_stats["CAISSE STANDARD"] = families_stats.get("CAISSE STANDARD", 0) + 1
            elif detect_sac(nom):
                families_stats["SAC"] = families_stats.get("SAC", 0) + 1
        
        print(f"📈 Nouvelles familles à ajouter:")
        for famille, count in sorted(families_stats.items()):
            print(f"   - {famille}: {count} produits")
        
        # Compter les SC/DC existants
        sc_count = len([row for _, row in df.iterrows() if detect_caisse_us_sc(str(row.get('Description', '')))])
        dc_count = len([row for _, row in df.iterrows() if detect_caisse_us_dc(str(row.get('Description', '')))])
        
        print(f"📊 Familles déjà présentes dans Pinecone:")
        print(f"   - CAISSE US SC: {sc_count} produits (déjà ajoutés)")
        print(f"   - CAISSE US DC: {dc_count} produits (déjà ajoutés)")
        print(f"   - Total ignoré: {sc_count + dc_count} (déjà présents)")
        print(f"   ✅ Ajout complémentaire des nouvelles familles")
        
        return documents
        
    except Exception as e:
        print(f"❌ Erreur chargement Excel: {e}")
        return None

def setup_pinecone():
    """Configuration Pinecone"""
    print("\n🔍 Configuration Pinecone...")
    
    load_dotenv()
    
    # Forcer le bon nom d'index
    index_name = "sample-index"
    
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index = pc.Index(index_name)
    
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    
    print(f"✅ Connexion établie sur '{index_name}'")
    return vector_store, index

def main():
    """Fonction principale"""
    print("🚀 === ALIMENTATION RAG SCHEMA BUTTERFLY PACKAGING ===\n")
    
    try:
        # 1. Charger et convertir les données
        documents = load_and_convert_excel()
        if not documents:
            return
        
        # 2. Configurer Pinecone
        vector_store, index = setup_pinecone()
        
        # 3. Vérifier l'état actuel
        stats = index.describe_index_stats()
        print(f"\n📊 État actuel Pinecone: {stats.total_vector_count} vecteurs")
        
        # 4. Confirmation
        print(f"\n⚠️ Ajout de {len(documents)} NOUVEAUX produits (complémentaires)")
        print(f"   Les 291 caisses US (SC/DC) restent en place")
        response = input("▶️ Continuer ? (o/n): ").lower().strip()
        if response not in ['o', 'oui', 'y', 'yes']:
            print("❌ Annulation")
            return
        
        # 5. Alimentation
        print("\n📤 Alimentation en cours...")
        # Utiliser un préfixe différent pour éviter les conflits avec les caisses US existantes
        uuids = [f"butterfly_new_{i:04d}" for i in range(len(documents))]
        
        # Ajout par lots
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_ids = uuids[i:i+batch_size]
            
            print(f"   📦 Lot {i//batch_size + 1} ({len(batch_docs)} produits)...")
            vector_store.add_documents(documents=batch_docs, ids=batch_ids)
        
        print(f"\n🎉 Alimentation réussie!")
        print(f"   📊 {len(documents)} produits ajoutés")
        print(f"   🔎 RAG prêt pour les alternatives")
        
        # 6. Test rapide
        print(f"\n🔍 Test de recherche...")
        test_results = vector_store.similarity_search("caisse carton", k=2)
        for i, doc in enumerate(test_results):
            content = json.loads(doc.page_content)
            print(f"   {i+1}. {content['nom']} ({content['categorie']})")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main() 