# Documentation du module retrieval.py

Ce module gère la recherche sémantique et la gestion des stocks pour le système de RAG (Retrieval Augmented Generation).

## Table des matières
1. [Configuration et Initialisation](#configuration-et-initialisation)
2. [Gestion des Stocks](#gestion-des-stocks)
3. [Recherche Sémantique](#recherche-sémantique)
4. [Traitement des Alternatives](#traitement-des-alternatives)

## Configuration et Initialisation

### Imports et Configuration Initiale
```python
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
```

Le module utilise :
- `pinecone` pour la base de données vectorielle
- `langchain_openai` pour la génération d'embeddings
- `pandas` pour la gestion des données de stock

### Chargement des Données de Stock
```python
_inventory_df = pd.read_csv(
    os.path.join(os.path.dirname(__file__), "../data/inventaire_stock.csv"),
    sep=';',
    encoding='utf-8'
)
```
- Charge l'inventaire depuis un fichier CSV
- Harmonise les noms de colonnes pour une utilisation cohérente

### Initialisation de Pinecone
```python
_pc = Pinecone(
    api_key=settings.pinecone_api_key,
    environment=settings.pinecone_env,
)
_index = _pc.Index(settings.index_name)
```
- Configure la connexion à Pinecone
- Initialise l'index vectoriel pour la recherche sémantique

## Gestion des Stocks

### Fonction get_stock
```python
def get_stock(product_id: str) -> int:
    """Retourne la quantité disponible en stock."""
```
**Paramètres** :
- `product_id` : Identifiant ou nom du produit

**Fonctionnement** :
1. Recherche le produit par nom ou ID dans l'inventaire
2. Calcule le stock disponible : `quantite_stock - commandes_alivrer`
3. Retourne 0 si le produit n'est pas trouvé

## Recherche Sémantique

### Configuration des Embeddings
```python
_embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=settings.openai_api_key,
)
```
- Utilise le modèle OpenAI pour générer des embeddings
- Ces embeddings permettent la recherche sémantique

### Fonction fetch_docs
```python
def fetch_docs(query: str, product_id: str = None, required_qty: int = 0) -> List[str]:
    """Recherche des documents pertinents et vérifie les stocks."""
```
**Paramètres** :
- `query` : La requête de recherche
- `product_id` : Identifiant du produit (optionnel)
- `required_qty` : Quantité demandée (optionnel)

**Comportement** :
1. **Sans product_id** :
   - Effectue une recherche sémantique simple
   - Retourne les documents pertinents

2. **Avec product_id** :
   - Vérifie d'abord le stock du produit demandé
   - Si stock suffisant : retourne les informations de stock
   - Si stock insuffisant : recherche des alternatives

## Traitement des Alternatives

### Structure des Informations de Stock
```python
stock_info = (
    f"PRODUIT DEMANDÉ :\n"
    f"Nom : {product_name}\n"
    f"Quantité demandée : {required_qty}\n"
    f"Stock initial : {total}\n"
    f"Commandes à livrer : {pending}\n"
    f"Stock disponible : {available}\n"
    f"Délai de réapprovisionnement : {delai}\n"
)
```
- Format standardisé des informations de stock
- Inclut toutes les informations pertinentes pour le LLM

### Recherche d'Alternatives
La fonction vérifie pour chaque alternative potentielle :
1. Score de similarité suffisant
2. Stock disponible suffisant
3. Pertinence par rapport à la demande

### Format des Alternatives
```python
alternative_info = (
    f"\nALTERNATIVE DISPONIBLE :\n"
    f"Nom : {product}\n"
    f"Stock disponible : {product_stock}\n"
    f"Délai de réapprovisionnement : {prod_row['delai_livraison']}\n"
    f"Description du produit :\n"
    f"{content}\n"
)
```
- Structure claire pour chaque alternative
- Inclut stock et délai de réapprovisionnement
- Ajoute la description complète du produit

## Fonction fetch_docs_for_products
```python
def fetch_docs_for_products(query: str, orders: Dict[str, int]) -> Dict[str, List[str]]:
    """Traite plusieurs produits en une seule requête."""
```
**Utilisation** :
- Traite plusieurs commandes en parallèle
- Retourne un dictionnaire avec les résultats pour chaque produit

## Bonnes Pratiques d'Utilisation

1. **Vérification des Stocks** :
   ```python
   stock = get_stock("nom_produit")
   if stock >= quantite_demandee:
       # Traiter la commande
   ```

2. **Recherche d'Alternatives** :
   ```python
   resultats = fetch_docs(
       query="description du besoin",
       product_id="produit_rupture",
       required_qty=100
   )
   ```

3. **Traitement Multiple** :
   ```python
   commandes = {
       "produit1": 50,
       "produit2": 30
   }
   resultats = fetch_docs_for_products("query", commandes)
   ``` 