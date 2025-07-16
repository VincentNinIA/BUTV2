# 🦋 RAG-NINIA - Assistant IA Butterfly Packaging

## 🚀 Lancement Rapide

### Option 1 : Script Simplifié (RECOMMANDÉ)
```bash
./start.sh
```

### Option 2 : Script Complet
```bash
./run_app.sh
```

### Option 3 : Manuel
```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Vérifier que le bon streamlit est utilisé
which streamlit  # doit pointer vers venv/bin/streamlit

# Lancer l'application
streamlit run app_streamlit/chatbot_ninia.py
```

## ⚙️ Configuration

1. **Variables d'environnement** : Copiez `.env.template` vers `.env` et configurez vos clés API
2. **Installation complète** : Consultez `INSTALLATION.md`

## 🐛 Problèmes Courants

### Erreur "ImportError: cannot import name 'LangSmithParams'"

**Cause** : Mauvais environnement virtuel utilisé

**Solution** :
```bash
# Utiliser le script de démarrage
./start.sh

# Ou réactiver manuellement l'environnement
deactivate
source venv/bin/activate
which streamlit  # doit pointer vers venv/bin/streamlit
```

## 📋 Fonctionnalités

- **Commandes** : "Je veux commander 10 caisses américaines"
- **Consultation stock** : "Quel est le stock des films étirables ?"
- **Alternatives** : "Alternative aux caisses Galia"
- **Questions générales** : "Comment vas-tu aujourd'hui ?"

## 📖 Documentation

- **Installation complète** : `INSTALLATION.md`
- **Documentation technique** : `docs/`

## 🆕 Architecture Version 2.0 - Refactoring Majeur

**L'architecture de NINIA a été complètement refactorisée !**

✅ **Architecture modulaire** : Debugging facilité, performance améliorée  
✅ **Nouvelles fonctionnalités** : Outils de debug intégrés  
✅ **Interface identique** : Aucun changement pour l'utilisateur final  

**👉 [Consultez la documentation complète](./docs/architecture_modulaire.md)** pour comprendre la nouvelle architecture et ses avantages.

## 🚀 Nouvelles Fonctionnalités RAG v2.1

**Le système RAG a été massivement optimisé et enrichi !**

✅ **Performance 12.7x plus rapide** : 0.46s vs 5.89s  
✅ **Alternatives intelligentes** : RAG optimisé avec fiches techniques complètes  
✅ **Commentaires enrichis** : "4 alternatives proposées" automatiquement  
✅ **Emails d'alerte intelligents** : Recommandations détaillées de l'agent IA  
✅ **Intégration complète** : RAG → Interface → Emails de bout en bout  

**👉 [Documentation complète des nouvelles fonctionnalités](./docs/nouvelles_fonctionnalites_rag.md)**

## 🎯 Améliorations v2.2 - Gestion Intelligente du Réapprovisionnement

**Le système de gestion des commandes a été optimisé pour mieux traiter les cas de réapprovisionnement !**

✅ **Déclenchement RAG intelligent** : Plus de recherches inutiles pour stock avec réapprovisionnement  
✅ **Commentaires explicites** : "Livraison dépend du réapprovisionnement - Stock actuel: 2520, En commande: 2880"  
✅ **Distinction claire** : Différenciation entre situation informative et critique  
✅ **Performance optimisée** : Évite les calculs inutiles pour les cas normaux  

**🎯 Cas d'usage résolu :**
```
Commande: "7600005 00000000 CAISSE US SC 200X140X140MM Qté 3000 Prix : 0,8€"
✅ AVANT: RAG déclenché inutilement + commentaire générique
✅ APRÈS: RAG non déclenché + commentaire explicite avec détails stock
```

### Tests de Validation Disponibles
```bash
# Test intégration complète RAG → Interface
python test_integration_live.py

# Test performance (mesure le gain 12.7x)
python test_rag_performance.py

# Test qualité fiches techniques LLM
python test_llm_fiches_techniques.py

# Test gestion réapprovisionnement (nouveau v2.2)
python test_cas_reappro.py
```

### Format de commande recommandé
```
76000 00420000 CAISSE US SC 450X300X230MM Qté 300 Prix : 0,7€
```

---

**URL de l'application** : http://localhost:8501 