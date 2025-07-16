# 📧 Système d'Alertes Email Automatiques

## 📋 Vue d'ensemble

Le système d'alertes email fait partie du module **Comments** de RAG-NINIA et génère automatiquement des emails d'alerte pour l'équipe commerciale lorsque des problèmes sont détectés sur les commandes clients.

### 🎯 Objectifs

- **Alertes proactives** : Notifier automatiquement les problèmes critiques
- **Données précises** : Utiliser les vraies valeurs de stock (correction bug majeur)
- **Intégration transparente** : Affichage dans l'interface Streamlit existante
- **Intelligence contextuelle** : Détection automatique des types de problèmes

## 🏗️ Architecture

### Localisation du code

```
ninia/comments/
├── comment_agent.py       # Agent principal avec méthodes d'alertes
└── comment_templates.py   # Templates d'emails spécialisés
```

### Classes impliquées

- **`CommentAgent`** : Génération et détection d'alertes
- **`CommentTemplates`** : Templates d'emails spécialisés
- **Interface Streamlit** : Affichage dans l'onglet "📧 Mode Mail"

## 🚨 Types d'alertes

### 1. Alerte rupture de stock

**Déclencheur** : `stock_disponible < quantite_demandee`

**Exemple d'usage** :
```python
rupture_info = {
    'nom_produit': 'CAISSE US SC 200X140X140MM',
    'quantite_demandee': 6000,
    'stock_magasin': 4000,          # Stock physique réel
    'stock_a_recevoir': 1000,       # Réapprovisionnement en cours
    'commandes_a_livrer': 2000,     # Déjà alloué à d'autres clients
    'stock_disponible': 3000,       # Net : 4000 + 1000 - 2000 = 3000
    'nom_client': 'Client_IA butterfly',
    'delai_livraison': '2-3 semaines'
}

email = comment_agent.generate_stock_alert_email(rupture_info)
```

**Exemple de mail généré** :
```
OBJET: 🚨 Rupture de stock critique – CAISSE US SC 200X140X140MM – Action requise

CORPS:
Bonjour,

Nous vous informons d'une situation de stock problématique :

📦 SITUATION DE STOCK :
- Produit : CAISSE US SC 200X140X140MM
- Stock physique magasin : 4000 unités
- Stock à recevoir (réapprovisionnement) : 1000 unités
- Commandes en attente de livraison : 2000 unités
- Stock net disponible : 3000 unités
- Commande client demandée : 6000 unités
- Unités manquantes : 3000 unités

👤 CLIENT CONCERNÉ : Client_IA butterfly

🎯 SITUATION : Stock insuffisant - Livraison partielle possible (3000 sur 6000) ou attendre réapprovisionnement

Actions recommandées :
1. Proposer livraison partielle immédiate (3000 unités)
2. Programmer complément après réapprovisionnement
3. Contacter le fournisseur pour accélérer la livraison
```

### 2. Alerte marge insuffisante

**Déclencheur** : `marge_calculee < marge_minimum`

**Exemple d'usage** :
```python
marge_info = {
    'nom_produit': 'CAISSE PREMIUM 500X400X300MM',
    'prix_propose': 2.50,
    'prix_achat': 2.20,
    'marge_calculee': 0.30,        # 2.50 - 2.20 = 0.30€
    'marge_minimum': 0.50,         # Marge minimum requise
    'deficit_marge': 0.20,         # 0.50 - 0.30 = 0.20€
    'quantite': 1000,
    'valeur_totale': 2500.00,      # 1000 * 2.50€
    'nom_client': 'Client_Premium'
}

email = comment_agent.generate_margin_alert_email(marge_info)
```

**Exemple de mail généré** :
```
OBJET: 💰 Marge insuffisante – CAISSE PREMIUM 500X400X300MM – Négociation requise

CORPS:
Bonjour,

Analyse de rentabilité préoccupante détectée :

💰 PROBLÈME DE MARGE :
- Produit : CAISSE PREMIUM 500X400X300MM
- Prix proposé client : 2,50€
- Prix d'achat : 2,20€
- Marge calculée : 0,30€ (12%)
- Marge minimum requise : 0,50€ (18,5%)
- Déficit : 0,20€ par unité

👤 CLIENT : Client_Premium (1000 unités - 2500€)

Recommandations :
1. Prix minimum recommandé : 2,70€ (marge 18,5%)
2. Négocier quantité pour meilleur prix
3. Proposer produit alternatif plus rentable
```

### 3. Alerte commerciale générale

**Déclencheur** : Problèmes multiples ou non spécifiques

**Exemple d'usage** :
```python
alerte_info = {
    'type_probleme': 'Stock et marge critiques',
    'nom_client': 'Client_Problematique',
    'nom_produit': 'CAISSE SPECIALE 600X400X400MM',
    'quantite_demandee': 500,
    'prix_propose': 3.20,
    'stock_magasin': 100,
    'stock_disponible': 100,
    'marge_calculee': 0.40,
    'marge_minimum': 0.80,
    'niveau_urgence': 'HAUTE'
}

email = comment_agent.generate_commercial_alert_email(alerte_info)
```

## 🔧 Correction majeure : Vraies données de stock

### Problème identifié

**Avant** : Les templates utilisaient `stock_actuel` qui retournait toujours 0 par défaut :
```python
# INCORRECT - Bug majeur
stock_actuel = rupture_info.get('stock_actuel', 0)  # Toujours 0 !
```

**Résultat** : Emails affichant "Stock actuel : 0 unité" même avec du stock disponible.

### Solution implémentée

**Après** : Templates corrigés pour utiliser les vraies clés de données :
```python
# CORRECT - Vraies données
stock_magasin = rupture_info.get('stock_magasin', 0)           # Stock physique
stock_a_recevoir = rupture_info.get('stock_a_recevoir', 0)     # Réapprovisionnement
commandes_a_livrer = rupture_info.get('commandes_a_livrer', 0) # Déjà alloué
stock_disponible = rupture_info.get('stock_disponible', 0)     # Net disponible

# Calcul automatique du manque réel
manque_reel = max(0, quantite_demandee - stock_disponible)
```

### Impact de la correction

- ✅ **Données exactes** : Stock physique réel affiché
- ✅ **Calculs précis** : Manque calculé automatiquement
- ✅ **Transparence** : Détail complet du stock (magasin + réappro - alloué)
- ✅ **Fiabilité** : Plus d'erreurs d'affichage "0 unité"

## 🔄 Intégration dans le flux de travail

### Détection automatique

```python
# Dans NiniaAgent.process_message()
def generate_table_comment(self, commande_info, comment_type="auto"):
    # 1. Génération du commentaire de tableau
    comment = self.comment_agent.generate_smart_comment(commande_info, comment_type)
    
    # 2. Détection et génération d'alertes email
    alert_email = self.comment_agent.generate_alert_email_if_needed(commande_info)
    
    # 3. Ajout de l'alerte dans l'interface si nécessaire
    if alert_email and 'mails_automatiques' in st.session_state:
        st.session_state.mails_automatiques.append({
            'type': 'alerte_critique',
            'contenu': alert_email,
            'timestamp': datetime.now()
        })
    
    return comment
```

### Affichage dans Streamlit

#### Onglet "📧 Mode Mail"

Les alertes apparaissent avec un style visuel distinct :

```python
# Alertes critiques avec bordure rouge
if mail['type'] == 'alerte_critique':
    st.markdown(f"""
    <div style="border: 2px solid #ff4444; padding: 10px; border-radius: 5px; background-color: #ffe6e6;">
    🚨 <strong>ALERTE CRITIQUE</strong><br/>
    {mail['contenu']}
    </div>
    """, unsafe_allow_html=True)
```

#### Métriques mises à jour

```python
# Séparation des compteurs
alertes_critiques = len([m for m in mails if m.get('type') == 'alerte_critique'])
communications_normales = len([m for m in mails if m.get('type') != 'alerte_critique'])

col1.metric("🚨 Alertes critiques", alertes_critiques)
col2.metric("📧 Communications", communications_normales)
```

## 🎯 Logique de détection

### Méthode `generate_alert_email_if_needed()`

```python
def generate_alert_email_if_needed(self, commande_info: Dict[str, Any]) -> Optional[str]:
    # Vérifications des conditions d'alerte
    stock_disponible = commande_info.get('stock_disponible', 0)
    quantite_demandee = commande_info.get('quantite_demandee', 0)
    marge_calculee = commande_info.get('marge_calculee', 0)
    marge_minimum = commande_info.get('marge_minimum', 0)
    
    # Priorité 1 : Rupture de stock
    if stock_disponible < quantite_demandee:
        return self.generate_stock_alert_email(commande_info)
    
    # Priorité 2 : Marge insuffisante
    elif marge_calculee < marge_minimum:
        return self.generate_margin_alert_email(commande_info)
    
    # Pas d'alerte nécessaire
    return None
```

### Exemples de déclenchement

| Scenario | Stock Dispo | Qté Demandée | Marge Calc | Marge Min | Alerte |
|----------|-------------|--------------|------------|-----------|--------|
| OK | 500 | 300 | 0.60€ | 0.50€ | ❌ Aucune |
| Rupture | 200 | 500 | 0.60€ | 0.50€ | 🚨 Stock |
| Marge faible | 500 | 300 | 0.30€ | 0.50€ | 💰 Marge |
| Double problème | 200 | 500 | 0.30€ | 0.50€ | 🚨 Stock (priorité) |

## 📊 Format des emails

### Structure standardisée

Tous les emails suivent le format :
```
OBJET: [emoji] [type d'alerte] – [produit] – [action]

CORPS:
Bonjour,

[Introduction du problème]

[Section détails avec émojis] :
- Données précises et calculs
- Informations client

[Actions recommandées] :
1. Action immédiate
2. Action à moyen terme
3. Action préventive

Cordialement,
Système NINIA - Butterfly Packaging
```

### Personnalisation par type

- **🚨 Stock** : Focus sur disponibilité et réapprovisionnement
- **💰 Marge** : Analyse financière et négociation
- **⚠️ Général** : Synthèse des problèmes multiples

## 🧪 Tests et validation

### Tests unitaires

```python
# Test de détection de rupture
def test_stock_alert_detection():
    commande_info = {
        'stock_disponible': 100,
        'quantite_demandee': 500,
        'marge_calculee': 0.60,
        'marge_minimum': 0.50
    }
    
    alert = comment_agent.generate_alert_email_if_needed(commande_info)
    assert alert is not None
    assert "rupture" in alert.lower()
```

### Tests d'intégration

```python
# Test complet avec vraies données
def test_integration_complete():
    # Simule une commande problématique
    message = "7600005 00000000 CAISSE US SC 200X140X140MM Qté 2000 Prix : 0,8€"
    
    # Traitement complet
    result = agent.process_message(message)
    
    # Vérifications
    assert result['commentaire'] is not None
    assert len(st.session_state.mails_automatiques) > 0
    assert st.session_state.mails_automatiques[0]['type'] == 'alerte_critique'
```

## 🚀 Déploiement et utilisation

### Activation automatique

Le système est automatiquement actif pour toute nouvelle commande. Aucune configuration requise.

### Redémarrage requis

Après modification des templates :
```bash
# Arrêter Streamlit
Ctrl+C

# Redémarrer
streamlit run app_streamlit/chatbot_ninia.py
```

### Exemple de test

```bash
# Dans le chatbot, tester :
"7600005 00000000 CAISSE US SC 200X140X140MM Qté 2000 Prix : 0,8€"

# Résultat attendu :
# - Commentaire : "STOCK INSUFFISANT - Livraison partielle possible..."
# - Email d'alerte dans l'onglet Mode Mail avec données correctes
```

## 🏆 Avantages du système

### Pour l'équipe commerciale

- ✅ **Alertes proactives** : Problèmes détectés automatiquement
- ✅ **Données précises** : Stock réel affiché, plus d'erreurs
- ✅ **Actions claires** : Recommandations concrètes dans chaque mail
- ✅ **Priorisation** : Alertes critiques vs communications normales

### Pour le système

- ✅ **Intégration transparente** : Aucun changement d'usage
- ✅ **Performance** : Génération rapide des alertes
- ✅ **Robustesse** : Fallback en cas d'erreur LLM
- ✅ **Evolutivité** : Nouveaux types d'alertes facilement ajoutables

### Pour la maintenance

- ✅ **Code modulaire** : Templates séparés et spécialisés
- ✅ **Debug facilité** : Méthodes de test intégrées
- ✅ **Documentation** : Chaque template documenté
- ✅ **Traçabilité** : Logs des alertes générées

## 📈 Améliorations futures possibles

1. **Niveaux d'urgence** : Gradation FAIBLE/MOYEN/CRITIQUE
2. **Seuils configurables** : Paramétrage des seuils de marge
3. **Historique des alertes** : Base de données des alertes envoyées
4. **Intégration email** : Envoi automatique via SMTP
5. **Dashboard alertes** : Vue d'ensemble des problèmes récurrents
6. **Alertes prédictives** : Prévision des ruptures futures

---

*Documentation mise à jour le 2024 - Système d'alertes email RAG-NINIA v2.0* 