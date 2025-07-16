# Documentation du Système RAG-NINIA

Ce dossier contient la documentation technique du système RAG (Retrieval Augmented Generation) avec l'agent NINIA.

## 🆕 NOUVELLE ARCHITECTURE (Version 2.0)

### 📚 Documentation principale

#### **[architecture_modulaire.md](./architecture_modulaire.md)** ⭐ **NOUVEAU**
**Documentation COMPLÈTE de l'architecture refactorisée :**
- Vue d'ensemble de la nouvelle architecture modulaire
- Guide détaillé de chaque module (extraction, analysis, alternatives, comments)
- Module de commentaires intelligents et alertes email automatiques
- Outils de debugging intégrés
- Exemples d'utilisation pratiques
- Guide de migration et troubleshooting

**👉 COMMENCEZ PAR CE DOCUMENT si vous découvrez le système**

#### **[systeme_alertes_email.md](./systeme_alertes_email.md)** ⭐ **NOUVEAU**
**Documentation DÉDIÉE au système d'alertes email automatiques :**
- Génération automatique d'emails d'alerte pour l'équipe commerciale
- Correction majeure des données de stock (bug "0 unité" résolu)
- Types d'alertes : rupture stock, marge insuffisante, problèmes généraux
- Intégration transparente dans l'interface Streamlit Mode Mail
- Templates spécialisés et détection intelligente des problèmes

### 📚 Documentation technique détaillée

#### core.md
Documentation du module central de génération de réponses :
- Configuration du LLM
- Gestion du contexte
- Génération des réponses
- Intégration avec le RAG

#### retrieval.md
Documentation détaillée du module de recherche et gestion des stocks :
- Configuration du système
- Gestion des stocks
- Recherche sémantique
- Traitement des alternatives

#### gestion_ruptures.md
Gestion des situations de rupture de stock et alternatives

#### nouveau_systeme_commande.md
Documentation du système de commande et validation

#### systeme_alertes_email.md ⭐ **NOUVEAU**
Documentation dédiée au système d'alertes email automatiques :
- Génération d'emails pour équipe commerciale
- Correction des données de stock (bug majeur résolu)
- Types d'alertes et templates spécialisés
- Intégration dans l'interface Streamlit

## Architecture du Système (Version 2.0)

```
RAG-NINIA/
├── ninia/                      # 🤖 Agent NINIA modulaire
│   ├── agent.py               # Agent principal unifié
│   ├── extraction/            # 🔍 Module d'extraction
│   │   ├── product_parser.py  # Extraction produits/quantités
│   │   └── text_extractor.py  # Normalisation et prix
│   ├── analysis/              # 📊 Module d'analyse
│   │   ├── order_validator.py # Validation complète
│   │   └── stock_checker.py   # Vérifications rapides
│   ├── alternatives/          # 🔄 Module d'alternatives
│   │   ├── manager.py         # Gestionnaire principal
│   │   └── selector.py        # Sélection LLM/règles
│   └── comments/              # 💬 Module commentaires + alertes ⭐ NOUVEAU
│       ├── comment_agent.py   # Génération commentaires + emails d'alerte
│       └── comment_templates.py # Templates spécialisés
├── rag/                       # ⚙️ Infrastructure RAG
│   ├── core.py               # Module central
│   ├── retrieval.py          # Recherche et stocks
│   └── settings.py           # Configuration
└── docs/                     # 📚 Documentation
    ├── architecture_modulaire.md  # 🆕 Guide principal
    ├── systeme_alertes_email.md   # 🆕 Système d'alertes
    ├── core.md               # Documentation RAG
    └── retrieval.md          # Documentation recherche
```

## 🚀 Comment Utiliser cette Documentation

### Pour les nouveaux utilisateurs
1. **COMMENCEZ OBLIGATOIREMENT par [`architecture_modulaire.md`](./architecture_modulaire.md)** 📖
   - Vue d'ensemble complète de la nouvelle architecture
   - Exemples pratiques et outils de debug
   - Guide de troubleshooting détaillé

### Pour comprendre les composants
2. **[`core.md`](./core.md)** - Fonctionnement du RAG et génération LLM
3. **[`retrieval.md`](./retrieval.md)** - Recherche et gestion des stocks
4. **[`nouveau_systeme_commande.md`](./nouveau_systeme_commande.md)** - Validation des commandes
5. **[`gestion_ruptures.md`](./gestion_ruptures.md)** - Gestion des ruptures

### Pour déboguer un problème
- Utilisez les **outils de debug intégrés** décrits dans `architecture_modulaire.md`
- Consultez la section **Troubleshooting** pour les problèmes courants
- Testez chaque module indépendamment

## ✨ Nouveautés Version 2.0

- ✅ **Architecture modulaire** : Séparation claire des responsabilités
- ✅ **Debugging facilité** : Outils intégrés pour identifier où ça plante
- ✅ **Performance améliorée** : Suppression des redondances
- ✅ **Maintenabilité** : Code plus organisé et testable
- ✅ **Documentation complète** : Guide étape par étape
- ✅ **Module commentaires intelligents** : Génération auto de commentaires pour tableaux
- ✅ **Système d'alertes email** : Notifications automatiques équipe commerciale
- ✅ **Correction données stock** : Bug "0 unité" résolu, vraies valeurs affichées
- ✅ **Interface alertes intégrée** : Affichage alertes critiques dans Mode Mail

## Prérequis

**Techniques :**
- Python 3.8+
- Connaissance des concepts RAG et LLM
- APIs OpenAI et Pinecone

**Architecture :**
- Compréhension des patterns modulaires
- Concepts de debugging et logging
- Gestion des exceptions Python

## 🆘 Besoin d'Aide ?

### En cas de problème
1. **Consultez [`architecture_modulaire.md`](./architecture_modulaire.md)** → Section Troubleshooting
2. **Utilisez les outils de debug** intégrés dans chaque module
3. **Vérifiez les logs** pour identifier l'étape qui échoue
4. **Testez module par module** pour isoler le problème

### Pour le développement
- Exemples de code dans chaque documentation
- Debug methods : `debug_extraction()`, `debug_validation()`, `debug_alternatives()`
- Format recommandé : `ID_PRODUIT DESCRIPTION Qté QUANTITÉ Prix : PRIX€`

---

**⚡ TIP** : La nouvelle architecture permet de **déboguer facilement** - si quelque chose ne marche pas, vous pouvez tester chaque étape individuellement ! 