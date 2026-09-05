---
permalink: /fr/labs/lab-07-troubleshooting-rbac
lang: fr
title: "Lab 07 - Dépannage réel : erreur RBAC 401"
description: "Suivre une véritable investigation de support Azure, toujours ouverte, sur une erreur 401 PermissionDenied, en utilisant uniquement l'interface en ligne de commande Azure."
---

> 🇬🇧 **[English version](../../labs/lab-07-troubleshooting-rbac)**

## Aperçu

| | |
|---|---|
| **Durée** | 40 minutes |
| **Niveau** | Avancé |
| **Prérequis** | [Lab 06](lab-06-cicd.md) |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Reproduire les commandes `az` exactes utilisées pour confirmer ou infirmer une configuration RBAC comme cause racine
* Lire directement les `dataActions` d'une définition de rôle intégrée au lieu de faire confiance à l'hypothèse d'un script de support
* Vérifier si une politique Azure pourrait silencieusement remplacer une propriété de ressource que vous lisez
* Énumérer les politiques d'accès conditionnel du tenant pour écarter les blocages au niveau de l'identité
* Expliquer pourquoi « le portail montre le rôle attribué » ne suffit pas comme preuve à lui seul

## Le symptôme

Ce PoC a rencontré une véritable erreur `401 PermissionDenied`,
reproductible, lorsque l'identité propre de l'agent hébergé appelle les
complétions de chat Azure OpenAI :

```text
ERROR: agent error (server_error): Error code: 401 - {'error': {'code': 'PermissionDenied',
'message': 'The principal `<id-du-principal-de-service>` lacks the required data action
`Microsoft.CognitiveServices/accounts/OpenAI/deployments/chat/completions/action`
to perform `POST /openai/deployments/{deployment-id}/chat/completions` operation.'}}
```

Ceci est suivi sous le nom **WI-11** dans le
[wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/RBAC-401-Investigation)
du projet et, au moment de cet atelier, reste **ouvert auprès du support
Azure**. Vous allez reproduire les étapes de diagnostic exactes utilisées
dans cette investigation.

## Exercices

### Exercice 7.1 : Ne faites pas confiance au diagnostic du message d'erreur lui-même — vérifiez-le

Le message d'erreur nomme une action de données spécifique manquante.
Vérifiez l'attribution directement plutôt que de supposer que le message
est exact :

```powershell
az role assignment list --assignee <id-du-principal-de-service> `
  --scope /subscriptions/<id-abonnement>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<nom-du-compte> `
  -o table
```

Dans cette investigation, cette commande a montré que **les deux** rôles,
`Foundry User` et `Cognitive Services OpenAI User`, étaient déjà attribués
exactement à la portée de la ressource — l'attribution que le support
demandait de revérifier était déjà correcte.

### Exercice 7.2 : Lire la définition du rôle elle-même — ne supposez pas qu'elle « inclut » une action de données

Une réponse du support a émis l'hypothèse que le *rôle attribué* ne
couvrait pas l'action de données exacte nommée dans l'erreur. Plutôt que
de croire cela sur parole, lisez directement les `dataActions` de la
définition du rôle :

```powershell
az role definition list --name "Cognitive Services OpenAI User" -o json
```

> [!TIP]
> Le résultat imbrique `dataActions` dans `permissions[0].dataActions`,
> pas comme propriété de premier niveau. Un naïf
> `... | ConvertFrom-Json | Select-Object -ExpandProperty dataActions`
> échoue — il faut d'abord descendre dans `permissions[0]`.

Confirmez que `Microsoft.CognitiveServices/accounts/OpenAI/deployments/chat/completions/action`
est explicitement listée. Dans cette investigation, elle l'était —
réfutant directement l'hypothèse du support avec la source de vérité de la
définition de rôle elle-même.

### Exercice 7.3 : Écarter les blocages au niveau de la ressource et du réseau

```powershell
az cognitiveservices account show --name <nom-du-compte> --resource-group <rg> `
  --query "{disableLocalAuth:properties.disableLocalAuth, publicNetworkAccess:properties.publicNetworkAccess, networkAcls:properties.networkAcls, privateEndpointConnections:properties.privateEndpointConnections}" -o json
```

Deux points à raisonner, pas seulement à lire :

* `disableLocalAuth: true` ne bloque que l'authentification par **clé
  API** — cela n'affecte pas l'authentification par identité
  managée/jeton AAD que cet agent utilise réellement. Ne laissez pas une
  valeur `true` ici devenir une fausse piste.
* `networkAcls: null` et un tableau `privateEndpointConnections` vide
  signifient qu'il n'y a pas non plus de restriction réseau bloquant
  l'appel.

### Exercice 7.4 : Vérifier si une politique remplace silencieusement ce que vous venez de lire

Une propriété affichant `"publicNetworkAccess": "Enabled"` pourrait, en
principe, être silencieusement remplacée par une **politique Azure à
effet `Modify`** que vous n'avez pas encore repérée. Vérifiez ce qui a
réellement été évalué contre cette ressource spécifique :

```powershell
az policy state list --resource "/subscriptions/<id-abonnement>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<nom-du-compte>" `
  --query "[].{policy:policyDefinitionName, assignment:policyAssignmentName, complianceState:complianceState}" -o json
```

Si une initiative de gouvernance de votre tenant contient effectivement
une politique qui peut forcer la désactivation de l'accès réseau public,
vérifiez la clause `if` de son `policyRule` pour le **type et le kind**
exacts de ressource qu'elle cible :

```powershell
az policy definition show --name <nom-de-la-definition-de-politique> --management-group <id-mg> --query "policyRule" -o json
```

Dans cette investigation, une politique à l'échelle du tenant existait
bien pour forcer la désactivation de l'accès réseau public — mais
uniquement pour l'ancien type de ressource
`Microsoft.MachineLearningServices/workspaces` (`kind == 'Hub'`). Un
rapide `az resource list` sur le groupe de ressources a confirmé
**qu'aucune ressource de ce type n'existe dans ce déploiement** (il
utilise le modèle plus récent de compte Cognitive Services `AIServices` +
`.../accounts/projects` imbriqué), donc cette politique ne pouvait pas
être la cause.

### Exercice 7.5 : Vérifier l'accès conditionnel au niveau du tenant

```powershell
az rest --method get --url "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" -o json
```

Cherchez toute politique dont `conditions.clientApplications` est non nul
— c'est la condition qui cible spécifiquement les principaux de
service/identités de charge de travail, par opposition aux utilisateurs
humains. Dans cette investigation, aucune des politiques activées du
tenant ne ciblait les principaux de service ; elles étaient toutes
centrées sur les utilisateurs humains (MFA, risque de connexion,
enregistrement des informations de sécurité).

### Exercice 7.6 : Comparer avec le contournement manuel de l'agent

Alors que le chemin CLI/API de l'agent hébergé continuait à renvoyer des
401, un agent créé **manuellement** dans le portail Foundry — utilisant la
même identité et le même déploiement de modèle — a réussi.

![Agent manuel créé avec succès dans le portail](../../assets/images/manual-agent-created.png)
![Le chat de l'agent manuel a réussi là où le propre chemin d'invocation de l'agent hébergé échouait avec 401](../../assets/images/manual-agent-chat-success.png)
![Les appels d'outils MCP de l'agent manuel ont également réussi](../../assets/images/manual-agent-mcp-tools-success.png)

C'est en soi un signal de diagnostic puissant : si le RBAC était réellement
incorrect, **les deux** chemins devraient échouer de manière identique. Un
chemin manuel fonctionnel à côté d'un chemin d'agent hébergé défaillant
pointe vers quelque chose de spécifique au propre code d'acquisition de
jeton de l'agent hébergé — pas la configuration RBAC visible côté client.

## Réflexion

À la fin des exercices 7.1 à 7.6, chaque angle côté client — attribution,
définition de rôle, paramètres de ressource, politique Azure, accès
conditionnel du tenant — revient propre. C'est en soi le résultat : **les
preuves construites ici sont ce qui justifie l'escalade vers l'éditeur de
la plateforme**, au lieu de continuer à revérifier la même attribution
RBAC. Lisez l'investigation complète, toujours en évolution, et les
brouillons de réponses au support dans le wiki du projet :
[Investigation RBAC 401](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/RBAC-401-Investigation).

## Vérification des connaissances

* Nommez trois couches côté client vérifiées dans ce lab avant de conclure que le problème est côté plateforme.
* Pourquoi « le portail montre le rôle attribué » n'est-il pas suffisant — qu'a ajouté l'exercice 7.2 par-dessus cela ?
* Quelle preuve unique de l'exercice 7.6 pointe le plus fortement vers une cause autre qu'une configuration RBAC ?

## Prochaine étape

Passez au [Lab 08 : Préparation à la production et portes de décision](lab-08-production-readiness.md).
