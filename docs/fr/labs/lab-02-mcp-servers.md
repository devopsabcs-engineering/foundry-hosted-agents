---
permalink: /fr/labs/lab-02-mcp-servers
lang: fr
title: "Lab 02 - Déployer les serveurs d'outils MCP"
description: "Explorer, exécuter et tester les deux serveurs d'outils MCP indépendants qui alimentent les spécialistes de l'agent."
---

> 🇬🇧 **[English version](../../labs/lab-02-mcp-servers)**

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 30 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Lab 01](lab-01-architecture.md) |

## Objectifs d'apprentissage

À la fin de ce lab, vous serez capable de :

* Expliquer ce que chaque serveur d'outils MCP expose et pourquoi les données sont simulées
* Construire les deux images à distance sans installer Docker
* Confirmer que les Container Apps déployées sont actives et répondent à de vrais appels d'outils
* Expliquer pourquoi les serveurs MCP sont versionnés/déployés indépendamment de l'agent

## Exercices

### Exercice 2.1 : Lire le code des serveurs

Les deux serveurs se trouvent sous [`mcp/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/mcp) et sont construits avec **FastMCP** :

| Serveur | Outils | Objectif |
| --- | --- | --- |
| `mcp/defender-server` | `get_device_risk`, `list_vulnerabilities` | Données simulées de risque d'appareil et de vulnérabilités Microsoft Defender |
| `mcp/anomaly-server` | `score_anomaly`, `detect_login_anomalies` | Notation d'anomalies simulée |

Ouvrez `mcp/defender-server/main.py` et `mcp/anomaly-server/main.py`.
Notez que chacun est une application FastMCP autonome avec son propre
`Dockerfile` — rien ici n'importe depuis `src/threat-assessment-agent/`.

### Exercice 2.2 : Construire et déployer vos propres serveurs

Utilisez PowerShell 7.3 ou ultérieur à la racine du dépôt, avec l'environnement
virtuel du Lab 00 actif. Ces ressources sont facturables. Utilisez un
abonnement approuvé et un nouveau groupe, jamais un groupe client existant.
Les points de terminaison sont publics et sans authentification, uniquement
pour les données fictives. Ne connectez pas de vraies données Defender et
n'envoyez aucune information client.

Remplacez l'abonnement ci-dessous. Gardez ce terminal ouvert pour le Lab 03.

```powershell
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$SubscriptionId = '<approved-subscription-id>'
$Suffix = [guid]::NewGuid().ToString('N').Substring(0, 8)
$WorkshopEnv = "fha-learn-$Suffix"
$ResourceGroup = "rg-$WorkshopEnv"
$Location = 'eastus2'
$Registry = "acrfhalearn$Suffix"
$McpPrefix = 'mcp-learn'
$ImageTag = 'workshop-v1'
az account set --subscription $SubscriptionId
az account show --subscription $SubscriptionId --query '{name:name,id:id,tenantId:tenantId}'
if ((az group exists --subscription $SubscriptionId --name $ResourceGroup) -eq 'true') {
    throw 'Choose a new workshop name; this group already exists.'
}
az group create --subscription $SubscriptionId --name $ResourceGroup --location $Location `
  --tags purpose=workshop-validation "workshopEnv=$WorkshopEnv" --output none
azd auth login
azd env new $WorkshopEnv --subscription $SubscriptionId --location $Location
azd env set AZURE_RESOURCE_GROUP $ResourceGroup -e $WorkshopEnv
az acr create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name $Registry --sku Basic --admin-enabled false --output none
```

Déployez le réseau partagé une seule fois, avant les piles d'environnement. Faites
approuver la plage `10.30.0.0/16` par le responsable réseau ; en cas de chevauchement,
adaptez tous les préfixes de sous-réseaux dans l'aperçu et le déploiement. Ce groupe
apprenant utilise la paire de sous-réseaux nommée production, car `$WorkshopEnv`
ne se termine pas par `-staging`. Ces noms ne le rendent pas productif. Pour des
ressources existantes, consultez [Réseau Cosmos privé](../private-networking.md).

```powershell
$VnetName = "vnet-$WorkshopEnv"
$NetworkParameters = @("vnetName=$VnetName", "location=$Location")
az deployment group what-if --subscription $SubscriptionId --resource-group $ResourceGroup `
  --template-file infra/network.bicep --parameters @NetworkParameters
```

Approuvez uniquement le nouveau réseau, cinq sous-réseaux, la zone DNS privée et
son lien dans votre groupe apprenant. Ce modèle est leur propriétaire unique ; ne
le déployez pas séparément pour staging et production et ne supprimez pas les
sous-réseaux de l'autre environnement.

```powershell
az deployment group create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-network --template-file infra/network.bicep --parameters @NetworkParameters --output none
$NetworkOutputs = az deployment group show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-network --query properties.outputs -o json | ConvertFrom-Json
$AcaSubnetId = $NetworkOutputs.acaProductionSubnetId.value
azd env set VNET_NAME $VnetName -e $WorkshopEnv
```

Construisez les vraies images MCP. Les images quickstart par défaut du
modèle Bicep sont des espaces réservés, pas des serveurs MCP fonctionnels.
Les builds distants nécessitent l'autorisation d'exécuter ACR Tasks,
mais pas Docker Desktop.

```powershell
az acr build --subscription $SubscriptionId --registry $Registry `
  --image "defender:$ImageTag" ./mcp/defender-server
az acr build --subscription $SubscriptionId --registry $Registry `
  --image "anomaly:$ImageTag" ./mcp/anomaly-server
$LoginServer = az acr show --subscription $SubscriptionId --name $Registry --query loginServer -o tsv
$DefenderImage = "${LoginServer}/defender:$ImageTag"
$AnomalyImage = "${LoginServer}/anomaly:$ImageTag"
azd env set MCP_ACR_NAME $Registry -e $WorkshopEnv
azd env set MCP_NAME_PREFIX $McpPrefix -e $WorkshopEnv
azd env set DEFENDER_MCP_IMAGE $DefenderImage -e $WorkshopEnv
azd env set ANOMALY_MCP_IMAGE $AnomalyImage -e $WorkshopEnv
$McpParameters = @("namePrefix=$McpPrefix", "acrName=$Registry", "defenderImage=$DefenderImage", "anomalyImage=$AnomalyImage")
$McpParameters += "infrastructureSubnetId=$AcaSubnetId"
az deployment group what-if --subscription $SubscriptionId --resource-group $ResourceGroup `
  --template-file infra/modules/mcp-container-apps.bicep --parameters @McpParameters
```

Vérifiez que l'aperçu cible uniquement votre nouveau groupe. Déployez, puis
récupérez les URL dans les sorties, sans copier celles du formateur.
Le préfixe `mcp-learn` active une identité dédiée au téléchargement des
images, avec le rôle `AcrPull` limité à votre registre.

```powershell
az deployment group create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-mcp --template-file infra/modules/mcp-container-apps.bicep `
  --parameters @McpParameters --output none
$McpOutputs = az deployment group show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-mcp --query properties.outputs -o json | ConvertFrom-Json
$env:DEFENDER_MCP_URL = "https://$($McpOutputs.defenderContainerAppFqdn.value)/mcp"
$env:ANOMALY_MCP_URL = "https://$($McpOutputs.anomalyContainerAppFqdn.value)/mcp"
az containerapp list --subscription $SubscriptionId --resource-group $ResourceGroup `
  --query '[].{name:name,state:properties.provisioningState,fqdn:properties.configuration.ingress.fqdn}' -o table
```

Les deux applications doivent afficher `Succeeded`. Un conteneur actif ne
prouve pas que MCP fonctionne : effectuez le test ci-dessous. En cas
d'échec, examinez l'erreur avant de réessayer. Ne remplacez pas votre
registre ou vos URL par ceux d'un client existant.

### Exercice 2.3 : Appeler un vrai outil sur le réseau

Le dépôt fournit un script de test ad hoc,
[`scripts/test_mcp_servers.py`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/scripts/test_mcp_servers.py),
qui se connecte en **HTTP en streaming** et appelle les quatre outils,
indépendamment de Foundry. Vos URL sont obligatoires. Un outil absent,
une réponse vide, une erreur de protocole ou d'application, ou un délai
de 90 secondes dépassé fait échouer le test.

```powershell
python scripts/test_mcp_servers.py --defender-url $env:DEFENDER_MCP_URL --anomaly-url $env:ANOMALY_MCP_URL
```

Attendez quatre appels réussis et un code de sortie zéro. Le test des
vulnérabilités utilise `device-001`, qui possède des vulnérabilités fictives
connues. D'autres scénarios représentent volontairement une télémétrie
absente et ne servent pas à vérifier la disponibilité.

> [!NOTE]
> Ce test vérifie le chemin réseau depuis votre poste, pas l'identité ou
> le réseau de l'agent. En cas d'échec, vérifiez les URL, la connectivité,
> les journaux des conteneurs et les données fictives. S'il réussit mais que
> l'agent échoue, examinez la Toolbox, les permissions, l'accès au modèle
> et les journaux de l'agent.

### Exercice 2.4 : Pourquoi un déploiement indépendant ?

`mcp/defender-server` et `mcp/anomaly-server` possèdent leur propre
`Dockerfile` et Container App. Bicep les déploie ; ce ne sont pas des
services distincts dans le fichier `azure.yaml` racine. Cela signifie :

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

Si vous arrêtez ici ou si le déploiement échoue, terminez le [Lab 09 : Nettoyage](lab-09-teardown.md).
