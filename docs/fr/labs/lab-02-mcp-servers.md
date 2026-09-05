---
permalink: /fr/labs/lab-02-mcp-servers
lang: fr
title: "Lab 02 - Déployer les serveurs d'outils MCP"
description: "Explorer, exécuter et tester les deux serveurs d'outils MCP indépendants qui alimentent les spécialistes de l'agent."
---

> 🇬🇧 **[English version](../../labs/lab-02-mcp-servers)**

## Aperçu

| | |
|---|---|
| **Durée** | 30 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Lab 01](lab-01-architecture.md) |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Expliquer ce que chaque serveur d'outils MCP expose et pourquoi les données sont simulées
* Exécuter un serveur MCP localement et appeler un outil via stdio
* Confirmer que les Container Apps déployées sont actives et répondent à de vrais appels d'outils
* Expliquer pourquoi les serveurs MCP sont versionnés/déployés indépendamment de l'agent

## Exercices

### Exercice 2.1 : Lire le code des serveurs

Les deux serveurs se trouvent sous [`mcp/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/mcp) et sont construits avec **FastMCP** :

| Serveur | Outils | Objectif |
|---|---|---|
| `mcp/defender-server` | `get_device_risk`, `list_vulnerabilities` | Données simulées de risque d'appareil et de vulnérabilités Microsoft Defender |
| `mcp/anomaly-server` | `score_anomaly`, `detect_login_anomalies` | Notation d'anomalies simulée |

Ouvrez `mcp/defender-server/main.py` et `mcp/anomaly-server/main.py`.
Notez que chacun est une application FastMCP autonome avec son propre
`Dockerfile` — rien ici n'importe depuis `src/threat-assessment-agent/`.

### Exercice 2.2 : Confirmer que les serveurs déployés sont actifs

Les deux serveurs de cet atelier sont déjà déployés en tant qu'Azure
Container Apps. Confirmez leur statut :

```powershell
az containerapp list --resource-group <votre-groupe-de-ressources> `
  --query "[].{name:name, provisioningState:properties.provisioningState, runningStatus:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn}" `
  -o table
```

Sortie attendue :

```text
Name                 ProvisioningState    RunningStatus    Fqdn
-------------------  -------------------  ---------------  -----------------------------------------------------------------------
mcp-anomaly-server   Succeeded            Running          mcp-anomaly-server.<env>.<region>.azurecontainerapps.io
mcp-defender-server  Succeeded            Running          mcp-defender-server.<env>.<region>.azurecontainerapps.io
```

### Exercice 2.3 : Appeler un vrai outil sur le réseau

Le dépôt fournit un script de test ad hoc,
[`scripts/test_mcp_servers.py`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/scripts/test_mcp_servers.py),
qui se connecte en **HTTP en streaming** à chaque Container App et appelle
un outil — indépendamment de l'agent hébergé Foundry.

```powershell
pip install mcp
python scripts/test_mcp_servers.py
```

Sortie attendue (les valeurs peuvent différer) :

```text
=== mcp-defender-server (https://mcp-defender-server...azurecontainerapps.io/mcp) ===
tools: ['get_device_risk', 'list_vulnerabilities']
call_tool(get_device_risk, {'device_id': 'device-001'}) -> [TextContent(... "riskScore": "High" ...)]

=== mcp-anomaly-server (https://mcp-anomaly-server...azurecontainerapps.io/mcp) ===
tools: ['score_anomaly', 'detect_login_anomalies']
call_tool(score_anomaly, {'metric': 'failed_logins_per_hour', 'value': 12.0}) -> [TextContent(... "severity": "high" ...)]
```

> [!NOTE]
> Ce script prouve que les serveurs MCP fonctionnent correctement **par
> eux-mêmes** — utile pour isoler un bogue : si ce script échoue, le
> problème est dans la Container App ; s'il réussit mais que l'agent ne
> peut toujours pas atteindre un outil, le problème est dans la couche de
> connexion Foundry Toolbox, pas dans le serveur d'outils.

### Exercice 2.4 : Pourquoi un déploiement indépendant ?

`mcp/defender-server` et `mcp/anomaly-server` sont chacun leur propre
service `azd` avec leur propre `Dockerfile`, déployés sur leur propre
Container App. Cela signifie :

* Chaque serveur d'outils peut être mis à jour, mis à l'échelle ou annulé
  **sans redéployer l'agent**.
* Chaque serveur d'outils a besoin de sa propre authentification, réseau,
  versionnement, vérifications de santé et limitation de débit — la
  Foundry Toolbox n'enregistre que la *connexion*, elle n'exploite pas le
  runtime.
* Le même serveur MCP pourrait être enregistré dans plusieurs Foundry
  Toolboxes pour plusieurs agents.

## Vérification des connaissances

* Quelle couche du Lab 01 le script `scripts/test_mcp_servers.py` teste-t-il — implémentation/hébergement, ou enregistrement/consommation ?
* Si le test de l'exercice 2.3 réussit mais que l'agent signale toujours "outil indisponible", où chercheriez-vous ensuite ?

## Prochaine étape

Passez au [Lab 03 : Provisionner et déployer l'agent hébergé](lab-03-deploy-agent.md).
