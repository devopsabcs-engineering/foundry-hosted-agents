---
permalink: /fr/labs/lab-06-cicd
lang: fr
title: "Lab 06 - CI/CD : pipeline de mise en production contrôlé par évaluation"
description: "Parcourir le chemin protégé commun, la validation continue, les approbations, la télémétrie et les limites de capacité."
ms.date: 2026-09-10
---

> 🇬🇧 **[English version](../../labs/lab-06-cicd)**

## Aperçu

| Élément | Valeur |
| --- | --- |
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

Le réseau doit être prêt avant le provisionnement d'une release. La CI compile
`network.bicep`, `main.bicep` et le module Cosmos facultatif, puis contrôle le réseau
avant le what-if staging et les deux provisionnements. Elle ne déploie pas le réseau
partagé et ne recrée pas de ressources incompatibles. Un échec exige la
[migration approuvée](../private-networking.md), pas un contrôle affaibli. Les runners
publics peuvent invoquer Foundry mais pas tester Cosmos directement sans route privée.

Ce lab combine une répétition locale des contrôles et une inspection en lecture
seule des preuves historiques GitHub Actions. **Ne déclenchez pas les workflows
partagés de publication ou Continuous Validation, ne modifiez pas leurs
environnements et ne poussez pas sur `main` en tant qu'apprenant.** Leurs jobs
actifs ciblent des comptes partagés, pas votre environnement du Lab 02.
Une répétition complète exige un dépôt approuvé distinct, une identité OIDC,
des variables isolées et des approbateurs. L'atelier de base ne crée pas ces
ressources GitHub et ne déploie pas en production.

Exécutez les contrôles hors ligne, puis conservez vos artefacts du Lab 05 :

```powershell
bash scripts/test-agent-response.sh
bash scripts/test-agent-rbac.sh
bash scripts/test-production-version.sh
python -m pytest eval/deterministic-tests/ scripts/tests/ -q
```

Réussite : les quatre commandes se terminent sans erreur. Une réussite locale
ne vérifie ni OIDC GitHub, ni les approbations, ni la promotion ou la récupération
en production ; notez ces éléments comme inspectés, pas exécutés.

### Exercice 6.1 : Un chemin de mise en production protégé

Ouvrez [`.github/workflows/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/.github/workflows) :

| Pipeline | Déclencheur | Ce qu'il fait |
| --- | --- | --- |
| `hosted-agent-cd.yml` | Manuel (`workflow_dispatch`) | Entrée de compatibilité déléguant à `deploy-and-evaluate.yml`, avec toutes les évaluations et approbations. |
| `deploy-and-evaluate.yml` | Manuel (`workflow_dispatch`) | Lint/tests → validation Bicep/what-if → staging → tests de fumée/contrat → évaluation → approbation manuelle → reconstruction du code → surveillance → récupération manuelle en cas d'échec. |
| `continuous-validation.yml` | Push, pull request, manuel | Régressions hors ligne ; sur main, évaluations staging et cinq flux simultanés sans déploiement. |
| `web-chat-build.yml` | Push ciblé, pull request, manuel | Tests d'autorisation/sessions, tests frontend, artefact compilé. Aucun déploiement Azure. |

Les deux entrées de publication sont manuelles. Continuous Validation fonctionne
aussi sur push/PR et son job actif sur main appelle le staging partagé.
Le verrou commun évite les exécutions concurrentes ; il ne sécurise pas une
cible d'environnement incorrecte.

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
Il résout la route active à distance ; version inconnue ou ambiguë : échec,
pas d'identifiant horodaté fictif. Chaque tentative utilise
`scripts/invoke-agent.sh` pour créer une session liée à la version et envoyer
l'historique fourni avec `store:false`, sans identifiants de conversation natifs.

Le contrôle valide le flux Responses SSE brut du script, pas du JSON seul.
Il exige un delta de texte non vide et une
réponse textuelle complète de l'assistant. Il rejette les flux en erreur,
échoués, incomplets, mal formés ou vides, sans se rabattre sur une sortie
console non vide. Les preuves staging sont conservées dans l'artefact
`staging-smoke-evidence`.

Contrôle facultatif pour les mainteneurs (`actionlint` à installer séparément) :

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

### Exercice 6.8 : Portes actuelles de publication, charge et télémétrie

Ouvrez la [mise en production 34427432731](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34427432731)
et la [validation continue 34427429700](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34427429700).
Les deux ont réussi sur `15098b7`. Les images précédentes restent historiques.

1. Examinez `hosted-agent-cd.yml` : délégation au même workflow protégé, sans contourner les évaluations ou approbations.
2. Ordre des approbations : **Promote to production**, puis **Post-deploy monitoring check** à sa demande. **Continuous Validation** n'a pas besoin d'approbation manuelle ; elle attend le verrou partagé `foundry-shared-environments`. Ne dupliquez pas les exécutions en attente.
3. Vérifiez les preuves de rappel, d'isolation et de `store:false`. Capture, test de fumée et charge doivent partager le contrat supporté.
4. Téléchargez `load-test-evidence-1` et `evaluation-evidence-1` : cinq flux terminés sans erreur, seuils qualité inchangés à 100 %, route stable avant/après.
5. Vérifiez la surveillance : identifiant brut extrait avec `jq -Rser`, trace `AppTraces` correspondante, puis contrôle glissant `AppExceptions`. Télémétrie absente ou requête invalide : échec, pas faux succès.

L'exécution `34424723263` n'avait terminé que deux requêtes sur cinq. Trois
opérations corrélées montraient des HTTP 429 du modèle. La correction approuvée
augmente uniquement staging de 10 000 à 50 000 TPM (100 à 500 RPM) ; production
reste à 10 000 TPM. `infra/main.bicep` utilise le suffixe `-staging` existant.
Évaluations et charge partagent ce quota. Le contrôle inchangé à cinq flux a
réussi ensuite ; ni SLA, ni capacité maximale, ni cause de toutes les anciennes
erreurs intermittentes ne sont ainsi établis.

Comparez `prod-agent-before.json` et l'état après déploiement conservé dans les
artefacts. Une version inchangée peut être réutilisée : l'idempotence ne signifie
pas créer une nouvelle version à chaque exécution. Les condensats MCP sont
conservés ; l'agent est reconstruit depuis le code. Récupération toujours manuelle.

La [démo du Lab 04](lab-04-invoke-agent.md) utilise les scénarios vérifiés de
la suite d'évaluation. La sélection remplit seulement le brouillon ; Send
utilise le chemin normal authentifié, lié au propriétaire.

## Vérification des connaissances

* Pourquoi un apprenant ne doit-il pas déclencher un pipeline partagé pour valider un déploiement d'atelier isolé ?
* Que bloque réellement la porte d'évaluation pour la promotion ?
* Quelle est l'hypothèse de concurrence pour les 401 intermittents, et comment la testeriez-vous ?

## Prochaine étape

Passez au [Lab 07 : Dépannage réel : erreur RBAC 401](lab-07-troubleshooting-rbac.md).
