#!/bin/bash

# Script pour corriger l'environnement virtuel
# Supprime l'ancien environnement et en crée un nouveau avec les bonnes versions

echo "🔧 Correction de l'environnement virtuel..."
echo "=========================================="

# Supprimer l'ancien environnement virtuel
echo "🗑️  Suppression de l'ancien environnement virtuel..."
rm -rf venv

# Créer un nouvel environnement virtuel
echo "🆕 Création d'un nouvel environnement virtuel..."
python3 -m venv venv

# Activer l'environnement virtuel
echo "🔌 Activation de l'environnement virtuel..."
source venv/bin/activate

# Mettre à jour pip
echo "📦 Mise à jour de pip..."
pip install --upgrade pip

# Installer les dépendances
echo "📚 Installation des dépendances..."
pip install -r requirements.txt

echo "✅ Environnement virtuel corrigé !"
echo "🚀 Vous pouvez maintenant lancer l'application avec : bash run_app.sh" 