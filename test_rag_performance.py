#!/usr/bin/env python3
"""
Test de performance : Ancien RAG vs RAG Optimisé
==============================================

Compare les performances entre :
- Version originale : fetch_docs() 
- Version optimisée : fetch_docs_optimized()
"""

import time
import sys
import os
from datetime import datetime

# Ajouter le chemin du projet
sys.path.insert(0, os.path.abspath('.'))

def test_performance_comparison():
    """Compare les performances des deux versions du RAG"""
    
    print("🚀 === TEST DE PERFORMANCE RAG ===\n")
    
    # Test cases
    test_cases = [
        {
            "name": "Produit OK (stock + marge suffisants)",
            "product_id": "CAISSE US SC 200X150X150MM",
            "required_qty": 10,
            "prix_propose": 1.5
        },
        {
            "name": "Rupture de stock",
            "product_id": "CAISSE US SC 450X300X230MM", 
            "required_qty": 5000,
            "prix_propose": 0.7
        },
        {
            "name": "Marge insuffisante",
            "product_id": "CAISSE US SC 400X300X300MM",
            "required_qty": 100, 
            "prix_propose": 0.25
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 === TEST {i}: {test_case['name']} ===")
        print(f"Produit: {test_case['product_id']}")
        print(f"Quantité: {test_case['required_qty']}")
        print(f"Prix proposé: {test_case['prix_propose']}€")
        
        # Test version originale
        print(f"\n⏱️ Test version ORIGINALE...")
        start_time = time.time()
        try:
            from rag.retrieval import fetch_docs
            result_original = fetch_docs(
                query=f"Vérification {test_case['product_id']}",
                product_id=test_case['product_id'],
                required_qty=test_case['required_qty'],
                prix_propose=test_case['prix_propose']
            )
            time_original = time.time() - start_time
            alternatives_original = len(result_original.get('alternatives', []))
            
            print(f"✅ Version originale terminée en {time_original:.2f}s")
            print(f"   - {alternatives_original} alternatives trouvées")
            
        except Exception as e:
            print(f"❌ Erreur version originale: {e}")
            time_original = float('inf')
            alternatives_original = 0
        
        # Test version optimisée  
        print(f"\n⚡ Test version OPTIMISÉE...")
        start_time = time.time()
        try:
            from rag.retrieval_optimized import fetch_docs_optimized
            result_optimized = fetch_docs_optimized(
                query=f"Vérification {test_case['product_id']}",
                product_id=test_case['product_id'],
                required_qty=test_case['required_qty'],
                prix_propose=test_case['prix_propose']
            )
            time_optimized = time.time() - start_time
            alternatives_optimized = len(result_optimized.get('alternatives', []))
            
            print(f"✅ Version optimisée terminée en {time_optimized:.2f}s")
            print(f"   - {alternatives_optimized} alternatives trouvées")
            
        except Exception as e:
            print(f"❌ Erreur version optimisée: {e}")
            time_optimized = float('inf')
            alternatives_optimized = 0
        
        # Comparaison
        print(f"\n📊 === COMPARAISON TEST {i} ===")
        if time_original != float('inf') and time_optimized != float('inf'):
            speedup = time_original / time_optimized
            print(f"⏱️ Temps:")
            print(f"   - Original: {time_original:.2f}s")
            print(f"   - Optimisé: {time_optimized:.2f}s")
            print(f"   - Gain: {speedup:.1f}x plus rapide")
            
            print(f"🔍 Alternatives:")
            print(f"   - Original: {alternatives_original}")
            print(f"   - Optimisé: {alternatives_optimized}")
            
            if speedup > 1:
                print(f"🎉 OPTIMISATION RÉUSSIE !")
            else:
                print(f"⚠️ Performance dégradée")
        else:
            print(f"❌ Impossible de comparer (erreurs)")
        
        print(f"\n" + "="*60)

def test_cache_performance():
    """Test l'efficacité du cache"""
    print(f"\n🔄 === TEST CACHE ===")
    
    try:
        from rag.retrieval_optimized import fetch_docs_optimized, clear_caches
        
        # Premier appel (sans cache)
        print("📞 Premier appel (population du cache)...")
        start_time = time.time()
        result1 = fetch_docs_optimized(
            query="Test cache",
            product_id="CAISSE US SC 200X150X150MM",
            required_qty=50,
            prix_propose=1.0
        )
        time1 = time.time() - start_time
        
        # Deuxième appel (avec cache)
        print("📞 Deuxième appel (avec cache)...")
        start_time = time.time()
        result2 = fetch_docs_optimized(
            query="Test cache", 
            product_id="CAISSE US SC 200X150X150MM",
            required_qty=50,
            prix_propose=1.0
        )
        time2 = time.time() - start_time
        
        print(f"\n📊 Résultats cache:")
        print(f"   - Premier appel: {time1:.2f}s")
        print(f"   - Deuxième appel: {time2:.2f}s")
        if time2 > 0:
            cache_speedup = time1 / time2
            print(f"   - Gain cache: {cache_speedup:.1f}x plus rapide")
        
        # Nettoyage
        clear_caches()
        print(f"🧹 Cache nettoyé")
        
    except Exception as e:
        print(f"❌ Erreur test cache: {e}")

def analyze_bottlenecks():
    """Analyse les goulots d'étranglement du RAG original"""
    print(f"\n🔍 === ANALYSE DES GOULOTS D'ÉTRANGLEMENT ===")
    
    print(f"📊 Problèmes identifiés dans la version originale:")
    print(f"   1. 🐌 Recherches Pinecone multiples:")
    print(f"      - 1 recherche principale (k=10)")
    print(f"      - 3 recherches supplémentaires (k=5 chacune)")
    print(f"      - 1 recherche fiche technique par alternative")
    print(f"      ➜ TOTAL: 25+ appels Pinecone par requête")
    
    print(f"\n   2. 🔄 Boucle sur TOUT l'inventaire:")
    print(f"      - 407 produits analysés un par un")
    print(f"      - 1 recherche Pinecone par produit")
    print(f"      ➜ TOTAL: Jusqu'à 407 appels supplémentaires")
    
    print(f"\n   3. 💾 Calculs répétés:")
    print(f"      - Similarité technique pour chaque produit")
    print(f"      - Accès CSV multiples")
    print(f"      - Pas de cache")
    
    print(f"\n✅ Optimisations appliquées:")
    print(f"   1. ⚡ Recherche Pinecone unique et ciblée")
    print(f"   2. 🎯 Filtrage précoce par catégorie")
    print(f"   3. 📦 Cache intelligent des résultats")
    print(f"   4. 🔢 Limitation du nombre d'analyses")
    print(f"   5. 🚀 Calculs optimisés de similarité")

if __name__ == "__main__":
    print(f"🕐 Début des tests de performance: {datetime.now().strftime('%H:%M:%S')}")
    
    # Analyse théorique
    analyze_bottlenecks()
    
    # Tests de performance
    test_performance_comparison()
    
    # Test du cache
    test_cache_performance()
    
    print(f"\n🏁 Tests terminés: {datetime.now().strftime('%H:%M:%S')}")
    print(f"\n💡 Recommandation: Utilisez fetch_docs_optimized() pour de meilleures performances !") 