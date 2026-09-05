---
nav_exclude: true
lang: fr
layout: default
title: Accueil
description: Atelier pratique et progressif pour héberger un système multi-agent LangGraph sur Microsoft Foundry Hosted Agents.
nav_order: 0
permalink: /fr/
---

> 🇬🇧 **[English version](../)**

# Atelier Foundry Hosted Agents

Bienvenue dans l'**Atelier Foundry Hosted Agents** — un atelier pratique et
progressif construit directement à partir d'une véritable preuve de
concept : héberger un **système multi-agent LangGraph d'évaluation des
menaces** sur **Microsoft Foundry Hosted Agents**, appuyé par des serveurs
d'outils MCP indépendants exécutés sur Azure Container Apps.

Vous déploierez les serveurs d'outils MCP, provisionnerez un projet
Foundry et un agent hébergé, l'invoquerez, le soumettrez à des évaluations
déterministes et de type LLM-as-judge, parcourrez le pipeline CI/CD qui
promeut un candidat en production, et — fait unique — apprendrez une
véritable investigation de dépannage de plateforme, encore ouverte à ce
jour, en utilisant uniquement l'interface en ligne de commande Azure.

> [!NOTE]
> Cet atelier est construit à partir du dépôt
> [`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents)
> — chaque commande, capture d'écran et extrait de journal dans ces
> laboratoires provient de ce déploiement réel, pas d'une simulation.

## À qui s'adresse cet atelier ?

| Public | Ce que vous apprendrez |
|---|---|
| **Ingénieurs IA / plateforme** | Déployer un système multi-agent LangGraph sur Foundry Hosted Agents de bout en bout |
| **Ingénieurs DevOps** | Câbler des pipelines CI/CD contrôlés par des évaluations autour d'un déploiement d'agent |
| **Architectes de solutions** | Comparer Foundry Hosted Agents aux options LangGraph/LangSmith auto-hébergées |
| **Ingénieurs support / SRE** | Apprendre une méthode rigoureuse de dépannage des permissions RBAC Azure |

## Prérequis

Avant de commencer le Lab 00, assurez-vous de disposer des éléments
suivants :

- [Visual Studio Code](https://code.visualstudio.com/) (dernière version stable)
- [Python](https://www.python.org/) 3.13
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Azure CLI (`az`)](https://learn.microsoft.com/cli/azure/install-azure-cli)
- Un abonnement Azure avec accès à Microsoft Foundry et un quota de modèle `gpt-4o-mini`
- Un [compte GitHub](https://github.com/) avec accès à GitHub Copilot (facultatif, utilisé au Lab 01)

## Labs

| # | Lab | Durée | Niveau |
|---|-----|----------|-------|
| 00 | [Prérequis et configuration de l'environnement](labs/lab-00-setup.md) | 20 min | Débutant |
| 01 | [Plongée dans l'architecture](labs/lab-01-architecture.md) | 30 min | Débutant |
| 02 | [Déployer les serveurs d'outils MCP](labs/lab-02-mcp-servers.md) | 30 min | Intermédiaire |
| 03 | [Provisionner et déployer l'agent hébergé](labs/lab-03-deploy-agent.md) | 35 min | Intermédiaire |
| 04 | [Invoquer l'agent et lire les traces](labs/lab-04-invoke-agent.md) | 30 min | Intermédiaire |
| 05 | [Évaluations : déterministes + LLM-as-judge](labs/lab-05-evaluations.md) | 40 min | Intermédiaire |
| 06 | [CI/CD : pipeline de mise en production contrôlé par évaluation](labs/lab-06-cicd.md) | 35 min | Avancé |
| 07 | [Dépannage réel : erreur RBAC 401](labs/lab-07-troubleshooting-rbac.md) | 40 min | Avancé |
| 08 | [Préparation à la production et portes de décision](labs/lab-08-production-readiness.md) | 30 min | Avancé |

## Horaire de l'atelier

### Demi-journée (3 heures)

| Heure | Activité |
|------|----------|
| 0:00 – 0:20 | Lab 00 : Prérequis |
| 0:20 – 0:50 | Lab 01 : Plongée dans l'architecture |
| 0:50 – 1:20 | Lab 02 : Déployer les serveurs d'outils MCP |
| 1:20 – 1:55 | Lab 03 : Provisionner et déployer l'agent hébergé |
| 1:55 – 2:10 | Pause |
| 2:10 – 2:40 | Lab 04 : Invoquer l'agent et lire les traces |
| 2:40 – 3:00 | Lab 05 : Évaluations (début) |

### Journée complète (6 heures)

| Heure | Activité |
|------|----------|
| 0:00 – 3:00 | Labs de la demi-journée (ci-dessus) |
| 3:00 – 3:15 | Pause |
| 3:15 – 3:40 | Lab 05 : Évaluations (suite) |
| 3:40 – 4:15 | Lab 06 : Pipeline CI/CD |
| 4:15 – 4:55 | Lab 07 : Dépannage réel : erreur RBAC 401 |
| 4:55 – 5:10 | Pause |
| 5:10 – 5:40 | Lab 08 : Préparation à la production et portes de décision |
| 5:40 – 6:00 | Conclusion et questions |

## Niveaux de livraison

| Niveau | Labs | Durée | Public |
|---|---|---|---|
| **Demi-journée** | Labs 00 – 05 (début) | ~3 heures | Première exposition à Foundry Hosted Agents |
| **Journée complète** | Labs 00 – 08 | ~6 heures | Déploiement, évaluation, CI/CD et dépannage de bout en bout |

## Pour commencer

1. Clonez ou forkez le dépôt [`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents).
2. Complétez le [Lab 00 : Prérequis](labs/lab-00-setup.md) pour configurer votre environnement.
3. Progressez dans les labs dans l'ordre — chaque lab s'appuie sur le précédent.

> **Astuce** : Les Labs 02–04 utilisent des ressources déjà déployées pour
> cet atelier (serveurs MCP, projet Foundry). Si vous exécutez votre propre
> environnement, le Lab 03 vous montre comment tout provisionner depuis
> zéro avec `azd`.

## Deck de présentation

Un deck de présentation compagnon (anglais et français) est disponible pour
une animation par un formateur :

- [Deck d'aperçu — Anglais (PPTX)](../assets/decks/foundry-hosted-agents-workshop-en.pptx)
- [Deck d'aperçu de l'atelier — Français (PPTX)](../assets/decks/foundry-hosted-agents-workshop-fr.pptx)

## Ressources connexes

| Ressource | Description |
|------------|-------------|
| [Dépôt `foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents) | Code source complet du PoC, infra, suite d'évaluation et pipelines CI/CD |
| [Wiki du projet](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki) | Notes d'architecture, contournement manuel de l'agent, journal d'investigation RBAC 401 |
| [Livrables de décision](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/deliverables) | Grille de décision de mise en production et deck de décision exécutif |

## Licence

Ce projet est sous licence [MIT](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/LICENSE).
