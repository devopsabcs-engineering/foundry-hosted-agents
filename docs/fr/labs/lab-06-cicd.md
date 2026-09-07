---
permalink: /fr/labs/lab-06-cicd
lang: fr
title: "Lab 06 - CI/CD : pipeline de mise en production contrôlé par évaluation"
description: "Parcourir les deux pipelines GitHub Actions : le pipeline direct du PoC et le flux complet de staging vers la production, contrôlé par évaluation."
---

> 🇬🇧 **[English version](../../labs/lab-06-cicd)**

## Aperçu

| | |
|---|---|
| **Durée** | 35 minutes |
| **Niveau** | Avancé |
| **Prérequis** | [Lab 05](lab-05-evaluations.md) |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Expliquer la différence entre les deux pipelines de ce dépôt et pourquoi les deux existent
* Retracer le flux complet staging → porte d'évaluation → approbation manuelle → production
* Expliquer pourquoi ce dépôt s'authentifie avec OIDC plutôt qu'avec des secrets stockés
* Reconnaître une cause plausible d'un vrai symptôme de 401 intermittent rencontré en CI

## Exercices

### Exercice 6.1 : Deux pipelines, deux objectifs

Ouvrez [`.github/workflows/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/.github/workflows) :

| Pipeline | Déclencheur | Ce qu'il fait |
|---|---|---|
| `hosted-agent-cd.yml` | Manuel (`workflow_dispatch`) | Provisionne et déploie **directement vers l'environnement PoC partagé**, puis exécute un test de fumée. Pas de staging, pas de porte d'évaluation. |
| `deploy-and-evaluate.yml` | Manuel (`workflow_dispatch`) | Flux complet de contrôle de mise en production : lint/tests unitaires → validation Bicep/what-if → déploiement d'un **candidat immuable en staging** → tests de fumée/contrat/streaming → **porte de qualité d'évaluation hors ligne** → approbation manuelle de production → promotion → surveillance post-déploiement → retour en arrière en cas de rupture. |

Les deux sont **en déclenchement manuel uniquement** — lisez le bloc de
commentaires en haut de chaque fichier. Ce n'était pas la conception
initiale ; c'est une leçon apprise : déclencher automatiquement les deux
pipelines à chaque push sur `main` les faisait entrer en concurrence sur
le même compte Cognitive Services partagé.

### Exercice 6.2 : La porte d'évaluation

Dans `deploy-and-evaluate.yml`, trouvez l'étape qui s'exécute après « déployer
le candidat en staging » et avant « approbation manuelle de production ».
Cette étape exécute les vérifications déterministes et les évaluateurs de
rubriques du [Lab 05](lab-05-evaluations.md) contre le **candidat de
staging**, pas contre le trafic de production. Une mise en production
n'atteint la porte d'approbation manuelle que si cette étape réussit.

### Exercice 6.3 : Authentification sans secret

Les deux workflows s'authentifient via une **fédération OIDC** — aucun
`AZURE_CLIENT_SECRET` ni identifiant stocké n'est présent nulle part dans
le dépôt. Trouvez le bloc `permissions: id-token: write` en haut de chaque
fichier de workflow ; c'est ce qui permet à GitHub Actions de demander un
jeton OpenID Connect à courte durée de vie qu'Azure approuve via un
identifiant fédéré, au lieu d'un secret à longue durée de vie.

### Exercice 6.4 : Une véritable leçon de concurrence

Lisez attentivement le bloc de commentaires en haut de
`hosted-agent-cd.yml` :

> Le déclenchement automatique à chaque push sur main entrait en
> concurrence avec les propres cycles de provisionnement/déploiement de
> `deploy-and-evaluate.yml` contre le même compte Cognitive Services, ce
> qui est probablement la vraie cause des erreurs `401 PermissionDenied`
> intermittentes observées lors des invocations de l'agent hébergé.

C'est une leçon réellement utile pour toute conception CI/CD : **deux
pipelines indépendants écrivant sur la même ressource partagée peuvent
ressembler exactement, de l'extérieur, à un bogue RBAC**, même lorsque
l'attribution de rôle elle-même est correcte. Le [Lab 07](lab-07-troubleshooting-rbac.md)
montre le processus méthodique pour confirmer ou infirmer cette hypothèse.

### Exercice 6.5 : Vérifier la cible et le contrat du test de fumée

L'exécution du 4 septembre [33899929713](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/33899929713)
a échoué avec un 401. Son journal montrait aussi que le job nommé staging
déployait la version 31 dans le compte PoC de production. Staging héritait
des variables de projet de production du dépôt. Les tentatives réutilisaient
la même session en échec, sans tester une nouvelle instance d'exécution.

Le workflow corrigé sélectionne explicitement le projet staging, vérifie son
point de terminaison avant le déploiement et le transmet à l'évaluation.
Il lit `.version` dans `azd ai agent show --output json` ; une version inconnue
provoque un échec plutôt qu'un identifiant horodaté fictif. Chaque tentative
utilise `--version`, `--new-session` et `--new-conversation`.

Le contrôle de contrat utilise `azd ai agent invoke --output raw`, qui
retourne du SSE et non du JSON. Il exige un delta de texte non vide et une
réponse textuelle complète de l'assistant. Il rejette les flux en erreur,
échoués, incomplets, mal formés ou vides, sans se rabattre sur une sortie
console non vide. Les preuves staging sont conservées dans l'artefact
`staging-smoke-evidence`.

Exécutez les tests locaux avant de déclencher le workflow :

```bash
bash scripts/test-agent-response.sh
actionlint -shellcheck= .github/workflows/deploy-and-evaluate.yml
```

Le 7 septembre, le validateur a accepté une réponse réelle de la version 32
du PoC avec le prompt CI et rejeté les 12 cas invalides. Cela ne vérifie ni
l'identité CI du staging ni l'exécution GitHub Actions complète. Les réponses
signalent encore l'absence de preuves MCP en direct ; un test de transport
réussi ne prouve pas le fonctionnement des outils ni la qualité des réponses.

> [!WARNING]
> Avant la partie production, créez l'environnement GitHub `production` avec
> des approbateurs obligatoires et vérifiez sa fédération OIDC et ses variables.
> Le 7 septembre, seuls `staging` et `github-pages` existaient ; la déclaration
> `environment: production` seule n'impose pas d'approbation manuelle.
> La promotion reconstruit le code au lieu de promouvoir l'artefact testé,
> et le rollback existant redéploie le code actuel au lieu de restaurer la
> version enregistrée. Ces points bloquent une mise en production fiable ;
> un test de fumée réussi ne constitue pas une approbation de production.

## Vérification des connaissances

* Quel pipeline déclencheriez-vous pour tester un changement en toute sécurité avant qu'il n'atteigne l'environnement PoC partagé ?
* Que bloque réellement la porte d'évaluation pour la promotion ?
* Quelle est l'hypothèse de concurrence pour les 401 intermittents, et comment la testeriez-vous ?

## Prochaine étape

Passez au [Lab 07 : Dépannage réel : erreur RBAC 401](lab-07-troubleshooting-rbac.md).
