---
title: "Isolated Workshop Validation / Validation isolée de l'atelier"
description: "Verified learner-run outcomes, fixes, cleanup evidence and remaining validation boundaries."
---

## English

The learner run used a fresh clone of `2e10a60` and iterative fixes, with a
dedicated `fha-learn-20260913` environment in East US 2. It did not change shared
Air Canada resources, GitHub environments, quota or production routing.
The tested infrastructure changes were copied into the learner clone; documentation
and additional guard tests were validated in the working repository. This was
not a second clean-room deployment of the final edited tree.

| Check | Observed result |
| --- | --- |
| Isolated infrastructure | Two remote-built MCP images, two Container Apps, Foundry project and agent version 1 deployed |
| Runtime access | Foundry User and Cognitive Services OpenAI User at the new account scope; initial Bicep assignment and helper rerun verified |
| MCP calls | All four synthetic tool calls succeeded; error responses now fail the probe |
| Existing golden dataset | 8/8 completed captures, no deterministic policy failures |
| Model judges | 21/21 passed: seven each for coherence, groundedness and task adherence |
| Conversation contract | 3/3 passed: reference, full-history follow-up and independent request |
| Bounded concurrent load | 5/5 completed streams, zero errors; p50 41.450 s, p95 43.798 s at 10k TPM |
| Telemetry | Exact smoke response ID found in the linked workspace's AppTraces |
| Local release gates | SSE, RBAC and remote-version shell regressions passed; `ruff check eval` passed |
| Final offline suite | 252 passed, 6 opt-in tests skipped, including bilingual command and PowerShell syntax checks |
| Teardown | Guarded preview and deletion completed; independent `az group exists` returned `false`; rerun returned `Already absent` |

The evaluation identifiers were `eval_4665559c3b44418e838ecac2adb32646` and
`evalrun_56eca2b1db294c109625df36e40a383e`. The deleted resource group was
`rg-fha-learn-20260913`, in subscription `64c3d212-40ed-4c6d-a825-6adfbdf25dad`.
The smoke trace had operation ID `d3f8947c11d706c1b3ef46b1296b44d9`.
Raw synthetic evaluation, conversation and load artifacts remain locally under
the learner clone's `.azure/`; they are not committed because that directory also
contains environment state and connection data.

The run exposed and repaired missing Windows prerequisites, incorrect deployment
ordering and image-variable names, absent runtime-role guidance, false-green MCP
responses, shared endpoint defaults, invalid PowerShell placeholders, incomplete
evaluation instructions, and missing cleanup. Labs 00-09 and both workshop indexes
now distinguish learner actions from historical evidence and optional admin tracks.

Shared cloud CI/CD, OIDC setup, production approvals, web-chat deployment, Cosmos
persistence and Agent 365 licensing were not executed in this isolated run.
The five-stream result is not an SLA or sustained-load guarantee. Trace ingestion
does not establish complete distributed tracing. Tenant identities, soft-deleted
service records and delayed billing were not independently audited or purged.
An authorized administrator should review any retained identities and subsequent costs.

Local Jekyll rendering was blocked by the missing Ruby MSYS2 compiler toolchain;
dependency installation stopped before a successful build. Markdown diagnostics
and bilingual PowerShell checks passed. The edits remain local: nothing was
committed, pushed or published, because pushing main triggers shared live validation.

## Français

Le parcours apprenant a utilisé un clone neuf de `2e10a60`, corrigé progressivement,
et l'environnement isolé `fha-learn-20260913` dans East US 2. Aucun changement n'a
été apporté aux ressources Air Canada partagées, aux environnements GitHub, aux
quotas ou au routage de production. Il ne s'agit pas d'un second déploiement neuf
de l'intégralité des fichiers finaux.

Les quatre outils MCP ont répondu. Les huit captures de la suite existante,
les 21 jugements et les trois tests d'historique ont réussi, sans échec de politique
déterministe. Cinq flux simultanés ont terminé sans erreur à 10k TPM ; la latence
p95 était de 43,798 secondes. Une trace correspondant à la réponse exacte a été
retrouvée dans l'espace Log Analytics lié. Les contrôles locaux finaux donnent
252 tests réussis et six tests facultatifs ignorés ; le contrôle Ruff a réussi.

Les labs 00-09 corrigent les prérequis Windows, l'ordre de déploiement, les noms
de variables d'image, les droits du runtime, les faux succès MCP, les cibles partagées,
les paramètres PowerShell invalides, l'évaluation incomplète et l'absence de nettoyage.
Les commandes apprenant sont identiques en anglais et en français et leur syntaxe
PowerShell a été vérifiée.

Le groupe `rg-fha-learn-20260913` a été supprimé après prévisualisation. Le contrôle
indépendant a renvoyé `false` et une nouvelle exécution a affiché `Already absent`.
Les résultats bruts restent dans le dossier `.azure/` local du clone apprenant,
sans être commités. Les identités de tenant et les enregistrements en suppression
réversible n'ont pas été audités ou purgés ; un administrateur doit vérifier les
éléments conservés et les frais qui peuvent apparaître ultérieurement.

Le CI/CD cloud partagé, OIDC, les approbations de production, le chat web, Cosmos
et Agent 365 n'ont pas été exécutés dans ce parcours isolé. Le test de charge ne
garantit ni SLA ni charge soutenue, et la trace ne prouve pas une instrumentation
distribuée complète. La construction Jekyll locale reste bloquée par l'absence
du compilateur Ruby MSYS2. Les diagnostics Markdown et les contrôles de commandes
bilingues ont réussi. Aucun commit, push ou publication n'a été effectué.
