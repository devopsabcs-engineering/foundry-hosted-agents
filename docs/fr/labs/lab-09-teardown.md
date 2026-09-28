---
permalink: /fr/labs/lab-09-teardown
lang: fr
title: "Lab 09 - Nettoyage et arrêt des coûts"
description: "Prévisualiser, supprimer et vérifier uniquement vos ressources apprenant étiquetées."
---

[English version](../../labs/lab-09-teardown)

## Aperçu

Prévoyez 10 à 20 minutes, suppression Azure comprise. Terminez ce lab même si le
déploiement ou l'évaluation a échoué. Arrêter l'agent ne supprime pas le registre,
les journaux ni les autres ressources facturables.

## Conserver vos preuves

Conservez localement les résultats non secrets de `.azure/workshop-evaluation/`,
`.azure/workshop-conversation/` et `.azure/workshop-load.json` avant la suppression.
Ne commitez pas `.azure/` : ce dossier contient l'état des environnements et peut
contenir des données de connexion. Notez votre environnement, compte, version
d'agent et ID d'exécution d'évaluation. Les captures historiques ne sont pas vos preuves.

## Prévisualiser le groupe exact

Utilisez les variables du Lab 02 dans la même session PowerShell. Si vous avez
perdu la session, récupérez votre abonnement approuvé, environnement et groupe
dans vos notes et `azd env list` ; ne devinez pas et ne copiez pas le groupe du formateur.

```powershell
./scripts/remove-workshop.ps1 -SubscriptionId $SubscriptionId -EnvironmentName $WorkshopEnv -ResourceGroup $ResourceGroup
```

Le script liste les ressources sans rien supprimer. Il exige le nom
`rg-<votre environnement fha-learn-*>` et les deux étiquettes du Lab 02 :
`purpose=workshop-validation` et `workshopEnv=<votre environnement>`.
Une différence arrête le script. N'ajoutez jamais ces étiquettes à un groupe client
existant pour contourner le contrôle. Faites vérifier les étiquettes manquantes
et la propriété du groupe avec votre formateur.

## Retirer l'identité du chat web

Si vous avez déployé le chat web au Lab 04, supprimez aussi son inscription
d'application et son groupe de sécurité. Ce sont des objets du tenant : la
suppression du groupe de ressources ne les retire pas.

```powershell
$ChatAppId = az ad app list --display-name "$WorkshopEnv web chat" --query '[0].appId' -o tsv
if ($ChatAppId) { az ad app delete --id $ChatAppId }
$ChatGroupId = az ad group list --display-name "$WorkshopEnv-chat-users" --query '[0].id' -o tsv
if ($ChatGroupId) { az ad group delete --group $ChatGroupId }
```

## Supprimer et vérifier

> [!CAUTION]
> La suppression retire toutes les ressources du groupe affiché : modèle, projet
> d'agent, applications MCP, images et journaux. Procédez uniquement pour votre
> groupe jetable. N'exécutez pas `azd down` depuis un environnement partagé ; les
> formateurs utilisent la procédure contrôlée à la fin de ce lab.

```powershell
./scripts/remove-workshop.ps1 -SubscriptionId $SubscriptionId -EnvironmentName $WorkshopEnv -ResourceGroup $ResourceGroup -Delete -ConfirmResourceGroup $ResourceGroup
az group exists --subscription $SubscriptionId --name $ResourceGroup
```

Vérifiez l'invite de confirmation et n'approuvez que l'abonnement/groupe exact.
Attendez la fin. La réussite exige `Verified absent` et `false` au contrôle
indépendant, pas seulement l'acceptation de la demande. Si la suppression échoue,
examinez les verrous et les politiques avec l'administrateur ; ne les retirez pas
pour contourner l'erreur. Une nouvelle exécution après suppression affiche `Already absent`.

Fermez les terminaux contenant les variables de l'atelier. Gardez l'état local
`.azure/` jusqu'à la vérification, puis supprimez uniquement le dossier de votre
environnement apprenant si vous n'en avez plus besoin. Ne supprimez pas l'état
local d'un autre environnement.

## Portée et vérifications restantes

Votre groupe jetable contient le réseau, les délégations et le lien DNS du Lab 02,
ainsi que le point privé et les checkpoints si vous avez exécuté l'expérience Cosmos.
Conservez les preuves approuvées avant de supprimer ces données. N'appliquez jamais
cette suppression à la fondation partagée staging/production et ne retirez pas ses
sous-réseaux séparément. Des associations de service peuvent retarder la suppression ;
examinez les échecs avec l'administrateur sans supprimer de dépendances partagées.

Supprimer le groupe ne garantit pas la suppression des identités d'agent Entra
du tenant, des identifiants OIDC GitHub ou des enregistrements de service conservés
en suppression réversible. L'atelier de base ne crée pas d'environnement GitHub ;
l'inscription d'application et le groupe du chat web facultatif sont retirés par
l'étape ci-dessus. Faites examiner les identités conservées par un
administrateur autorisé ; ne supprimez pas d'identités partagées et ne purgez pas
d'enregistrements récupérables sans approbation. Consultez Cost Management plus
tard : des frais d'utilisation peuvent apparaître après le nettoyage.

L'atelier est terminé lorsque vos résultats et limites sont consignés et que
l'absence du groupe de ressources est vérifiée.

## Formateur seulement : supprimer l'environnement partagé Air Canada

> [!WARNING]
> Cette procédure supprime l'environnement partagé staging et production, y compris
> toutes les versions d'agent, le pilote de chat web, les images de conteneur et les
> données Cosmos. Seul le propriétaire de l'environnement l'exécute, après avoir
> exporté les preuves à conserver.

L'environnement partagé couvre deux groupes de ressources :

| Groupe de ressources | Contenu | Supprimé par |
|---|---|---|
| `rg-air-canada-threat-assessment-poc` | Comptes, projets et agents Foundry ; applications de conteneur MCP et chat web ; registre ; Cosmos DB ; VNet et DNS privé ; supervision | `azd down --force --purge` (groupe géré par azd) |
| `rg-air-canada-threat-assessment-msi` | `msi-air-canada-threat-assessment`, l'identité OIDC GitHub utilisée par tous les workflows | `az group delete` (non géré par azd) |

`azd down` seul ne suffit pas : il ne connaît que le groupe géré par azd, et Foundry
refuse de supprimer un compte tant que des projets existent.
`scripts/teardown-air-canada.ps1` l'encapsule. Le script enregistre un inventaire,
supprime les projets et les hôtes de capacité Foundry, exécute
`azd down --force --purge` (avec repli sur `az group delete`), purge les comptes
Foundry en suppression réversible, supprime le groupe d'identité, retire les
attributions de rôle orphelines de l'identité au niveau de l'abonnement et vérifie
l'absence des deux groupes. Les groupes `ME_*` gérés par Container Apps
disparaissent automatiquement.

### Depuis votre poste

Exécutez depuis la racine du dépôt, connecté à l'abonnement Air Canada, avec
l'environnement azd local `air-canada-threat-assessment-poc`. La première commande
prévisualise seulement ; la seconde supprime les deux groupes :

```powershell
./scripts/teardown-air-canada.ps1
./scripts/teardown-air-canada.ps1 -Delete -ConfirmResourceGroups 'rg-air-canada-threat-assessment-poc,rg-air-canada-threat-assessment-msi'
```

La réussite exige `Verified absent` pour les deux groupes.

### Depuis GitHub Actions

Ouvrez **Actions > Teardown Air Canada Environment > Run workflow** :

1. Prévisualisation : laissez **execute** décoché, puis examinez le journal du job
   et l'artefact `air-canada-teardown-inventory-<run>`.
2. Suppression des charges de travail : cochez **execute** et saisissez
   `rg-air-canada-threat-assessment-poc` dans **confirm_resource_groups**.
   L'approbation de l'environnement `production` s'applique. L'identité du pipeline
   est conservée ; vous pouvez relancer le workflow.
3. Dernière exécution facultative : cochez aussi **delete_pipeline_identity** et
   confirmez les deux groupes, séparés par une virgule. L'exécution supprime sa
   propre identité ; elle ne fait donc que demander la suppression. Vérifiez-la
   localement :

```powershell
az group exists --name rg-air-canada-threat-assessment-msi
```

Une fois l'identité supprimée, chaque workflow du dépôt échoue à la connexion Azure
jusqu'à ce que vous recréiez l'identité, ses identifiants fédérés, ses rôles et les
variables du dépôt. Ses attributions de rôle au niveau de l'abonnement deviennent
orphelines ; retirez-les avec les ID de l'artefact d'inventaire.

Les objets du tenant hors des deux groupes restent : inscriptions d'application du
chat web, groupes de sécurité du pilote et identités d'agent Entra. Retirez-les
séparément avec l'approbation d'un administrateur du tenant.
