#!/usr/bin/env python3
"""
Version optimisée du système de recherche RAG
=============================================

Optimisations appliquées :
- Réduction drastique des appels Pinecone
- Cache intelligent des résultats
- Filtrage précoce des alternatives
- Traitement par batch
"""

import pandas as pd
from typing import Dict, List, Optional, Union, TypedDict
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
import re
from .settings import settings
from .retrieval import (
    ProductInfo, format_product_info, get_stock, 
    normalize_name, _inventory_df, extract_technical_features, 
    calculate_technical_similarity
)

# Cache global pour éviter les recherches répétées
_pinecone_cache = {}
_similarity_cache = {}

def fetch_docs_optimized(query: str, product_id: str = None, required_qty: int = 0, prix_propose: float = None) -> Dict[str, Union[ProductInfo, List[ProductInfo]]]:
    """
    Version optimisée de fetch_docs avec beaucoup moins d'appels API
    
    Optimisations :
    1. Une seule recherche Pinecone principale 
    2. Filtrage intelligent basé sur les catégories
    3. Cache des résultats
    4. Limitation du nombre d'alternatives analysées
    """
    print("\n=== DÉBUT RECHERCHE RAG OPTIMISÉE ===")
    print(f"Requête : {query}")
    print(f"Produit demandé : {product_id}")
    print(f"Quantité requise : {required_qty}")
    print(f"Prix proposé : {prix_propose}€")
    
    # Si pas de product_id, recherche simple
    if not product_id:
        print("Pas de product_id, recherche simple")
        return {"produit": None, "alternatives": []}

    # Récupération des informations du produit demandé
    print(f"\nRecherche du produit : {product_id}")
    _prod_row = _inventory_df.loc[_inventory_df["nom"] == product_id]
    if _prod_row.empty:
        _prod_row = _inventory_df.loc[_inventory_df["product_id"] == product_id]
    
    if _prod_row.empty:
        print("Produit non trouvé dans l'inventaire")
        return {"produit": None, "alternatives": []}
    
    # Information du produit demandé
    stock = get_stock(product_id)
    produit_info = format_product_info(
        product_name=_prod_row["nom"].iloc[0],
        row=_prod_row.iloc[0],
        stock_dispo=stock,
        description=None  # On évite la recherche de fiche technique ici
    )
    
    # Calcul de la marge
    if prix_propose is not None and produit_info.get('prix_achat') is not None:
        marge_actuelle_calculee = prix_propose - produit_info['prix_achat']
    elif produit_info.get('prix_vente_conseille') is not None and produit_info.get('prix_achat') is not None:
        marge_actuelle_calculee = produit_info['prix_vente_conseille'] - produit_info['prix_achat']
    else:
        marge_actuelle_calculee = 0.0

    marge_minimum_produit = produit_info.get('marge_minimum', 0.0)
    marge_suffisante_calculee = marge_actuelle_calculee >= marge_minimum_produit

    # Enrichir produit_info
    produit_info['marge_actuelle'] = marge_actuelle_calculee
    produit_info['marge_suffisante'] = marge_suffisante_calculee
    produit_info['prix_propose_retenu'] = prix_propose
    
    print(f"\nVérification des conditions :")
    print(f"- Stock disponible : {stock} (requis : {required_qty})")
    print(f"- Marge actuelle : {produit_info['marge_actuelle']:.2f}€ (minimum requis : {produit_info['marge_minimum']}€)")
    print(f"- Marge suffisante : {'Oui' if produit_info['marge_suffisante'] else 'Non'}")
    
    # Si stock ET marge suffisants, recherche limitée d'alternatives
    if stock >= required_qty and produit_info['marge_suffisante']:
        print("✅ Produit OK - Recherche d'alternatives limitée")
        alternatives = find_limited_alternatives(produit_info, required_qty, prix_propose)
    else:
        print("❌ Problème détecté - Recherche d'alternatives étendue")
        alternatives = find_extended_alternatives(produit_info, required_qty, prix_propose)
    
    print(f"\nNombre d'alternatives trouvées : {len(alternatives)}")
    print("=== FIN RECHERCHE RAG OPTIMISÉE ===\n")

    return {
        "produit": produit_info,
        "alternatives": alternatives
    }

def find_limited_alternatives(produit_info: Dict, required_qty: int, prix_propose: float = None) -> List[Dict]:
    """
    Recherche limitée d'alternatives pour un produit qui fonctionne déjà
    Maximum 3-5 alternatives de la même catégorie
    """
    print("🔍 Recherche limitée d'alternatives...")
    
    # Extraire la catégorie du produit (CAISSE, BOITE, etc.)
    product_name = produit_info['name'].lower()
    category = extract_product_category(product_name)
    
    if not category:
        return []
    
    # Filtrer l'inventaire par catégorie similaire
    candidates = _inventory_df[
        _inventory_df['nom'].str.lower().str.contains(category, na=False) &
        (_inventory_df['nom'] != produit_info['name'])
    ].head(20)  # Maximum 20 candidats pour éviter trop de calculs
    
    alternatives = []
    for _, row in candidates.iterrows():
        # Vérification rapide : stock > 0 et prix cohérent
        product_stock = get_stock(row['nom'])
        if product_stock <= 0:
            continue
            
        alt_info = format_product_info(
            product_name=row['nom'],
            row=row,
            stock_dispo=product_stock,
            description=None
        )
        
        # Calcul de similarité rapide par nom
        similarity = calculate_name_similarity(produit_info['name'], row['nom'])
        if similarity < 0.3:  # Seuil minimum
            continue
            
        # Calcul de marge
        prix_achat = float(row["prix_achat"]) if pd.notna(row["prix_achat"]) else 0.0
        if prix_propose:
            marge_alt = prix_propose - prix_achat
        else:
            marge_alt = float(row["prix_vente_conseille"]) - prix_achat
            
        alt_info.update({
            'score': 0.8,  # Score par défaut
            'similarite_technique': similarity,
            'marge': marge_alt,
            'marge_minimum': float(row["marge_minimum"]),
            'stock_suffisant': product_stock >= required_qty,
            'marge_suffisante': marge_alt >= float(row["marge_minimum"])
        })
        
        alternatives.append(alt_info)
        
        if len(alternatives) >= 5:  # Limite à 5 alternatives
            break
    
    # Tri par similarité
    alternatives.sort(key=lambda x: x['similarite_technique'], reverse=True)
    print(f"✅ {len(alternatives)} alternatives limitées trouvées")
    return alternatives

def find_extended_alternatives(produit_info: Dict, required_qty: int, prix_propose: float = None) -> List[Dict]:
    """
    Recherche étendue d'alternatives pour un produit problématique
    Utilise une seule recherche Pinecone optimisée
    """
    print("🔍 Recherche étendue d'alternatives...")
    
    # Import tardif pour éviter les problèmes de dépendances circulaires
    from .retrieval import _vector_store
    
    # Cache key pour éviter les recherches répétées
    cache_key = f"{produit_info['name']}_{required_qty}_{prix_propose}"
    if cache_key in _pinecone_cache:
        print("📦 Utilisation du cache Pinecone")
        docs_and_scores = _pinecone_cache[cache_key]
    else:
        # UNE SEULE recherche Pinecone optimisée
        category = extract_product_category(produit_info['name'])
        query_optimized = f"Alternative {category} pour {produit_info['name']} stock marge"
        
        print(f"🚀 Recherche Pinecone : {query_optimized}")
        docs_and_scores = _vector_store.similarity_search_with_score(
            query_optimized,
            k=15,  # Récupérer plus de résultats en une fois
        )
        _pinecone_cache[cache_key] = docs_and_scores
    
    print(f"📊 {len(docs_and_scores)} résultats Pinecone")
    
    # Extraction rapide des noms de produits des documents
    candidate_products = set()
    for doc, score in docs_and_scores:
        if score < 0.2:  # Filtrage précoce
            continue
            
        content = doc.page_content.lower()
        # Recherche rapide des produits dans le contenu
        for product in _inventory_df['nom'].head(100):  # Limite à 100 premiers produits
            if product.lower() in content and product != produit_info['name']:
                candidate_products.add(product)
    
    print(f"🎯 {len(candidate_products)} candidats identifiés")
    
    # Analyse rapide des candidats
    alternatives = []
    for product in list(candidate_products)[:20]:  # Maximum 20 analyses
        alt_info = analyze_alternative_fast(product, required_qty, prix_propose, produit_info)
        if alt_info:
            alternatives.append(alt_info)
    
    # Tri par score global
    alternatives.sort(key=lambda x: x.get('score_global', 0), reverse=True)
    
    print(f"✅ {len(alternatives)} alternatives étendues trouvées")
    return alternatives[:8]  # Maximum 8 alternatives finales

def analyze_alternative_fast(product: str, required_qty: int, prix_propose: float, produit_info: Dict) -> Optional[Dict]:
    """
    Analyse rapide d'une alternative avec récupération des fiches techniques
    """
    try:
        # Import tardif pour éviter les problèmes de dépendances circulaires
        from .retrieval import _vector_store
        
        # Récupération rapide des données
        prod_row = _inventory_df.loc[_inventory_df["nom"] == product]
        if prod_row.empty:
            return None
            
        prod_row = prod_row.iloc[0]
        product_stock = get_stock(product)
        
        # Calculs de base
        prix_achat = float(prod_row["prix_achat"]) if pd.notna(prod_row["prix_achat"]) else 0.0
        marge_min = float(prod_row["marge_minimum"]) if pd.notna(prod_row["marge_minimum"]) else 0.0
        
        if prix_propose:
            marge_alt = prix_propose - prix_achat
        else:
            marge_alt = float(prod_row["prix_vente_conseille"]) - prix_achat
        
        # Similarité rapide
        similarity = calculate_name_similarity(produit_info['name'], product)
        
        # Score global simple
        score_stock = min(product_stock / max(required_qty, 1), 1.0)
        score_marge = 1.0 if marge_alt >= marge_min else 0.0
        score_global = (similarity * 0.5) + (score_stock * 0.3) + (score_marge * 0.2)
        
        # Filtre : garder seulement les alternatives intéressantes
        if similarity < 0.2 or score_global < 0.3:
            return None
        
        # ✅ CORRECTION CRITIQUE: Récupérer la fiche technique pour LLM
        print(f"   📄 Récupération fiche pour {product}...")
        tech_docs = _vector_store.similarity_search_with_score(
            f"fiche technique {product}",
            k=1
        )
        description = tech_docs[0][0].page_content if tech_docs else None
        print(f"   {'✅' if description else '❌'} Fiche: {len(description) if description else 0} chars")
        
        alt_info = format_product_info(
            product_name=product,
            row=prod_row,
            stock_dispo=product_stock,
            description=description  # ✅ INCLURE la fiche technique !
        )
        
        alt_info.update({
            'score': 0.7,
            'similarite_technique': similarity,
            'marge': marge_alt,
            'marge_minimum': marge_min,
            'stock_suffisant': product_stock >= required_qty,
            'marge_suffisante': marge_alt >= marge_min,
            'score_global': score_global
        })
        
        return alt_info
        
    except Exception as e:
        print(f"❌ Erreur analyse {product}: {e}")
        return None

def extract_product_category(product_name: str) -> str:
    """
    Extrait la catégorie principale d'un produit
    """
    product_name = product_name.lower()
    
    categories = {
        'caisse': ['caisse'],
        'boite': ['boite', 'boîte'],
        'etui': ['etui', 'étui'],
        'film': ['film'],
        'sac': ['sac'],
        'palette': ['palette'],
        'carton': ['carton']
    }
    
    for category, keywords in categories.items():
        if any(keyword in product_name for keyword in keywords):
            return category
    
    return 'emballage'  # Catégorie par défaut

def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calcul rapide de similarité entre deux noms de produits
    """
    cache_key = f"{name1}|{name2}"
    if cache_key in _similarity_cache:
        return _similarity_cache[cache_key]
    
    name1_clean = normalize_name(name1).lower()
    name2_clean = normalize_name(name2).lower()
    
    # Similarité par mots communs
    words1 = set(name1_clean.split())
    words2 = set(name2_clean.split())
    
    if not words1 or not words2:
        similarity = 0.0
    else:
        common_words = len(words1.intersection(words2))
        total_words = len(words1.union(words2))
        similarity = common_words / total_words
    
    # Bonus pour catégorie identique
    if extract_product_category(name1) == extract_product_category(name2):
        similarity += 0.2
    
    # Normalisation
    similarity = min(similarity, 1.0)
    
    _similarity_cache[cache_key] = similarity
    return similarity

def clear_caches():
    """Vide tous les caches pour libérer la mémoire"""
    global _pinecone_cache, _similarity_cache
    _pinecone_cache.clear()
    _similarity_cache.clear()
    print("🧹 Caches vidés") 