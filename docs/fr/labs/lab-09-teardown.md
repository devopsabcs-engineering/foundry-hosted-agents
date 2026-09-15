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

## Supprimer et vérifier

> [!CAUTION]
> La suppression retire toutes les ressources du groupe affiché : modèle, projet
> d'agent, applications MCP, images et journaux. Procédez uniquement pour votre
> groupe jetable. N'exécutez pas `azd down` depuis un environnement partagé.

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
en suppression réversible. L'atelier de base ne crée ni environnement GitHub ni
inscription d'application web. Faites examiner les identités conservées par un
administrateur autorisé ; ne supprimez pas d'identités partagées et ne purgez pas
d'enregistrements récupérables sans approbation. Consultez Cost Management plus
tard : des frais d'utilisation peuvent apparaître après le nettoyage.

L'atelier est terminé lorsque vos résultats et limites sont consignés et que
l'absence du groupe de ressources est vérifiée.
