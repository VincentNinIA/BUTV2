#!/usr/bin/env python3
"""
Script pour alimenter le RAG avec les données d'inventaire Excel
"""

import os
import json
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone

def load_inventory_data():
    """Charge les données d'inventaire depuis Excel"""
    print("📊 Chargement des données d'inventaire...")
    
    try:
        df = pd.read_excel("data/Articles.xlsx")
        print(f"✅ {len(df)} produits chargés depuis Articles.xlsx")
        print(f"📋 Colonnes disponibles: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"❌ Erreur lors du chargement du fichier Excel: {e}")
        return None

def convert_to_documents(df):
    """Convertit les données Excel en documents pour Pinecone"""
    print("\n🔄 Conversion des données en format RAG...")
    
    documents = []
    
    for index, row in df.iterrows():
        try:
            # Extraire les informations du produit avec le format demandé par l'utilisateur
            nom = str(row.get('nom', 'Produit inconnu')).strip()
            id_prod = str(row.get('id', f'PROD_{index+1:03d}')).strip()
            stock = int(row.get('stock_disponible', 0)) if pd.notna(row.get('stock_disponible')) else 0
            prix_vente = float(row.get('prix_vente_conseille', 0)) if pd.notna(row.get('prix_vente_conseille')) else 0.0
            prix_achat = float(row.get('prix_achat', 0)) if pd.notna(row.get('prix_achat')) else 0.0
            marge_min = float(row.get('marge_minimum', 0)) if pd.notna(row.get('marge_minimum')) else 0.0
            
            # Extraire les autres informations disponibles
            categorie = str(row.get('categorie', 'Emballage')).strip() if pd.notna(row.get('categorie')) else 'Emballage'
            description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else ''
            
            # Créer le contenu JSON structuré
            product_data = {
                "id": id_prod,
                "nom": nom,
                "categorie": categorie,
                "description": description,
                "stock_disponible": stock,
                "prix_vente_conseille": prix_vente,
                "prix_achat": prix_achat,
                "marge_minimum": marge_min,
                "format_display": f"{id_prod} {nom} Qté {stock} Prix : {prix_vente:.2f}€",
                "recherche_keywords": [
                    nom.lower(),
                    id_prod.lower(),
                    categorie.lower()
                ]
            }
            
            # Ajouter d'autres colonnes disponibles
            for col in df.columns:
                if col not in ['id', 'nom', 'categorie', 'description', 'stock_disponible', 
                              'prix_vente_conseille', 'prix_achat', 'marge_minimum']:
                    value = row.get(col)
                    if pd.notna(value):
                        product_data[col] = str(value).strip()
            
            # Créer le document pour Pinecone
            page_content = json.dumps(product_data, ensure_ascii=False, indent=2)
            
            doc = Document(
                page_content=page_content,
                metadata={
                    "source": f"Articles.xlsx - ligne {index+1}",
                    "id": id_prod,
                    "nom": nom,
                    "categorie": categorie,
                    "stock": stock,
                    "prix": prix_vente
                }
            )
            
            documents.append(doc)
            
            if (index + 1) % 10 == 0:
                print(f"   📦 {index + 1} produits convertis...")
                
        except Exception as e:
            print(f"❌ Erreur conversion ligne {index+1}: {e}")
            continue
    
    print(f"✅ {len(documents)} documents créés avec succès")
    return documents

def setup_pinecone():
    """Configure la connexion Pinecone"""
    print("\n🔍 Configuration de Pinecone...")
    
    load_dotenv()
    
    # Vérifier les variables d'environnement
    api_key = os.environ.get("PINECONE_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("❌ PINECONE_API_KEY manquante dans le fichier .env")
    if not openai_key:
        raise ValueError("❌ OPENAI_API_KEY manquante dans le fichier .env")
    
    # Initialiser Pinecone
    pc = Pinecone(api_key=api_key)
    
    # Vérifier l'index
    index_name = "sample-index"
    indexes = pc.list_indexes()
    
    if index_name not in [idx.name for idx in indexes]:
        print(f"❌ Index '{index_name}' introuvable")
        print(f"📋 Index disponibles: {[idx.name for idx in indexes]}")
        raise ValueError(f"Index '{index_name}' n'existe pas")
    
    index = pc.Index(index_name)
    
    # Initialiser les embeddings
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=openai_key
    )
    
    # Créer le vector store
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    
    print(f"✅ Connexion Pinecone établie sur l'index '{index_name}'")
    
    return vector_store, index

def check_existing_data(vector_store, index):
    """Vérifie les données existantes dans Pinecone"""
    print("\n📊 Vérification des données existantes...")
    
    stats = index.describe_index_stats()
    total_vectors = stats.total_vector_count
    
    print(f"📈 Nombre de vecteurs existants: {total_vectors}")
    
    if total_vectors > 0:
        # Récupérer quelques exemples
        try:
            results = vector_store.similarity_search("produit", k=3)
            print(f"📦 Exemples de produits existants:")
            for i, doc in enumerate(results[:3]):
                try:
                    content = json.loads(doc.page_content)
                    format_display = content.get('format_display', content.get('nom', 'Produit'))
                    print(f"   {i+1}. {format_display}")
                except:
                    print(f"   {i+1}. {doc.page_content[:100]}...")
        except Exception as e:
            print(f"⚠️ Erreur lecture exemples: {e}")
    
    return total_vectors

def add_documents_to_pinecone(vector_store, documents):
    """Ajoute les documents à Pinecone"""
    print(f"\n📤 Ajout de {len(documents)} documents à Pinecone...")
    
    try:
        # Générer des IDs uniques
        uuids = [f"prod_{i:04d}" for i in range(len(documents))]
        
        # Ajouter par petits lots pour éviter les timeouts
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_ids = uuids[i:i+batch_size]
            
            print(f"   📦 Ajout du lot {i//batch_size + 1} ({len(batch_docs)} documents)...")
            vector_store.add_documents(documents=batch_docs, ids=batch_ids)
        
        print(f"✅ {len(documents)} documents ajoutés avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout: {e}")
        return False

def test_search(vector_store):
    """Test de recherche après ajout"""
    print("\n🔎 Test de recherche...")
    
    test_queries = [
        "boîte carton",
        "emballage 300mm", 
        "film plastique",
        "palette"
    ]
    
    for query in test_queries:
        try:
            results = vector_store.similarity_search(query, k=2)
            print(f"\n🔍 Recherche '{query}': {len(results)} résultats")
            
            for i, doc in enumerate(results):
                try:
                    content = json.loads(doc.page_content)
                    format_display = content.get('format_display', content.get('nom', 'Produit'))
                    print(f"   {i+1}. {format_display}")
                except:
                    print(f"   {i+1}. {doc.page_content[:100]}...")
                    
        except Exception as e:
            print(f"❌ Erreur recherche '{query}': {e}")

def main():
    """Fonction principale"""
    print("🚀 === ALIMENTATION DU RAG AVEC DONNÉES EXCEL ===\n")
    
    try:
        # 1. Charger les données Excel
        df = load_inventory_data()
        if df is None:
            return
        
        # 2. Convertir en documents
        documents = convert_to_documents(df)
        if not documents:
            print("❌ Aucun document créé")
            return
        
        # 3. Configurer Pinecone
        vector_store, index = setup_pinecone()
        
        # 4. Vérifier données existantes
        existing_count = check_existing_data(vector_store, index)
        
        # 5. Confirmation utilisateur
        print(f"\n⚠️ Vous allez ajouter {len(documents)} nouveaux produits")
        print(f"   (La base contient déjà {existing_count} vecteurs)")
        
        response = input("\n▶️ Continuer ? (o/n): ").lower().strip()
        if response not in ['o', 'oui', 'y', 'yes']:
            print("❌ Annulation par l'utilisateur")
            return
        
        # 6. Ajouter les documents
        success = add_documents_to_pinecone(vector_store, documents)
        
        if success:
            # 7. Test de recherche
            test_search(vector_store)
            
            print(f"\n🎉 RAG alimenté avec succès !")
            print(f"   📊 {len(documents)} produits ajoutés")
            print(f"   🔎 Recherche RAG opérationnelle")
            print(f"\n▶️ Vous pouvez maintenant tester les alternatives:")
            print(f"   python test_rag_status.py")
            print(f"   python debug_app.py")
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        print(f"\n💡 Vérifiez votre fichier .env avec:")
        print(f"   OPENAI_API_KEY=votre_clé")
        print(f"   PINECONE_API_KEY=votre_clé")

if __name__ == "__main__":
    main() 