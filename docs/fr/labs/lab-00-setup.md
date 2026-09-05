---
permalink: /fr/labs/lab-00-setup
lang: fr
title: "Lab 00 - Prérequis et configuration de l'environnement"
description: "Installer les outils requis, cloner le dépôt, créer un environnement virtuel Python et vérifier l'accès à Azure."
---

> 🇬🇧 **[English version](../../labs/lab-00-setup)**

## Aperçu

| | |
|---|---|
| **Durée** | 20 minutes |
| **Niveau** | Débutant |
| **Prérequis** | Aucun |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Installer les outils nécessaires pour provisionner et invoquer un agent hébergé Foundry
* Cloner le dépôt `foundry-hosted-agents` et configurer un environnement virtuel Python
* Vous connecter à Azure et confirmer que vous voyez le projet Foundry utilisé dans cet atelier
* Exécuter les suites de tests du dépôt comme vérification de bon fonctionnement

## Exercices

### Exercice 0.1 : Installer les outils requis

1. **Python 3.13** — <https://www.python.org/downloads/>

   ```powershell
   python --version
   ```

2. **Azure Developer CLI (`azd`)** — <https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd>

   ```powershell
   azd version
   ```

3. **Azure CLI (`az`)** — <https://learn.microsoft.com/cli/azure/install-azure-cli>

   ```powershell
   az version
   ```

4. **Visual Studio Code** — <https://code.visualstudio.com/>

### Exercice 0.2 : Installer l'extension `azd` Foundry

Les agents hébergés Foundry sont provisionnés via une extension `azd` :

```powershell
azd ext install microsoft.foundry
```

### Exercice 0.3 : Cloner le dépôt et configurer Python

```powershell
git clone https://github.com/devopsabcs-engineering/foundry-hosted-agents.git
cd foundry-hosted-agents
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r src/threat-assessment-agent/requirements.txt -r src/threat-assessment-agent/requirements-dev.txt
```

### Exercice 0.4 : Se connecter à Azure

```powershell
azd auth login
az login
```

Confirmez que vous êtes bien sur l'abonnement qui héberge les ressources de
cet atelier :

```powershell
az account show --query "{name:name, id:id}" -o table
```

### Exercice 0.5 : Exécuter les suites de tests existantes

Avant de toucher à toute infrastructure, confirmez que les tests du dépôt
passent dans votre environnement — c'est exactement la même commande que
le pipeline CI exécute.

```powershell
pytest eval/deterministic-tests/ -v
pytest src/threat-assessment-agent/tests/ -v
```

Résultat attendu : **12 passed** pour les vérifications d'évaluation
déterministes et **18 passed** pour les tests unitaires de l'agent. Si
l'une des suites échoue, revérifiez l'exercice 0.3 (installation des
dépendances) avant de continuer.

> [!TIP]
> Ces deux suites de tests ne touchent pas du tout à Azure — elles
> s'exécutent entièrement sur des fixtures locales et une machine à états
> LangGraph compilée. C'est un moyen rapide de confirmer que votre
> environnement Python est correct avant le Lab 02.

## Vérification des connaissances

* Quelle est la différence entre `az` et `azd`, et pourquoi cet atelier a-t-il besoin des deux ?
* Quelles sont les deux suites de tests que vous venez d'exécuter, et que valide chacune ?

## Prochaine étape

Passez au [Lab 01 : Plongée dans l'architecture](lab-01-architecture.md).
