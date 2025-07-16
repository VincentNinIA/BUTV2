#!/usr/bin/env python3
"""
Script de test pour vérifier l'état du RAG et des données d'inventaire
"""

import os
import pandas as pd
from dotenv import load_dotenv
import json

def check_env_variables():
    """Vérifie les variables d'environnement nécessaires"""
    print("🔧 Vérification des variables d'environnement...")
    
    load_dotenv()
    
    required_vars = [
        "OPENAI_API_KEY",
        "PINECONE_API_KEY",
        "PINECONE_ENVIRONMENT"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: Configuré")
    
    if missing_vars:
        print(f"\n❌ Variables manquantes: {missing_vars}")
        print("\n📝 Créez un fichier .env avec:")
        print("OPENAI_API_KEY=votre_clé_openai")
        print("PINECONE_API_KEY=votre_clé_pinecone")
        print("PINECONE_ENVIRONMENT=votre_environnement_pinecone")
        return False
    else:
        print("✅ Toutes les variables d'environnement sont configurées")
        return True

def check_inventory_data():
    """Vérifie les données d'inventaire"""
    print("\n📊 Vérification des données d'inventaire...")
    
    try:
        # Vérifier le fichier Excel
        if os.path.exists("data/Articles.xlsx"):
            print("✅ Fichier Articles.xlsx trouvé")
            
            # Lire les données
            df = pd.read_excel("data/Articles.xlsx")
            print(f"📈 {len(df)} produits dans le fichier Excel")
            print(f"📋 Colonnes: {list(df.columns)}")
            
            # Afficher quelques exemples avec le format demandé par l'utilisateur
            print("\n📦 Exemples de produits (format: ID description Qté quantité Prix : prix):")
            for i, row in df.head(3).iterrows():
                try:
                    # Extraire les informations principales
                    nom = row.get('nom', 'N/A')
                    id_prod = row.get('id', f'ID{i+1}')
                    stock = row.get('stock_disponible', 0)
                    prix = row.get('prix_vente_conseille', 0.0)
                    
                    print(f"   {id_prod} {nom} Qté {stock} Prix : {prix:.2f}€")
                except Exception as e:
                    print(f"   Erreur lecture ligne {i}: {e}")
            
            return True
        else:
            print("❌ Fichier Articles.xlsx non trouvé")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lecture inventaire: {e}")
        return False

def check_pinecone_status():
    """Vérifie l'état de la base vectorielle Pinecone"""
    print("\n🔍 Vérification de l'état Pinecone...")
    
    try:
        if not check_env_variables():
            return False
            
        from pinecone import Pinecone
        
        # Initialiser Pinecone
        pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
        
        # Vérifier l'index
        index_name = "sample-index"  # Nom par défaut du projet
        
        # Lister les index disponibles
        indexes = pc.list_indexes()
        print(f"📋 Index disponibles: {[idx.name for idx in indexes]}")
        
        if index_name in [idx.name for idx in indexes]:
            print(f"✅ Index '{index_name}' trouvé")
            
            # Vérifier le contenu
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            total_vectors = stats.total_vector_count
            
            print(f"📊 Nombre de vecteurs dans l'index: {total_vectors}")
            
            if total_vectors > 0:
                print("✅ Le RAG contient des données")
                return True
            else:
                print("⚠️ Le RAG est vide (0 vecteurs)")
                return False
        else:
            print(f"❌ Index '{index_name}' non trouvé")
            return False
            
    except Exception as e:
        print(f"❌ Erreur connexion Pinecone: {e}")
        return False

def test_rag_search():
    """Test rapide de recherche RAG"""
    print("\n🔎 Test de recherche RAG...")
    
    try:
        from rag.core import setup_rag
        
        # Initialiser le RAG
        retriever = setup_rag()
        
        # Test de recherche
        query = "boîte carton 300mm"
        results = retriever.get_relevant_documents(query)
        
        print(f"✅ Recherche '{query}' - {len(results)} résultats trouvés")
        
        if results:
            print("📦 Premier résultat:")
            content = results[0].page_content
            if len(content) > 200:
                content = content[:200] + "..."
            print(f"   {content}")
            return True
        else:
            print("⚠️ Aucun résultat trouvé")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test RAG: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 === TEST DE L'ÉTAT DU SYSTÈME RAG-NINIA ===\n")
    
    # Tests individuels
    env_ok = check_env_variables()
    data_ok = check_inventory_data()
    
    if env_ok:
        pinecone_ok = check_pinecone_status()
        if pinecone_ok:
            rag_ok = test_rag_search()
        else:
            rag_ok = False
    else:
        pinecone_ok = False
        rag_ok = False
    
    # Résumé
    print("\n" + "="*50)
    print("📋 RÉSUMÉ DE L'ÉTAT SYSTÈME:")
    print(f"   🔧 Variables d'environnement: {'✅' if env_ok else '❌'}")
    print(f"   📊 Données d'inventaire: {'✅' if data_ok else '❌'}")
    print(f"   🔍 Base vectorielle Pinecone: {'✅' if pinecone_ok else '❌'}")
    print(f"   🔎 Recherche RAG: {'✅' if rag_ok else '❌'}")
    
    # Recommandations
    print("\n💡 ACTIONS RECOMMANDÉES:")
    
    if not env_ok:
        print("   1. Créer le fichier .env avec les clés API")
    
    if not pinecone_ok and env_ok:
        print("   2. Alimenter la base Pinecone avec: python ingestion/ajout_produits.py")
    
    if data_ok and not rag_ok:
        print("   3. Vérifier la configuration du RAG dans rag/core.py")
    
    if env_ok and data_ok and pinecone_ok and rag_ok:
        print("   🎉 Système prêt ! Vous pouvez tester les alternatives.")
        print("   ▶️ Lancez: python debug_app.py pour tester")

if __name__ == "__main__":
    main() 