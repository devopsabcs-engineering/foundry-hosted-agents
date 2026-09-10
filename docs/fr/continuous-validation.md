---
lang: fr
title: Validation continue et tendances des tests
description: Exécuter les tests de régression et les sondes de staging dans GitHub Actions et conserver les tendances dans le wiki.
nav_order: 0.5
---

> **[English version](../continuous-validation.md)**

## Cadence

Le workflow `Continuous Validation` exécute les tests hors ligne à chaque push sur `main`,
à chaque pull request et sur déclenchement manuel. Une fois ces tests réussis, les exécutions
sur `main` évaluent l'agent de staging existant avec le jeu de référence et lancent cinq requêtes
Responses concurrentes. Les pull requests ne reçoivent aucun identifiant Azure et n'exécutent
pas de tests en ligne.

Ce workflow ne provisionne, ne déploie et ne promeut rien ; il n'invoque pas la production.
Le SHA du code de test identifie les tests extraits, pas nécessairement le code exécuté en staging.
Les évaluations ciblent la version active découverte. La sonde de charge utilise la route de staging,
avec vérification de la version avant et après le test. Les latences ne sont pas publiées si cette
route change ou ne peut pas être vérifiée.

`Deploy and Evaluate (Staging -> Production)` reste manuel et soumis à approbation. Ses résultats
hors ligne et ses évaluations alimentent aussi les tendances. Le point d'entrée de déploiement
manuel délègue au même pipeline protégé et ne constitue pas un chemin direct sans contrôles.

Les opérations Azure partagent le groupe de concurrence `foundry-shared-environments`.
Le pipeline de publication conserve ce verrou pendant l'approbation de production et la surveillance.
La validation en ligne attend alors son tour. Avec `queue: max`, GitHub conserve jusqu'à 100
exécutions ou jobs en attente sans remplacer les précédents. Une file pleine peut encore provoquer
une annulation ; les modifications Azure externes ou manuelles échappent à ce verrou.
Les exécutions échouées ou annulées restent visibles dans le tableau de suivi.

## Mesures

| Famille de tests | Mesures publiées | Comportement en cas d'échec |
| --- | --- | --- |
| Graphe d'agent et tests déterministes | Tests JUnit réussis, échoués, ignorés et somme des durées | Le job échoue ; les résultats collectés sont conservés |
| Vérifications shell | Résultat de chaque étape dans le résumé et le JSON agrégé | Une vérification échouée fait échouer le job source |
| Évaluations hébergées de référence | Captures, erreurs de capture, violations de politique déterministe, nombre de reçus d'outils et trois taux de réussite des juges | Les contrôles stricts de capture, de preuve et de qualité restent appliqués |
| Sonde de charge concurrente | Succès, erreurs, durée totale, p50/p95 des requêtes réussies et nombre de requêtes fixé à cinq | HTTP autre que 200, événement incomplet ou en erreur, JSON mal formé ou absence de texte assistant terminé font échouer la sonde |

Le contrat de charge est `completed-text-v2`. Chaque requête a un délai maximal de 180 secondes ;
l'étape CI est limitée à cinq minutes. La CLI accepte de 1 à 20 échantillons pour les expériences
manuelles, mais la CI fixe la concurrence à cinq. Un delta de texte et exactement un message assistant
terminé sont requis. Les requêtes échouées ne contribuent jamais aux latences des succès.
Sans succès, la latence est indisponible, pas nulle.

Les tests en ligne utilisent des données synthétiques. Cinq échantillons ne démontrent ni une capacité,
ni un SLA, ni un percentile de queue statistiquement stable. L'ancien mode `sequential-cold-start`
ne prouve pas un démarrage à froid de l'hôte et n'est pas planifié par la CI. Les anciens JSON de charge
reposaient sur un autre contrat de réussite et sont exclus de la nouvelle série. Les refus de sécurité
vérifiés restent des contrôles déterministes, pas des réussites attribuées aux juges.

## Résumés et historique du wiki

Les compteurs hors ligne, résumés d'évaluation et mesures de charge figurent dans les résumés des jobs
sources. `Publish Test Trends` démarre à la fin d'une validation ou publication de confiance sur `main`,
y compris après un échec ou une annulation. Son résumé présente les mesures agrégées, le résultat de
chaque job et contrôle, ainsi qu'un lien vers la tentative source exacte. Il conserve un artefact
téléchargeable `ci-report-<run>-<attempt>`.

Le workflow de publication extrait le code de suivi depuis `main`, vérifie le dépôt, la branche,
l'événement et le chemin du workflow source, puis télécharge uniquement les artefacts autorisés pour
cette tentative. Il n'exécute jamais leur contenu et n'extrait pas de code de pull request.
L'autorisation Azure OIDC appartient uniquement au job en ligne. La publication utilise un accès
Actions en lecture seule et un identifiant distinct pour le wiki.

Après une publication réussie, le wiki contient :

* [Continuous-Test-Trends](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/Continuous-Test-Trends), avec graphiques Mermaid et tableaux liés aux exécutions et tentatives exactes
* `trend-history/<run-id>-<attempt>.json`, avec preuves agrégées durables sans prompts ni réponses

Le tableau affiche les 50 dernières tentatives ; chaque graphique présente jusqu'à 12 mesures
disponibles. Les étiquettes associent V (validation) ou R (publication), le numéro d'exécution du
workflow et la tentative. Les liens du tableau donnent les identifiants complets. Les axes des barres
commencent à zéro ; les taux des juges utilisent toute la plage de 0 à 100 %.

Les fichiers d'historique restent dans le dépôt du wiki. Republier la même tentative est idempotent ;
l'expiration des artefacts sources n'efface pas les mesures déjà conservées. Les valeurs manquantes
apparaissent comme `N/A` et sont omises des graphiques, jamais converties en zéros. Les workflows
échoués restent dans le tableau même si certaines mesures individuelles ont réussi.

### Croissance de la suite de tests

Le wiki présente un inventaire lié aux exécutions et des graphiques distincts pour le total hors ligne,
le graphe d'agent, les évaluations déterministes et les tests des contrats de suivi et de charge.
Les compteurs proviennent des cas JUnit, y compris les tests ignorés. Les contrôles shell restent des
résultats par étape, sans nombre de cas inventé. Les catégories JUnit inconnues sont regroupées sous
`Other JUnit` lorsqu'elles existent.

Chaque colonne représente une exécution ou tentative mesurée, pas un cumul d'exécutions.
De nouveaux tests augmentent l'inventaire ; réexécuter une suite inchangée laisse son nombre stable.
Les suppressions apparaissent comme des diminutions. Le total hors ligne inclut déjà ses composants :
ne les additionnez pas une seconde fois.

Les cas d'évaluation en ligne, contrôles terminés des juges et requêtes de charge ont leurs propres
graphiques de compteurs. Ils peuvent se recouper ou répéter des scénarios ; ils ne constituent ni des
tests hors ligne supplémentaires, ni une preuve de croissance de la couverture. Les résultats absents
restent `N/A`. Une exécution partielle peut présenter moins de tests disponibles. Les résumés hors ligne
et de publication incluent aussi la répartition par type.

Les anciens agrégats sans compteurs par type restent `N/A` pour cette répartition. Republiez leurs
tentatives sources tant que les artefacts JUnit sont disponibles pour récupérer ces mesures.
Une nouvelle validation ajoute une colonne ; republier la même tentative actualise son point sans
le dupliquer.

Les séries d'évaluation sont séparées par empreintes du jeu de données et du code d'évaluation,
déploiement du juge et environnement. Un changement du modèle derrière le même nom de déploiement
du juge n'est pas automatiquement détecté : utilisez un nouveau nom pour conserver des séries
comparables séparées. Le tableau indique aussi les changements de version de l'agent.
Une version de déploiement n'est pas un SHA source.

Les artefacts bruts hors ligne et en ligne sont conservés 30 jours pour la validation, les artefacts
d'évaluation de publication sept jours et les rapports agrégés 90 jours. L'historique assaini du wiki
survit à cette rétention. Les artefacts bruts peuvent contenir des prompts et réponses synthétiques ;
ils ne sont pas copiés dans le wiki.

## Activer la publication

Les workflows doivent être fusionnés ou poussés sur `main` pour s'exécuter automatiquement.
La première publication réussie crée la page du wiki ; ajouter les fichiers localement ne suffit pas.

1. Vérifiez les variables de l'environnement GitHub `staging` : `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
   `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP` et `FOUNDRY_MODEL_NAME`. L'identité OIDC doit déjà
   pouvoir invoquer staging et créer ou lire les évaluations. Le workflow n'ajoute aucun rôle.
2. Dans **Settings > Secrets and variables > Actions**, créez `WIKI_PUSH_TOKEN` avec un identifiant
   approuvé par votre organisation et capable de cloner et pousser le wiki. Limitez son accès au dépôt
   requis lorsque possible. Un jeton classique pour un wiki privé ou interne nécessite les droits
   `repo` appropriés et les approbations SSO requises. Vérifiez la compatibilité du wiki avant de choisir
   un jeton à permissions fines ou une GitHub App.
3. Ne collez aucun secret dans le chat ou les workflows. Ne réutilisez pas un identifiant Azure pour
   le wiki. Le workflow ne suppose pas que `GITHUB_TOKEN` peut pousser vers ce dépôt distinct.
4. Poussez les changements approuvés ou déclenchez `Continuous Validation` sur `main` après publication.
5. Vérifiez l'exécution source et son exécution `Publish Test Trends`. Confirmez que la page du wiki
   contient le bon identifiant et la bonne tentative, puis ajoutez-la au menu du wiki si nécessaire.

Sans `WIKI_PUSH_TOKEN`, l'étape wiki échoue volontairement avec un message indiquant la correction
nécessaire. Le résumé agrégé et le rapport téléchargeable sont produits avant cette étape et restent
disponibles. Une validation locale ne prouve ni une exécution CI en ligne ni une publication du wiki.

## Republier une tentative

Déclenchez `Publish Test Trends` avec le `run_id` source terminé et son `attempt`. Le rapport est
reconstruit sans invoquer l'agent ni redéployer. Faites-le tant que les artefacts sources sont disponibles.
Les artefacts propres à chaque tentative évitent de présenter les précédents comme actuels.
Une réexécution partielle peut laisser des mesures absentes pour les jobs non relancés.

La publication wiki possède son propre groupe de concurrence avec file d'attente. Elle prépare
uniquement la page générée et `trend-history/`, sans toucher aux autres pages. Une modification manuelle
concurrente peut faire rejeter le push Git ; le workflow ne force jamais le push. Relancez la publication
pour cloner le nouvel état du wiki et réessayer.

## Vérification locale

```powershell
.venv/Scripts/python.exe -m pytest scripts/tests/test_ci_results.py experiments/load-testing/test_load_test.py -q
.venv/Scripts/python.exe -m ruff check scripts/ci_results.py scripts/tests/test_ci_results.py experiments/load-testing/load_test.py experiments/load-testing/test_load_test.py
actionlint -ignore 'unexpected key "queue" for "concurrency" section' .github/workflows/*.yml
```

L'exception ciblée pour `actionlint` est nécessaire tant que son schéma ne reconnaît pas le champ
[`queue: max`](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
documenté par GitHub. Les autres contrôles de syntaxe, d'expressions et de shell restent actifs.
Retirez cette exception dès que le linter reconnaît le champ. Les tests ciblés couvrent les faux succès
de charge, les erreurs CLI, les preuves absentes, les taux nuls des juges, la republication de l'historique,
les changements de route et les graphiques générés à partir de données synthétiques.
