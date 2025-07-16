#!/bin/bash

# Script de lancement pour RAG-NINIA
# Utilise automatiquement l'environnement virtuel correct

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🦋 RAG-NINIA - Lancement de l'application${NC}"
echo "================================================="

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Environnement virtuel non trouvé !${NC}"
    echo "Veuillez d'abord installer l'environnement avec :"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Vérifier si le fichier .env existe
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Fichier .env manquant !${NC}"
    echo "Copie du template .env..."
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo -e "${GREEN}✅ Fichier .env créé à partir du template${NC}"
        echo -e "${YELLOW}⚠️  N'oubliez pas de configurer vos clés API dans le fichier .env${NC}"
    else
        echo -e "${RED}❌ Template .env.template non trouvé !${NC}"
        echo "Veuillez créer un fichier .env avec vos clés API"
        exit 1
    fi
fi

# Vérifier les clés API
echo -e "${BLUE}🔍 Vérification de la configuration...${NC}"
if grep -q "votre_cle_openai_ici" .env; then
    echo -e "${YELLOW}⚠️  La clé OpenAI n'est pas configurée !${NC}"
    echo "Veuillez modifier le fichier .env et remplacer 'votre_cle_openai_ici' par votre vraie clé OpenAI"
    exit 1
fi

if grep -q "votre_cle_pinecone_ici" .env; then
    echo -e "${YELLOW}⚠️  La clé Pinecone n'est pas configurée !${NC}"
    echo "Veuillez modifier le fichier .env et remplacer 'votre_cle_pinecone_ici' par votre vraie clé Pinecone"
    exit 1
fi

echo -e "${GREEN}✅ Configuration OK${NC}"

# Lancer l'application avec le bon environnement virtuel
echo -e "${BLUE}🚀 Lancement de l'application...${NC}"
echo "L'application va s'ouvrir dans votre navigateur à l'adresse : http://localhost:8501"
echo ""
echo -e "${YELLOW}💡 Pour arrêter l'application, appuyez sur Ctrl+C${NC}"
echo ""

# Activer l'environnement virtuel et utiliser son streamlit
source venv/bin/activate && streamlit run app_streamlit/chatbot_ninia.py 