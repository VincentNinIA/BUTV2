#!/bin/bash

# Script simplifié pour démarrer RAG-NINIA
# Force l'activation de l'environnement virtuel

echo "🦋 Démarrage de RAG-NINIA..."

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "app_streamlit/chatbot_ninia.py" ]; then
    echo "❌ Erreur: Veuillez exécuter ce script depuis le répertoire RAG-NINIA"
    exit 1
fi

# Désactiver tout environnement virtuel existant
deactivate 2>/dev/null || true

# Activer l'environnement virtuel
echo "🔄 Activation de l'environnement virtuel..."
source venv/bin/activate

# Vérifier que le bon streamlit est utilisé
if [[ $(which streamlit) == *"venv/bin/streamlit" ]]; then
    echo "✅ Environnement virtuel correctement activé"
else
    echo "❌ Problème d'activation de l'environnement virtuel"
    echo "Streamlit trouvé : $(which streamlit)"
    exit 1
fi

# Lancer l'application
echo "🚀 Lancement de l'application..."
echo "L'application va s'ouvrir sur : http://localhost:8501"
echo ""
streamlit run app_streamlit/chatbot_ninia.py 