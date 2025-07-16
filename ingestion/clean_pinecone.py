"""
Script pour nettoyer/vider l'index Pinecone
============================================

Ce script supprime toutes les données de l'index Pinecone pour permettre
une réinjection propre des nouvelles données du fichier Excel.
"""

import os
from pinecone import Pinecone
from rag.settings import settings

def clean_pinecone_index():
    """Vide complètement l'index Pinecone."""
    
    print("🧹 Nettoyage de l'index Pinecone...")
    
    # Connexion à Pinecone
    pc = Pinecone(
        api_key=settings.pinecone_api_key,
        environment=settings.pinecone_env,
    )
    
    # Connexion à l'index
    index = pc.Index(settings.index_name)
    
    try:
        # Récupérer des informations sur l'index
        stats = index.describe_index_stats()
        total_vectors = stats['total_vector_count']
        
        print(f"📊 Index actuel : {total_vectors} vecteurs")
        
        if total_vectors == 0:
            print("✅ L'index est déjà vide !")
            return
        
        # Supprimer tous les vecteurs
        print("🗑️  Suppression de tous les vecteurs...")
        index.delete(delete_all=True)
        
        print("✅ Index Pinecone nettoyé avec succès !")
        print("💡 Vous pouvez maintenant réinjecter les nouvelles données")
        
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage : {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🧹 NETTOYAGE DE L'INDEX PINECONE")
    print("=" * 50)
    
    confirmation = input("⚠️  Êtes-vous sûr de vouloir vider l'index Pinecone ? (oui/non): ")
    
    if confirmation.lower() in ['oui', 'yes', 'y', 'o']:
        success = clean_pinecone_index()
        if success:
            print("\n🎉 Nettoyage terminé ! L'index est prêt pour de nouvelles données.")
        else:
            print("\n💥 Échec du nettoyage.")
    else:
        print("❌ Opération annulée.") 