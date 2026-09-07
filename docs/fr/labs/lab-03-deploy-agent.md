---
permalink: /fr/labs/lab-03-deploy-agent
lang: fr
title: "Lab 03 - Provisionner et déployer l'agent hébergé"
description: "Utiliser azd pour provisionner un projet Foundry, un déploiement de modèle, des connexions Toolbox et l'agent hébergé lui-même."
---

> 🇬🇧 **[English version](../../labs/lab-03-deploy-agent)**

## Aperçu

| | |
|---|---|
| **Durée** | 35 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Lab 02](lab-02-mcp-servers.md) |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Lire un manifeste `azure.yaml` qui mélange des services d'infrastructure et un service d'agent hébergé
* Provisionner un projet Foundry, un déploiement de modèle et une Toolbox avec `azd provision`
* Déployer le code de l'agent hébergé avec `azd deploy`
* Localiser l'agent déployé, son modèle et son identité dans le portail Foundry

## Exercices

### Exercice 3.1 : Lire la définition du service agent

Ouvrez `azure.yaml` à la racine du dépôt. Le service
`threat-assessment-agent` est celui qui nous intéresse :

```yaml
threat-assessment-agent:
    project: ./src/threat-assessment-agent
    host: azure.ai.agent
    language: python
    uses:
        - ai-project
        - security-tools
    codeConfiguration:
        dependencyResolution: remote_build
        entryPoint: main.py
        runtime: python_3_13
    container:
        resources:
            cpu: "0.5"
            memory: 1Gi
    kind: hosted
    protocols:
        - protocol: responses
          version: 2.0.0
```

Champs clés :

| Champ | Signification |
|---|---|
| `host: azure.ai.agent` | Ceci est un service d'agent hébergé Foundry, pas une container app ni une fonction |
| `kind: hosted` | Foundry exploite le calcul de session ; vous ne possédez que le code du graphe |
| `uses: [ai-project, security-tools]` | Câble le déploiement de modèle et la Toolbox MCP du Lab 01 |
| `dependencyResolution: remote_build` | Foundry construit vos dépendances Python côté serveur à partir de `requirements.txt` |
| `protocol: responses` | L'agent parle le protocole Responses compatible OpenAI (supporte le streaming) |

### Exercice 3.2 : Provisionner

```powershell
azd auth login
azd env new <votre-nom-environnement-atelier>
azd provision
```

Cette étape crée (ou confirme) le compte Foundry, le projet, le
déploiement de modèle `gpt-4o-mini`, et les deux connexions Toolbox du
Lab 01 (`defender-conn`, `anomaly-conn`) — tout **sauf** le code de
l'agent lui-même.

### Exercice 3.3 : Déployer l'agent

```powershell
azd deploy
```

Cette étape téléverse `src/threat-assessment-agent/` et le construit à
distance selon `dependencyResolution: remote_build`, puis publie une
nouvelle version de l'agent hébergé.

> **Dépannage : `no Foundry project endpoint resolved`**
>
> Si `azd deploy` échoue sur le service `security-tools` ou
> `threat-assessment-agent` avec cette erreur, votre environnement a été
> provisionné avant l'ajout du point de terminaison du projet Foundry comme
> sortie bicep. Relancez `azd provision` pour le récupérer, ou définissez-le
> manuellement pour cet environnement :
>
> ```powershell
> azd env set FOUNDRY_PROJECT_ENDPOINT "https://<accountName>.services.ai.azure.com/api/projects/<projectName>"
> ```
>
> `<accountName>` et `<projectName>` sont les valeurs `accountName`/`projectName`
> déjà présentes dans votre fichier `.azure/<env>/.env`.

> **Dépannage : `failed to resolve connection "defender-conn"` (ou `anomaly-conn`)**
>
> Cela signifie que la connexion n'existe pas encore sur le projet Foundry.
> Les connexions Toolbox `defender-conn`/`anomaly-conn` sont créées par
> `azd provision` depuis le bicep (pas par `azd deploy`) ; si votre
> environnement a été provisionné avant l'ajout de ces connexions comme
> ressources bicep, elles n'ont jamais été créées. Relancez
> `azd provision` pour les créer, puis relancez `azd deploy`.

> **Dépannage : `AZURE_AI_PROJECT_ID is not set`**
>
> Le service `threat-assessment-agent` a besoin de l'ID de ressource ARM
> du projet Foundry (différent de `FOUNDRY_PROJECT_ENDPOINT`). Si votre
> environnement a été provisionné avant l'ajout de cette sortie bicep,
> relancez `azd provision` pour la récupérer, ou définissez-la manuellement :
>
> ```powershell
> azd env set AZURE_AI_PROJECT_ID "/subscriptions/<subscriptionId>/resourceGroups/<resourceGroup>/providers/Microsoft.CognitiveServices/accounts/<accountName>/projects/<projectName>"
> ```

### Exercice 3.4 : Trouver l'agent dans le portail

![Vue d'ensemble du projet Foundry dans le portail Azure](../../assets/images/03-azure-foundry-project-overview.png)

![Vue d'ensemble du projet dans le portail Foundry](../../assets/images/04-foundry-portal-project-overview.png)

![Liste des agents du portail Foundry montrant le threat-assessment-agent déployé](../../assets/images/05-foundry-portal-agents-list.png)

![Page de détail de l'agent dans le portail Foundry](../../assets/images/06-foundry-portal-agent-detail.png)

Naviguez vers votre projet Foundry dans le portail et confirmez que vous
pouvez voir :

1. Le `threat-assessment-agent` dans la liste des agents, avec un numéro
   de version.
2. La page de détail de l'agent, montrant son modèle (`gpt-4o-mini`) et sa
   Toolbox (`security-tools`).
3. **Une identité Entra ID dédiée** a été créée automatiquement pour cet
   agent au moment du déploiement — vous n'avez pas câblé manuellement une
   identité managée. Trouvez-la sous l'onglet **Identity** de l'agent.

> [!TIP]
> Cette « Instance Identity » créée automatiquement est celle qui appelle
> réellement Azure OpenAI et la Toolbox MCP à l'exécution. C'est la même
> identité que vous investiguerez avec `az role assignment list` au
> [Lab 07](lab-07-troubleshooting-rbac.md).

## Vérification des connaissances

* Que signifie `remote_build`, et pourquoi cela pourrait-il compter pour une dépendance volumineuse comme `langgraph` ?
* D'où vient l'identité d'exécution de l'agent — l'avez-vous créée vous-même ?
* Nommez les deux connexions Toolbox câblées dans cet agent, et quel spécialiste utilise laquelle.

## Prochaine étape

Passez au [Lab 04 : Invoquer l'agent et lire les traces](lab-04-invoke-agent.md).
