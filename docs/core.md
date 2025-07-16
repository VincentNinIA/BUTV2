# Documentation du module core.py

Ce module est le cœur du système RAG, responsable de l'interaction avec le LLM (Large Language Model) et de la génération des réponses.

## Table des matières
1. [Configuration du LLM](#configuration-du-llm)
2. [Gestion du Contexte](#gestion-du-contexte)
3. [Génération des Réponses](#génération-des-réponses)
4. [Intégration avec le RAG](#intégration-avec-le-rag)

## Configuration du LLM

### Initialisation du Modèle
```python
_llm = ChatOpenAI(
    model="gpt-4.1",
    temperature=1,
    api_key=settings.openai_api_key,
)
```

**Configuration** :
- Utilise le modèle GPT-4.1 via l'API OpenAI
- `temperature=1` : Favorise la créativité dans les réponses
- Clé API chargée depuis les paramètres

## Gestion du Contexte

### Fonction build_stock_ctx
```python
def build_stock_ctx(product_id: str, required_qty: int = 0) -> str:
    """Construit un bloc de contexte avec stock initial, commandes et délai."""
```

**Paramètres** :
- `product_id` : Identifiant ou nom du produit
- `required_qty` : Quantité demandée (optionnel, défaut=0)

**Fonctionnement** :
1. Recherche le produit dans l'inventaire
2. Calcule les informations de stock
3. Formate le contexte avec :
   - Nom du produit
   - Stock initial
   - Commandes en attente
   - Stock disponible
   - Quantité demandée
   - Délai de réapprovisionnement

**Format de Sortie** :
```python
return (
    f"Produit : {row['nom']}\n"
    f"Stock initial : {total}\n"
    f"Commandes à livrer : {pending}\n"
    f"Stock disponible : {available}\n"
    f"Quantité demandée : {demanded}\n"
    f"Délai de réapprovisionnement estimé : {delai}\n\n"
)
```

## Génération des Réponses

### Fonction answer
```python
def answer(question: str, product_id: str = None, required_qty: int = 0) -> str:
    """Génère une réponse en utilisant le RAG et le LLM."""
```

**Paramètres** :
- `question` : La question ou demande de l'utilisateur
- `product_id` : Identifiant du produit (optionnel)
- `required_qty` : Quantité demandée (optionnel)

**Processus** :
1. **Récupération des Documents** :
   ```python
   docs = fetch_docs(question, product_id=product_id, required_qty=required_qty)
   ```
   - Utilise le module retrieval pour obtenir les informations pertinentes
   - Gère les cas d'erreur et d'absence de résultats

2. **Construction du Contexte** :
   ```python
   stock_ctx = docs[0] if product_id else ""
   alternatives_ctx = "\nALTERNATIVES SUGGÉRÉES :\n" + "\n".join(docs[1:])
   ```
   - Extrait les informations de stock du premier document
   - Formate les alternatives si présentes

3. **Assemblage du Prompt** :
   ```python
   full_context = (
       "INFORMATIONS DE STOCK :\n"
       f"{stock_ctx}\n"
       f"{alternatives_ctx}"
   ).strip()
   ```
   - Structure claire des informations
   - Séparation entre stock et alternatives

4. **Génération de la Réponse** :
   ```python
   system = SystemMessage(SYSTEM_PROMPT.format(context=full_context))
   user = HumanMessage(question)
   return _llm.invoke([system, user]).content
   ```
   - Utilise le prompt système avec le contexte
   - Ajoute la question de l'utilisateur
   - Invoque le LLM pour générer la réponse

## Intégration avec le RAG

### Flux de Données
1. Question utilisateur → `answer()`
2. `answer()` → `fetch_docs()` pour la recherche
3. Construction du contexte enrichi
4. Génération de la réponse via LLM

### Gestion des Erreurs
- Retourne un message d'erreur si aucune information pertinente n'est trouvée
- Gère les cas où le produit n'existe pas
- Fournit des réponses appropriées même sans alternatives

## Bonnes Pratiques d'Utilisation

1. **Requête Simple** :
   ```python
   reponse = answer("Quels sont vos produits disponibles ?")
   ```

2. **Vérification de Stock** :
   ```python
   reponse = answer(
       "Je voudrais commander des caisses",
       product_id="Caisses américaines simple cannelure",
       required_qty=100
   )
   ```

3. **Debug et Monitoring** :
   - Les prompts complets sont affichés avec `print("=== FULL PROMPT ===\n")`
   - Facilite le débogage et l'optimisation des réponses

## Points d'Attention

1. **Gestion du Contexte** :
   - Le contexte doit être structuré clairement
   - Les informations de stock doivent être précises
   - Les alternatives doivent être pertinentes

2. **Performance** :
   - Les appels au LLM sont asynchrones
   - La construction du contexte est optimisée
   - La recherche de documents est efficace

3. **Maintenance** :
   - Le code est modulaire et bien documenté
   - Les paramètres sont configurables via settings
   - Les messages d'erreur sont clairs et utiles 