# 🚀 Configuration du RAG - Guide rapide

## 📋 Étapes de configuration

### 1. **Créer le fichier .env**

Créez un fichier `.env` à la racine du projet avec :

```bash
# Clés API obligatoires
OPENAI_API_KEY=sk-votre_cle_openai_ici
PINECONE_API_KEY=votre_cle_pinecone_ici
PINECONE_ENVIRONMENT=gcp-starter
```

> **Où obtenir les clés ?**
> - OpenAI : https://platform.openai.com/api-keys
> - Pinecone : https://app.pinecone.io/

### 2. **Vérifier l'état du système**

```bash
python test_rag_status.py
```

**Résultat attendu :**
- ✅ Variables d'environnement: ✅
- ✅ Données d'inventaire: ✅ 
- ❌ Base vectorielle Pinecone: ❌ (vide)
- ❌ Recherche RAG: ❌

### 3. **Alimenter le RAG avec vos données**

```bash
python alimenter_rag.py
```

Ce script va :
- 📊 Charger `data/Articles.xlsx` 
- 🔄 Convertir au format RAG avec le format demandé [[memory:2717753]]
- 📤 Uploader vers Pinecone
- 🔎 Tester la recherche

**Format des produits :** 
```
76000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€
```

### 4. **Tester les alternatives**

```bash
python debug_app.py
```

## 🎯 Test rapide

Une fois le RAG alimenté, testez une commande avec rupture de stock :

```python
from ninia.agent import CommandProcessor

agent = CommandProcessor()
result = agent.process_order("Je veux 500 unités de CAISSE US SC 450X300X230MM")
```

**Résultat attendu :**
- 🔍 Détection rupture de stock
- 🤖 Le LLM propose des alternatives similaires
- 💡 Solutions commerciales (livraison partielle, substitution, etc.)

## 🛠️ Résolution de problèmes

### **Erreur "Index non trouvé"**
Créez l'index Pinecone :
```bash
# Dans votre console Pinecone
# Créer un index nommé "sample-index"  
# Dimension: 3072 (pour text-embedding-3-large)
```

### **Erreur "No module named..."**
Installez les dépendances :
```bash
pip install -r requirements.txt
```

### **RAG vide après alimentation**
Vérifiez le format de `data/Articles.xlsx` :
- Colonnes requises : `id`, `nom`, `stock_disponible`, `prix_vente_conseille`

## ✅ Validation finale

Après configuration complète, `python test_rag_status.py` doit afficher :
- ✅ Variables d'environnement: ✅
- ✅ Données d'inventaire: ✅ 
- ✅ Base vectorielle Pinecone: ✅
- ✅ Recherche RAG: ✅

🎉 **Système prêt !** Le LLM peut maintenant proposer des alternatives intelligentes. 