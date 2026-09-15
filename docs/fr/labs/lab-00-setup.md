---
permalink: /fr/labs/lab-00-setup
lang: fr
title: "Lab 00 - Prérequis et configuration de l'environnement"
description: "Installer les outils requis, cloner le dépôt, créer un environnement virtuel Python et vérifier l'accès à Azure."
---

> 🇬🇧 **[English version](../../labs/lab-00-setup)**

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 20 minutes |
| **Niveau** | Débutant |
| **Prérequis** | Aucun |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Installer les outils nécessaires pour provisionner et invoquer un agent hébergé Foundry
* Cloner le dépôt `foundry-hosted-agents` et configurer un environnement virtuel Python
* Vous connecter à Azure et choisir un abonnement approuvé pour vos ressources d'atelier isolées
* Exécuter les suites de tests du dépôt comme vérification de bon fonctionnement

## Exercices

Avant le Lab 02, faites approuver le VNet, les sous-réseaux délégués, la zone DNS
privée, les plages sans chevauchement et les permissions réseau limitées. Cosmos,
si retenu, exige un point privé et une machine de test reliée au réseau ; un poste
public ne peut pas tester son plan de données. Foundry reste public et authentifié.
Consultez [Réseau Cosmos privé](../private-networking.md). Si les politiques exigent
aussi Foundry, le registre ou MCP privés, arrêtez : ce profil ne les couvre pas.

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

Les commandes utilisent **PowerShell 7.3 ou plus récent**. Les scripts d'appel,
de RBAC et d'évaluation nécessitent aussi **Git Bash, jq et curl**. Sous Windows,
installez Git for Windows et jq par le canal logiciel approuvé (par exemple
`winget install --id Git.Git --exact` et `winget install --id jqlang.jq --exact`).
Redémarrez le terminal après l'installation. Ne modifiez pas les politiques
d'exécution ou de réseau de votre organisation pour installer une dépendance.

À chaque nouvelle session PowerShell, activez Python comme indiqué ci-dessous
et vérifiez les outils. Le `System32/bash.exe` de Windows lance WSL, pas Git Bash.
Adaptez le chemin de Git si votre organisation l'installe ailleurs.

```powershell
$env:PATH = "C:\Program Files\Git\bin;$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:PATH"
$env:MSYS_NO_PATHCONV = '1'
Get-Command git, bash, jq, curl.exe, az, azd
bash -lc 'command -v az azd jq curl && jq --version'
```

`MSYS_NO_PATHCONV` empêche Git Bash de transformer les ID de ressources Azure en
chemins Windows. Gardez la même session pour les Labs 02-08 ; ses variables
identifient vos ressources jetables. Si vous perdez la session, récupérez les
valeurs de votre environnement, jamais les noms des captures historiques.

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
python -m pip install -r src/threat-assessment-agent/requirements.txt -r src/threat-assessment-agent/requirements-dev.txt
```

### Exercice 0.4 : Se connecter à Azure

```powershell
azd auth login
az login
```

Utilisez un abonnement où vous êtes autorisé à créer des ressources facturables et à attribuer
des rôles limités aux ressources. Ne réutilisez pas le groupe de ressources du formateur ou
d'un client existant. Connectez-vous avec votre propre identité approuvée ; les scénarios
utilisent des données synthétiques, pas des données d'employés ou de clients.
Confirmez l'abonnement et le locataire avant de continuer :

```powershell
az account show --query "{name:name, id:id, tenantId:tenantId}" -o table
```

### Exercice 0.5 : Exécuter les suites de tests existantes

Avant de toucher à toute infrastructure, confirmez que les tests du dépôt
passent dans votre environnement — c'est exactement la même commande que
le pipeline CI exécute.

```powershell
python -m pytest eval/deterministic-tests/ -v
python -m pytest src/threat-assessment-agent/tests/ -v
```

Résultat attendu : les deux commandes se terminent sans test échoué. Le nombre de tests
évolue avec l'atelier ; ne le comparez pas à une ancienne capture ou à un rapport de publication.
Certains tests facultatifs sont ignorés par défaut. Utilisez `python -m pytest -rs` avec les
mêmes chemins pour voir pourquoi. Si une suite échoue, revérifiez l'exercice 0.3 avant de continuer.

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
