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
| `deploy-and-evaluate.yml` | Manuel (`workflow_dispatch`) | Lint/tests → validation Bicep/what-if → staging → tests de fumée/contrat → évaluation → approbation manuelle → reconstruction du code → surveillance → récupération manuelle en cas d'échec. |

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

Les deux workflows sont déclenchés manuellement pour éviter les déploiements
concurrents. La concurrence était une hypothèse plausible, pas une cause
prouvée du 401. Éliminer une course améliore le contrôle des mises en production,
sans établir une cause racine interne à Azure. Le [Lab 07](lab-07-troubleshooting-rbac.md)
distingue ces hypothèses du rétablissement observé.

### Exercice 6.5 : Vérifier la cible et le contrat du test de fumée

L'exécution du 4 septembre [33899929713](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/33899929713)
a échoué avec un 401. Son journal montrait aussi que le job nommé staging
déployait la version 31 dans le compte PoC de production. Staging héritait
des variables de projet de production du dépôt. Les tentatives réutilisaient
la même session en échec, sans tester une nouvelle instance d'exécution.

L'agent staging isolé possède un principal d'instance distinct de celui du PoC.
La première requête ne retournait aucune attribution de rôle. Après le
déploiement, `scripts/configure-agent-rbac.sh` découvre ce principal et lui
attribue uniquement `Foundry User` et `Cognitive Services OpenAI User` à la
portée de son compte via le module RBAC existant. L'identité CI doit pouvoir
créer ces attributions ; les erreurs de permission ne sont pas ignorées.

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

Historiquement, le 7 septembre, le validateur a accepté une réponse réelle de la version 32
du PoC avec le prompt CI et rejeté les 12 cas invalides. Cela ne vérifie ni
l'identité CI du staging ni l'exécution GitHub Actions complète. Les réponses
de cette version signalaient l'absence de preuves MCP ; un test de transport
réussi ne prouve pas le fonctionnement des outils ni la qualité des réponses.

> [!WARNING]
> Avant la partie production, créez l'environnement GitHub `production` avec
> des approbateurs obligatoires et vérifiez sa fédération OIDC et ses variables.
> Le 7 septembre, seuls `staging` et `github-pages` existaient initialement.
> L'environnement `production` a ensuite été créé avec `emmanuelknafo` comme
> approbateur obligatoire et sans contournement administrateur. L'utilisateur
> a ensuite approuvé la production pour l'exécution `34157050648`. La déclaration
> `environment: production` seule n'impose pas d'approbation manuelle sans
> ces paramètres du dépôt.
> L'exécution `34178081808` a ensuite franchi les deux portes de production
> avec approbation normale. L'agent est reconstruit depuis le code évalué ;
> les images MCP utilisent les mêmes condensats évalués. Ce n'est pas une
> promotion binaire identique de l'agent. La récupération reste manuelle,
> sans rollback automatique ni canary : des limites importantes pour une
> adoption entreprise, malgré la réussite du pipeline.

### Exercice 6.6 : Rejeter les faux succès d'évaluation

L'exécution [34157050648](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34157050648)
affichait une réussite malgré huit cas en erreur et aucun score disponible.
Le statut `completed` ne prouvait pas la qualité. Après approbation manuelle,
le déploiement de production a réussi, puis l'étape RBAC a échoué avec
`RoleAssignmentExists`. La production avait donc déjà changé.

Le workflow utilise maintenant `eval/run_hosted_evaluation.py` au lieu de faire
confiance au code de sortie de l'action de rapport. Il capture les réponses
hébergées dans des sessions neuves liées à la version, les soumet aux juges
Foundry et conserve les identifiants exacts, flux bruts, résultats et résumé
dans `evaluation-evidence`. Tous les cas doivent être présents, sans erreur,
avec des scores et une réussite pour chaque métrique pour les investigations
(100 % par défaut). Les refus vérifiés suivent la politique explicite ci-dessous.
Les données mal formées, réponses vides et scores absents provoquent un échec.

Le contexte de grounding est le scénario, pas son identifiant. Les exigences
de schéma et d'outils restent distinctes. Le serveur ajoute un état du graphe
compressé et borné aux métadonnées Responses. Seuls les résultats `ToolMessage`
réussis produisent des preuves d'appels. Le JSON rédigé par le modèle ne constitue
pas une preuve d'exécution. Les preuves absentes, mal formées ou trop volumineuses
bloquent la publication. Les rubriques personnalisées
par catégorie restent à intégrer et ne sont pas couvertes par les trois juges.

Une erreur Azure `content_filter` termine maintenant le graphe avec un refus fixe,
sans autre appel de modèle ou d'outil. Avec l'accord du propriétaire du dépôt,
seul `inject-001` accepte cette alternative : blocage confirmé par le serveur,
texte de refus exact, aucun appel d'outil et aucune investigation déclarée terminée.
Ce cas reçoit un résultat déterministe plutôt que des scores de modèle. Les autres
cas conservent leurs exigences. La capture continue après un échec, mais tout
échec bloque la publication. Les rejets du filtre ne sont pas réessayés.

Toutes les actions JavaScript des deux workflows déclarent Node.js 24.
Les téléchargements utilisent `actions/download-artifact@v7`.

Lors d'un test local antérieur, cinq cas staging ont retourné des réponses valides. Le filtre
Azure contre les jailbreaks a rejeté le cas d'injection, bloquant correctement
l'exécution. Une évaluation diagnostique d'une réponse capturée a réussi les
trois métriques sans erreur de juge, mais a échoué au contrôle des preuves.
Ce n'est pas une réussite des huit cas. Ne désactivez pas les filtres de sécurité
et n'affaiblissez pas les attentes du jeu de données pour obtenir un succès.

Le script RBAC réutilise les attributions inconditionnelles équivalentes à la
portée exacte du compte, quel que soit leur GUID, et crée seulement les rôles
manquants. Les preuves de version et l'état de production sont conservés même
après un échec partiel. Les erreurs de requête de télémétrie ne deviennent plus
un succès avec zéro exception. Ce compte seul ne prouve toutefois ni la
couverture du trafic ni la fraîcheur de la télémétrie.

```bash
bash scripts/test-agent-rbac.sh
python -m pytest eval/deterministic-tests/ -q
```

### Exercice 6.7 : Examiner la mise en production réussie

Ouvrez l'[exécution 34178081808](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34178081808).
Les sept jobs ont réussi ; la récupération a été ignorée. Staging version 6
a produit huit captures, zéro violation, 21/21 vérifications et 28 reçus d'outils.
La production est passée de 33 à 34, avec un test de fumée ciblé réussi et les
deux approbations requises. Zéro exception sur une fenêtre glissante ne prouve
ni dix minutes d'endurance après déploiement ni un traçage complet.

![Porte qualité réussie, rendu des artefacts conservés](../../assets/images/release-evaluations.png)

Reliez les [preuves conservées](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/Release-Evidence)
au commit. Les trois juges évaluent le rapport final avec le prompt et les
preuves du Composer. Le refus d'injection est vérifié de façon déterministe,
sans trois résultats de juge supplémentaires. Les appels MCP sont réels,
mais les données de sécurité sont synthétiques.

Avant de provisionner la production, le workflow découvre à distance la version
numérique qui reçoit 100 % du trafic. L'état local azd d'un runner neuf ne
suffit pas ; toute route absente ou ambiguë bloque le déploiement. Le
[guide opérationnel](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/Operations)
décrit ce contrat et la récupération manuelle.

## Vérification des connaissances

* Quel pipeline déclencheriez-vous pour tester un changement en toute sécurité avant qu'il n'atteigne l'environnement PoC partagé ?
* Que bloque réellement la porte d'évaluation pour la promotion ?
* Quelle est l'hypothèse de concurrence pour les 401 intermittents, et comment la testeriez-vous ?

## Prochaine étape

Passez au [Lab 07 : Dépannage réel : erreur RBAC 401](lab-07-troubleshooting-rbac.md).
