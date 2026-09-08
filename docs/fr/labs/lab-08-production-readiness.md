---
permalink: /fr/labs/lab-08-production-readiness
lang: fr
title: "Lab 08 - Préparation à la production et portes de décision"
description: "Lire la grille de décision de mise en production du PoC et comprendre comment des expériences par phases alimentent une décision go/no-go conditionnelle."
---

> 🇬🇧 **[English version](../../labs/lab-08-production-readiness)**

## Aperçu

| | |
|---|---|
| **Durée** | 30 minutes |
| **Niveau** | Avancé |
| **Prérequis** | [Lab 07](lab-07-troubleshooting-rbac.md) |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Expliquer la différence entre les statuts de porte « Pass », « Conditional », « Fail » et « Not testable in this PoC »
* Associer chaque porte de décision de production à l'expérience qui a produit sa preuve
* Expliquer pourquoi un PoC peut honnêtement recommander un « go conditionnel » plutôt qu'un oui/non net
* Localiser le deck de décision exécutif et la grille utilisés pour communiquer cela aux parties prenantes

## Exercices

### Exercice 8.1 : Les quatre pistes d'expérimentation

Ouvrez [`experiments/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/experiments) :

| Piste | Question à laquelle elle répond | Résultat |
|---|---|---|
| `load-testing/` | Combien de sessions concurrentes avant qu'un problème survienne ? | Partiel — aucun plafond observé à 1-20 concurrentes, mais la plage cible (10-100) n'a pas été entièrement testée |
| `cosmos-checkpointer/` | L'agent peut-il utiliser Cosmos DB comme état LangGraph durable ? | Partiel — infra déployée et un vrai bogue trouvé et corrigé, mais le benchmark en direct a été bloqué par une politique réseau du tenant imposant un accès privé uniquement |
| `agent365-onboarding/` | Cet agent peut-il être enregistré sous Entra Agent ID / Agent 365 ? | Bloqué, mais validement — le tenant n'a pas la licence Agent 365 ; la sonde s'est arrêtée correctement plutôt que de simuler un succès |
| `continuous-evaluation/` | Le trafic de production peut-il être évalué en continu ? | Bloqué par une lacune RBAC corrigible (rôle `Foundry User` manquant sur l'identité managée du projet pour lister les jeux de données) |

Ouvrez `experiments/load-testing/report.md` et trouvez sa section
**« Honest scope statement »** — notez comment elle indique explicitement
ce qui n'a *pas* été testé, plutôt que d'extrapoler silencieusement à
partir d'un échantillon plus petit.

### Exercice 8.2 : Lire la grille de décision

Ouvrez [`deliverables/production-decision-gate-scorecard.md`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/deliverables/production-decision-gate-scorecard.md)
et trouvez sa légende de statuts :

| Statut | Signification |
|---|---|
| **Pass** | Les preuves recueillies dans ce PoC satisfont directement la porte |
| **Conditional** | Des preuves partielles existent ; un suivi précis et nommé comble l'écart |
| **Fail** | Les preuves recueillies contredisent ou échouent la porte telle que testée |
| **Not testable in this PoC** | Nécessite une confirmation commerciale/juridique/plateforme distincte (tarification, SLA, licence du tenant) |

Trouvez la ligne de la porte **Quality** — c'est la seule porte marquée
**Pass** sans condition. Retracez son indicateur de preuve jusqu'aux
artefacts exacts du [Lab 05](lab-05-evaluations.md) : le jeu de données de
référence et la porte déterministe stricte, puis les huit captures, 21/21
vérifications, le refus d'injection et les 28 reçus d'outils de l'exécution
34178081808. Ce succès sur des données synthétiques ne prouve pas une
efficacité statistique sur des données client réelles.

### Exercice 8.3 : Pourquoi un « go conditionnel », pas un oui/non net

Lisez la section **Overall recommendation** de la grille. Elle recommande
un **go conditionnel pour poursuivre l'investissement PoC vers pilote**,
explicitement conditionné par :

1. Des responsables sécurité, données et opérations nommés, avec revue de l'accès MCP public et de l'autorisation.
2. Des tests de charge étendus avec MCP fonctionnel et une récupération manuelle répétée.
3. Une confirmation commerciale/SLA/tarification et l'acceptation des previews.
4. De nouveaux tests d'évaluation continue, Cosmos et Agent 365 seulement si retenus pour le pilote.

WI-11 est résolu opérationnellement et le pipeline complet a réussi ; ce
n'est plus un blocage ouvert du pilote.

C'est un schéma délibérément honnête : le rôle d'un PoC est de **séparer
ce qui est prouvé de ce qui reste à prouver**, pas de fabriquer une fausse
confiance dans un sens ou dans l'autre.

### Exercice 8.4 : Le deck exécutif

Ouvrez [`deliverables/deck-outline.md`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/deliverables/deck-outline.md)
et sa **légende de balisage de confiance** :

| Tag | Signification |
|---|---|
| `confirmed` | Établi directement par la documentation produit, des échantillons, ou les propres tests de ce PoC |
| `preview` | Documenté mais explicitement une capacité preview/bêta |
| `inferred` | Synthétisé à partir de faits confirmés séparément mais jamais observés fonctionner ensemble |
| `requires-validation` | Documenté, mais une limite, un SLA, un prix ou un chemin d'intégration reste non vérifié |

Chaque affirmation du deck compilé
(`deliverables/air-canada-foundry-hosted-agents-decision.pptx`, généré par
`scripts/build-deck.js`) porte l'un de ces quatre tags — un schéma que
vous pouvez réutiliser chaque fois que vous devez présenter des résultats
techniques à un public de parties prenantes non techniques sans exagérer
la certitude.

## Vérification des connaissances

* Quelle porte est la seule marquée « Pass » sans condition, et quelle preuve la soutient ?
* Pourquoi l'expérience d'intégration Agent 365 a-t-elle compté comme un résultat valide même si elle était « bloquée » ?
* Quels sont les quatre tags de confiance utilisés dans le deck exécutif, et quelle est la différence entre `inferred` et `requires-validation` ?

## Conclusion de l'atelier

Vous venez de parcourir un PoC complet, de l'architecture au déploiement,
à l'invocation, à l'évaluation, au CI/CD, à une véritable investigation de
dépannage résolue, jusqu'à une recommandation honnête de
préparation à la production. Le code source complet de tout ce qui figure
dans cet atelier se trouve dans
[`devopsabcs-engineering/foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents) —
forkez-le, et le [wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki)
conserve l'historique WI-11, les preuves actuelles et les limites restantes.
