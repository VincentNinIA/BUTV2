# Guide d'Installation - RAG-NINIA

## Prérequis
- Python 3.12 ou plus récent
- pip (installé avec Python)
- Git (optionnel, pour cloner le projet)

## Étapes d'Installation

### 1. Créer et Activer l'Environnement Virtuel
```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
# Sur macOS/Linux:
source venv/bin/activate
# Sur Windows:
# venv\Scripts\activate
```

### 2. Installer les Dépendances
```bash
# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Créer le Fichier de Configuration (.env)
Créez un fichier `.env` à la racine du projet avec le contenu suivant :

```env
# Clés API obligatoires
OPENAI_API_KEY=votre_cle_openai_ici
PINECONE_API_KEY=votre_cle_pinecone_ici

# Configuration Pinecone
PINECONE_ENV=eu-west-1-aws
PINECONE_INDEX_NAME=sample-index

# Paramètres RAG
TOP_K=4
SCORE_THRESHOLD=0.15
```

### 4. Configurer les Clés API

#### OpenAI API Key
1. Allez sur https://platform.openai.com/api-keys
2. Créez une nouvelle clé API
3. Copiez la clé dans le fichier `.env`

#### Pinecone API Key
1. Allez sur https://www.pinecone.io/
2. Créez un compte et obtenez votre clé API
3. Copiez la clé dans le fichier `.env`

### 5. Corriger les Problèmes de Compatibilité
```bash
# Désinstaller les versions problématiques
pip uninstall langchain_openai langchain_core -y

# Réinstaller avec des versions compatibles
pip install langchain_openai==0.0.5 langchain_core==0.1.23
```

### 6. Tester l'Installation
```bash
# Tester les modules principaux
python3 -c "import streamlit; print('Streamlit OK')"
python3 -c "from rag.settings import settings; print('Configuration OK')"
python3 -c "from ninia.agent import NiniaAgent; print('Agent OK')"
```

### 7. Lancer l'Application

**Option 1 : Utiliser le script de lancement (RECOMMANDÉ)**
```bash
# Sur macOS/Linux
./run_app.sh

# Sur Windows
run_app.bat
```

**Option 2 : Lancement manuel**
```bash
# Assurez-vous que l'environnement virtuel est activé
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate     # Windows

# Puis lancez l'application
streamlit run app_streamlit/chatbot_ninia.py
```

## Vérification de l'Installation

### Test Rapide
```bash
# Vérifier que tous les modules se chargent correctement
python3 -c "
from rag.settings import settings
from ninia.agent import NiniaAgent
from rag.core import answer
from rag.retrieval import fetch_docs
print('✅ Tous les modules sont fonctionnels')
"
```

### Lancer l'Application

**Méthode recommandée :**
```bash
# Sur macOS/Linux
./run_app.sh

# Sur Windows
run_app.bat
```

L'application devrait s'ouvrir sur `http://localhost:8501`

## Fonctionnalités Disponibles

- **Commandes** : "Je veux commander 10 caisses américaines"
- **Consultation stock** : "Quel est le stock des films étirables ?"
- **Alternatives** : "Alternative aux caisses Galia"
- **Questions générales** : "Comment vas-tu ?"

## Données
- **Inventaire** : Fichier `data/inventaire_stock.csv` avec 26 produits
- **Types de produits** : Caisses, films étirables, étuis fourreau, etc.

## Résolution des Problèmes

### Erreur "Module not found" ou "LangSmithParams"
Cette erreur survient quand le mauvais environnement Python est utilisé.

**Solution :**
```bash
# Vérifier l'environnement virtuel
which python3
echo $VIRTUAL_ENV

# Si le problème persiste, utiliser le script de lancement
./run_app.sh  # macOS/Linux
run_app.bat   # Windows

# Ou utiliser directement le Python de l'environnement virtuel
./venv/bin/python3 -m streamlit run app_streamlit/chatbot_ninia.py
```

### Erreur API Key
- Vérifiez que le fichier `.env` est bien à la racine
- Vérifiez que les clés API sont valides
- Redémarrez l'application après modification du `.env`

### Erreur Pinecone
- Vérifiez la région Pinecone (défaut: eu-west-1-aws)
- Vérifiez le nom de l'index
- Créez l'index si nécessaire sur le dashboard Pinecone

## Support
- Consultez la documentation dans le dossier `docs/`
- Vérifiez les logs d'erreur de Streamlit
- Testez chaque module individuellement 