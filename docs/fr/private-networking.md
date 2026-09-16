---
title: Cosmos privé et Foundry public
description: Réseau hybride, limites de migration et vérification de Cosmos privé pour l'atelier d'évaluation des menaces.
permalink: /fr/private-networking
---

[English version](../private-networking.md)

> [!WARNING]
> La migration partagée n'est pas terminée. Les opérations Cosmos privées et la
> santé du chat web sont validées, mais la création de session en staging renvoie
> `Project not found` et bloque la promotion en production. Voir le
> [compte rendu daté](../../deliverables/hybrid-network-validation-20260915.md).

## Périmètre réseau

Cette configuration suit le modèle hybride du dépôt FSI. Ce n'est pas un
déploiement entièrement privé et elle ne garantit pas la conformité aux politiques
hors de ce périmètre.

| Composant | Accès | Responsabilité |
| --- | --- | --- |
| Compte Foundry | Point de terminaison public ; clients authentifiés | Sous-réseau dédié à l'injection pour les sorties de l'agent |
| Container Apps MCP | HTTPS public, données fictives uniquement | Environnement avec profils de charge et sorties dans le VNet |
| Expérience de checkpoints Cosmos | Accès public désactivé ; authentification Entra uniquement | Point de terminaison privé SQL, groupe de zone DNS et RBAC de données |
| Registre, chat web, supervision | Modèle d'accès existant conservé | Revues de sécurité distinctes ; pas de privatisation par ce changement |

Cosmos reste facultatif. `infra/main.bicep` ne le déploie pas et `azure.yaml`
n'active pas `ENABLE_COSMOS_CHECKPOINTER`. La connectivité privée n'active pas la
persistance, ne remplace pas le stockage géré par Foundry et ne prouve pas une
exécution durable exactement une fois.

## Propriété du réseau partagé

Déployez `infra/network.bicep` une seule fois par groupe avant les piles
d'environnement. Il possède le VNet, les cinq sous-réseaux, la zone
`privatelink.documents.azure.com` et son lien. Les modèles d'environnement utilisent
des références `existing` pour éviter les écritures concurrentes sur le même VNet.
Une modification ultérieure doit préserver tous les sous-réseaux et leurs
associations de service. Ne redéployez jamais un inventaire partiel.

| Sous-réseau | CIDR par défaut | Consommateur |
| --- | --- | --- |
| `snet-aca-production` | `10.30.0.0/23` | Environnement Container Apps de production |
| `snet-aca-staging` | `10.30.2.0/23` | Environnement Container Apps de staging |
| `snet-agent-production` | `10.30.4.0/24` | Compte Foundry de production |
| `snet-agent-staging` | `10.30.5.0/24` | Compte Foundry de staging |
| `snet-private-endpoints` | `10.30.6.0/24` | Points de terminaison privés Cosmos |

Les quatre premiers sont délégués à `Microsoft.App/environments`. Le dernier n'a
pas de délégation et désactive les politiques réseau des points de terminaison
privés. Chaque compte Foundry possède son propre sous-réseau d'agent. Un nom
d'environnement terminé par `-staging` sélectionne staging ; tous les autres
sélectionnent la paire nommée production.

Le responsable réseau doit approuver les plages sans chevauchement, les routes,
la propriété DNS et les permissions avant le déploiement. Adaptez tous les CIDR
ensemble si nécessaire. Si le DNS est centralisé, utilisez son transfert et sa
zone approuvés plutôt qu'une zone concurrente. Le modèle suppose une zone dans
le même groupe de ressources et le DNS fourni par Azure sur le VNet.

## Nouvel environnement d'atelier

Le [Lab 02](labs/lab-02-mcp-servers.md) prévisualise et déploie le réseau dans un
nouveau groupe jetable, enregistre `VNET_NAME` et fournit le sous-réseau à MCP.
Le [Lab 03](labs/lab-03-deploy-agent.md) exécute le contrôle en lecture seule
`scripts/test-network-readiness.ps1` avant Foundry. L'abonnement Azure CLI courant
doit correspondre à l'environnement azd ; le contrôle utilise cet abonnement.

Compilez sans créer d'artefacts de déploiement ni contacter Azure :

```powershell
az bicep build --file infra/network.bicep --stdout | Out-Null
az bicep build --file infra/main.bicep --stdout | Out-Null
az bicep build --file infra/modules/cosmos-db.bicep --stdout | Out-Null
```

La compilation ne prouve pas la disponibilité régionale, la conformité aux
politiques, la capacité, les permissions ou la connectivité. Examinez `what-if`
avant chaque déploiement réel.

## Migration d'un environnement partagé existant

Pour la migration Air Canada approuvée avec réutilisation des noms, utilisez le
workflow manuel `teardown-hybrid-migration.yml`. Lancez d'abord `execute=false`
avec `confirm_resource_group=rg-air-canada-threat-assessment-poc`, puis examinez
l'artefact d'inventaire et le résultat what-if. Lancez ensuite `execute=true` avec
la même confirmation. Les deux exécutions utilisent l'approbation de production
et le verrou de déploiement partagé. Le script refuse les apps dépendantes
inattendues et les ressources déjà intégrées au réseau.

Le workflow conserve les empreintes des images, identités et URL, provisionne le
réseau approuvé, puis supprime uniquement les cinq apps autorisées, deux
environnements MCP et deux comptes Foundry. Il purge ces comptes pour réutiliser
leurs noms. Cosmos, ACR, la supervision et les identités attribuées par
l'utilisateur restent en place. La purge détruit les anciennes versions hébergées :
l'inventaire permet une récupération, mais ne constitue ni une sauvegarde des
données ni un retour arrière exécutable. Redéployez avec `deploy-and-evaluate.yml`
et `bootstrap_after_teardown=true`. Ce mode ignore la recherche d'une ancienne
version seulement si un inventaire Azure réussi prouve l'absence du compte de
production. Tous les contrôles de release restent obligatoires. Restaurez le chat
web séparément avec son image conservée et actualisez son URI de connexion.

Pour un compte Cosmos existant, déployez
`infra/modules/cosmos-private-endpoint.bicep` avec `accountName`, `location`,
`privateEndpointSubnetId` et `privateDnsZoneId`. Prévisualisez les modifications et
n'acceptez que le point de terminaison et son DNS. Ce module réseau référence le
compte existant sans redéployer ses paramètres, sa base ou son conteneur. Réservez
le module complet `cosmos-db.bicep` aux nouveaux comptes expérimentaux ; ne
l'appliquez pas aux politiques d'un compte existant sans examiner les différences.

N'exécutez pas les exercices de création contre le groupe PoC existant. Les anciens
comptes Foundry n'ont pas d'injection réseau et les anciens environnements Container
Apps n'ont pas de sous-réseau d'infrastructure. Traitez cela comme une migration,
pas comme de simples paramètres modifiables. Le contrôle bloque le provisionnement
si les paramètres existants diffèrent. Il ne supprime ni ne recrée de ressources.

1. Inventoriez les ID des comptes/projets, versions d'agent, environnements des apps,
   rôles, URL, URI de redirection et données Cosmos. Conservez les cibles de retour arrière.
2. Obtenez les approbations réseau, politique et migration. Préférez un groupe staging
   séparé, de nouveaux noms de comptes/environnements uniques et un sous-réseau dédié
   neuf. N'attachez pas un deuxième compte à un sous-réseau déjà occupé.
3. Prévisualisez et déployez le réseau complet sous un propriétaire unique. Alignez
   la variable de dépôt `VNET_NAME` et celle d'azd. Si les noms d'environnement
   changent, adaptez ceux du workflow staging/production ainsi que ses variables
   approuvées de points de terminaison et de ressources dans la migration.
4. Provisionnez et déployez staging. Rétablissez les rôles limités de la nouvelle
   identité d'agent, le modèle et la Toolbox. Adaptez les cibles du chat web et les
   URI de connexion modifiées. Vérifiez le chat authentifié avant Cosmos facultatif.
5. Exécutez les tests DNS et de données ci-dessous, puis testez séparément le runtime
   hébergé si les checkpoints sont retenus. Conservez les preuves de version,
   d'identité et de réseau. Ne baissez pas les seuils d'évaluation et ne réutilisez
   pas le résultat d'une ancienne release.
6. Migrez la production après une nouvelle release et l'approbation requise.
   Gardez l'ancienne route pour le retour arrière jusqu'à l'acceptation ; retirez
   ensuite les anciennes ressources séparément.

La réutilisation des noms exige un plan d'indisponibilité et de récupération
explicitement approuvé. Un provisionnement d'agent échoué peut laisser des
associations de service ; inspectez-les et utilisez un nouveau sous-réseau approuvé
si nécessaire, sans suppression aveugle. Ce changement ne migre aucune ressource réelle.

## Déploiement Cosmos facultatif

Utilisez les variables et `$NetworkOutputs` de votre propre Lab 02. Ces commandes
créent du stockage et un point de terminaison privé facturables. Indiquez l'ID objet
de l'identité exécutant l'expérience ; ne supposez pas qu'il s'agit de l'identité
du compte/projet Foundry. L'agent reçoit sa propre identité lors du déploiement.

```powershell
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$ExperimentPrincipalId = '<approved-experiment-identity-object-id>'
$CosmosAccount = "cosmos-$WorkshopEnv"
$PrincipalIds = ConvertTo-Json -InputObject @($ExperimentPrincipalId) -Compress
$CosmosParameters = @(
    "environmentName=$WorkshopEnv", "accountName=$CosmosAccount", "location=$Location",
    "privateEndpointSubnetId=$($NetworkOutputs.privateEndpointSubnetId.value)",
    "privateDnsZoneId=$($NetworkOutputs.cosmosPrivateDnsZoneId.value)",
    "dataPlanePrincipalIds=$PrincipalIds"
)
az deployment group what-if --subscription $SubscriptionId --resource-group $ResourceGroup `
  --template-file infra/modules/cosmos-db.bicep --parameters @CosmosParameters
```

Approuvez uniquement vos ressources d'expérience et le rôle Cosmos limité. Ne donnez
pas d'accès au principal historique du fichier d'exemple. Ce fichier seul ne suffit
plus : les ID du sous-réseau et de la zone DNS sont obligatoires.

```powershell
az deployment group create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-cosmos --template-file infra/modules/cosmos-db.bicep `
  --parameters @CosmosParameters --output none
$Cosmos = az cosmosdb show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name $CosmosAccount -o json | ConvertFrom-Json
if ($Cosmos.publicNetworkAccess -ne 'Disabled' -or -not $Cosmos.disableLocalAuth) {
    throw 'Cosmos access policy mismatch'
}
$Endpoint = az network private-endpoint show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name "pe-$CosmosAccount" -o json | ConvertFrom-Json
if (@($Endpoint.privateLinkServiceConnections | Where-Object {
    $_.privateLinkServiceConnectionState.status -eq 'Approved'
}).Count -ne 1) { throw 'Private endpoint is not approved' }
$env:COSMOS_ENDPOINT = $Cosmos.documentEndpoint
```

`Succeeded` et `Approved` concernent le plan de contrôle uniquement. Le modèle
conserve la base `threat-assessment-agent`, le conteneur `checkpoints` et
`/partition_key`. Il ne migre ni ne supprime les documents de checkpoint existants.

## Vérifier le chemin de données privé

Exécutez les contrôles suivants depuis un poste ou runner approuvé disposant d'une
route vers le point privé et de la résolution DNS liée. Les runners GitHub hébergés
ordinaires et les postes publics n'ont pas ce chemin. Récupérez vos propres variables
sur cette machine ; n'utilisez pas d'ancienne URL et ne partagez pas de jetons.

```powershell
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$PrivateAddresses = @(az network nic show --subscription $SubscriptionId `
  --ids $Endpoint.networkInterfaces[0].id --query 'ipConfigurations[].privateIPAddress' -o json | ConvertFrom-Json)
$ResolvedAddresses = @([System.Net.Dns]::GetHostAddresses(([uri]$env:COSMOS_ENDPOINT).DnsSafeHost) |
    Where-Object { $_.AddressFamily -eq 'InterNetwork' } | ForEach-Object { $_.IPAddressToString })
if (-not $ResolvedAddresses.Count -or @($ResolvedAddresses | Where-Object { $_ -notin $PrivateAddresses }).Count) {
    throw 'Cosmos DNS does not resolve exclusively to this private endpoint'
}
$env:ENABLE_COSMOS_CHECKPOINTER = 'true'
$env:COSMOS_DATABASE_NAME = 'threat-assessment-agent'
$env:COSMOS_CONTAINER_NAME = 'checkpoints'
try {
    python experiments/cosmos-checkpointer/benchmark.py
    if ($LASTEXITCODE -ne 0) { throw 'Cosmos benchmark failed' }
} finally {
    Remove-Item Env:ENABLE_COSMOS_CHECKPOINTER -ErrorAction SilentlyContinue
}
```

Le benchmark écrit des documents fictifs et produit des preuves locales. Vérifiez
les résultats des opérations Cosmos directes et de LangGraph ; une réussite depuis
un poste ne prouve pas le chemin ou l'identité de l'agent hébergé. Avant d'activer
les checkpoints d'un candidat hébergé, accordez à son identité réelle le RBAC Cosmos
et testez la persistance et l'isolation des threads sur ce runtime. N'activez pas le
flag dans la release de base uniquement parce qu'un point privé existe. L'expérience
historique bloquée reste historique, pas un nouveau benchmark réussi.

## CI et preuves

Le workflow compile les trois modèles, contrôle le réseau avant le what-if staging
et répète le contrôle avant les provisionnements staging et production. Il ne
redéploie pas le réseau partagé. Une infrastructure absente ou incompatible bloque
la release. OIDC, évaluations, approbation et supervision restent obligatoires.
L'accès public Foundry permet aux runners existants d'invoquer l'agent, pas
d'exécuter des tests directs sur le plan de données Cosmos.

Conservez des preuves distinctes pour les politiques effectives, l'approbation du
point privé, DNS/IP, les opérations Cosmos authentifiées, la persistance hébergée
et les contrôles de release. Compilation et mocks ne suffisent pas pour ces tests réels.

## Nettoyage et références

Utilisez le [Lab 09](labs/lab-09-teardown.md) uniquement pour votre groupe apprenant
jetable étiqueté. Ses points privés et son réseau sont inclus dans la suppression
du groupe. Ne supprimez jamais une zone DNS, un VNet ou un sous-réseau encore utilisé
par un autre environnement. Supprimer Cosmos détruit l'état de l'expérience ;
conservez les preuves approuvées avant le nettoyage.

* [Réseau Foundry en détail](https://learn.microsoft.com/azure/foundry/agents/concepts/agents-networking-deep-dive)
* [Pare-feu et déploiement du code source](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code#firewall-requirements-for-private-virtual-networks)
* [Points de terminaison privés Cosmos](https://learn.microsoft.com/azure/cosmos-db/how-to-configure-private-endpoints)
