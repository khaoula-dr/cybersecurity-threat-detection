# Résultats (Cybersecurity Threat Detection System)

Région : eu-north-1 · Dataset : UNSW-NB15 · Modèle : XGBoost 1.7-1 (conteneur intégré SageMaker)

## 1. Synthèse par rapport aux objectifs

| Objectif | Cible | Résultat | Statut |
| --- | --- | --- | --- |
| AUC (test officiel) | ≥ 0,95 | 0,984 | Atteint |
| F1 (test officiel, seuil 0,5) | ≥ 0,90 | 0,897 | Manqué de 0,003, écart expliqué (voir 5 et 11) |
| Latence d'inférence à chaud | < 1 s | 145 à 176 ms | Atteint |
| Latence au premier appel (démarrage à froid) | < 1 s | 3,4 à 3,8 s | Non atteint |
| Coût total | < 50 USD | environ 0,10 USD (estimation AWS du 2026-10-10, mise à jour toutes les 24 h) | Atteint |

## 2. Données, features, découpage

Détails dans `docs/features.md` et `docs/dataset.md`.

- Train 140 273 lignes, validation 35 068, test officiel 82 332 (conservé tel quel).
- 63 features (36 numériques, 6 `proto`, 13 `service`, 8 `state`), cible en première colonne, CSV sans en-tête.
- Exclues : `id`, `attack_cat`, `stcpb`, `dtcpb`, `ct_ftp_cmd`.
- Les attaques sont majoritaires (68,1 % du train, 55,1 % du test) : `scale_pos_weight` laissé à 1.

## 3. Entraînement (US-09)

- Job : `sagemaker-xgboost-2026-10-08-10-10-11-366` (ml.m5.large), 244 s facturées (environ 0,003 $).
- AUC validation 0,9937, AUC train 0,9956.

## 4. Évaluation sur le test officiel (US-10), seuil 0,5

| Métrique | Valeur |
| --- | --- |
| AUC | 0,984 |
| F1 | 0,897 |
| Recall | 0,984 |
| Precision | 0,824 |
| Accuracy | 0,875 |

Matrice de confusion : TN 27 449 · FP 9 551 · FN 732 · TP 44 600.

Le modèle rate peu d'attaques (732 sur 45 332, soit 1,6 %) mais déclenche 25,8 % de fausses alertes sur le trafic normal.
La validation (AUC 0,994) est plus favorable que le test : les deux jeux n'ont pas la même distribution.

## 5. Choix du seuil

Seuil 0,5, choisi sur la validation (meilleur F1 : 0,970). Le test n'a pas servi à choisir.

| Seuil | F1 test | Precision | Recall |
| --- | --- | --- | --- |
| 0,3 | 0,864 | 0,763 | 0,997 |
| 0,5 | 0,897 | 0,824 | 0,984 |
| 0,7 | 0,922 | 0,892 | 0,955 |

Un seuil plus haut réduit les fausses alertes mais manque davantage d'attaques. Le seuil 0,5 respecte le garde-fou de recall ≥ 0,97.
Le seuil 0,7 atteindrait F1 ≥ 0,90, mais l'adopter reviendrait à le choisir en regardant le test.

## 6. Attaques manquées par type (test, seuil 0,5) : 732

Fuzzers 627 (10,3 %) · Exploits 60 (0,5 %) · Analysis 33 (4,9 %) · DoS 5 · Reconnaissance 3 · Shellcode 3 · Generic 1 · Backdoor 0 · Worms 0.
Les Fuzzers (trafic aléatoire proche du normal) représentent 86 % des attaques manquées.

## 7. Importance des features (gain)

sttl 3534 · ct_srv_dst 136 · ct_dst_sport_ltm 100 · proto_other 85 · swin 71 · service_http 64 · proto_udp 56 · smean 55.

`sttl` pèse environ 26 fois la deuxième feature. Dans le train, `sttl = 254` correspond à 90 % d'attaques et `sttl = 31` à 100 % de trafic normal.
Le modèle exploite très probablement une particularité du banc d'essai. Cette dépendance n'a pas été testée par ablation (voir 11).

## 8. Pipeline SageMaker (US-16, US-17)

Étapes : Preprocess → Train → Evaluate → CheckQuality → RegisterModel.
Paramètres externalisés : `InputData`, `MinF1` (0,89), `MinAUC` (0,95). Sorties sous `s3://.../pipeline/`, sans toucher à `processed/` ni `models/`.

- **Reproductibilité :** l'AUC de validation du pipeline (0,99365) est identique à celle de l'entraînement manuel, et le modèle fait 218,1 Ko dans les deux cas.
  Les fichiers CSV du pipeline sont un peu plus gros (train 29,4 Mo contre 27,4 Mo) : cause non vérifiée, probablement le formatage des nombres.
- **Évaluation :** `evaluation.json` du pipeline est identique à l'évaluation manuelle (AUC 0,9837, F1 0,8966, recall 0,9839, precision 0,8236, même matrice).
- **Exécution complète (MinF1 = 0,89) :** les cinq étapes en `Succeeded`, version 2 `Approved` dans le Model Registry.
- **Test de rejet (MinF1 = 0,95) :** `CheckQuality` sans `RegisterModel`, exécution `Succeeded`, registre inchangé à la version 2.
- **Incident :** `RegisterModel` a échoué (AccessDenied sur `sagemaker:CreateModelPackageGroup`). La policy du pipeline était incomplète. L'action a été ajoutée, puis l'exécution reprise avec `retry-pipeline-execution`, sans refaire le prétraitement ni l'entraînement.
- **Seuil `MinF1 = 0,89` :** fixé après avoir vu le F1 du test (0,8966). Un seuil à 0,90 aurait rejeté le modèle. C'est un choix a posteriori, à signaler.

## 9. Déploiement et inférence JSON (US-12 à US-14)

Chaîne : JSON → Lambda `ctds-inference` → endpoint SageMaker (CSV) → `{prediction, probability}`.
Le conteneur XGBoost intégré attend du CSV : une Lambda d'adaptation range les features dans l'ordre de `columns.json`, complète les champs absents avec les médianes du train (`defaults.json`) et applique le seuil 0,5.
Les prédictions sont d'autant plus fiables que l'appelant fournit de champs. Les variables `ct_*`, calculées sur des fenêtres de connexions, sont ici remplacées par des médianes.

Latence mesurée (Duration Lambda, CloudWatch et test de bout en bout) :

- à chaud : 132 à 176 ms ;
- premier appel (démarrage à froid) : 3 355 à 3 777 ms. Cause probable : initialisation (import boto3, lecture de `columns.json` et `defaults.json`) avec 256 Mo de mémoire. Non testé : charger au démarrage, plus de mémoire, concurrence provisionnée (payante).
- endpoint seul (test CSV) : 15 à 30 ms, 163 ms au premier appel.

## 10. Tests de bout en bout (US-18) et logs (US-15)

Date : 2026-10-10. Endpoint déployé puis supprimé (liste vide vérifiée).

| Cas | Résultat | Probabilité | Latence (1er appel, 2e appel) |
| --- | --- | --- | --- |
| Attaque Exploits | Suspicious | 0,999 | 3 777 ms (à froid), 158 ms |
| Normal, sttl = 62 | Normal | 0,2347 | 173 ms, 155 ms |
| Normal, sttl = 254 | Suspicious | 0,6083 | 145 ms, 176 ms |

- Les probabilités sont identiques à celles d'un déploiement précédent : le déploiement est reproductible.
- Le troisième cas est un faux positif connu. Le test vérifie que la limite est reproduite, pas que le modèle a raison.
- **Déclencheur S3 (US-11) :** un upload de `raw/UNSW_NB15_training-set.csv` régénère `processed/` (vérifié à deux reprises, dont 2026-10-10 à 11:03).
- **Erreur volontaire (US-15) :** `{"sttl": "abc"}` lève `ValueError: could not convert string to float: 'abc'`, retrouvée dans `/aws/lambda/ctds-inference`.
- **Logs disponibles :** `/aws/lambda/ctds-preprocessing`, `/aws/lambda/ctds-inference`, `/aws/sagemaker/TrainingJobs`, `/aws/sagemaker/Endpoints/ctds-endpoint`.
- Erreurs réelles aussi retrouvées pendant la mise au point : ImportModuleError, Task timed out, ValidationError (endpoint absent).
- Tests unitaires : 5 tests `pytest` (prétraitement et inférence).

## 11. Limites

- **Dépendance à `sttl` :** probable artefact du banc d'essai, généralisation incertaine sur un vrai réseau. Un réentraînement sans `sttl` (et sans `ct_state_ttl`) permettrait de la mesurer. Il n'a pas été réalisé.
- **Distribution :** train et test diffèrent (68 % contre 55 % d'attaques), et la proportion d'attaques est irréaliste (sur un vrai réseau, elles sont rares). Le taux de fausses alertes serait à réévaluer en conditions réelles.
- **F1 de 0,897 :** 0,003 sous l'objectif, au seuil de 0,5 choisi sur la validation.
- **Fuzzers :** 86 % des attaques manquées.
- **Features `ct_*` :** remplacées par des médianes à l'inférence si l'appelant ne les fournit pas.
- **Démarrage à froid :** 3,4 à 3,8 s au premier appel.
- **Déclencheur S3 :** la Lambda lit des noms de fichiers fixes, donc valable pour ce dataset uniquement.
- **Lambda de prétraitement :** limitée à 15 minutes et à la mémoire allouée. Pour de gros volumes, il faudrait Glue ou SageMaker Processing (déjà utilisé dans le pipeline).
- **Seuils du pipeline :** `MinF1 = 0,89` fixé après observation du résultat.

## 12. Écarts au cahier des charges

- Projet piloté avec le compte root (MFA actif) : IAM Identity Center et l'accès console IAM ne sont pas disponibles sur le plan gratuit.
- Pas d'alerte budget configurable sur le plan gratuit : suivi manuel dans Cost Explorer, plafond de 100 $ de crédits.
- Pas de `ml/train.py` : le conteneur XGBoost intégré n'en a pas besoin.
- `ml/inference.py` remplacé par `lambda/inference.py` (adaptation JSON dans une Lambda plutôt que dans le conteneur).
- Stretch non réalisés : alertes SNS, dashboard et alarmes CloudWatch, Model Monitor, Infrastructure as Code, KMS et CloudTrail.

## 13. Coûts

Coût total estimé du projet : **environ 0,10 USD** sur 120 USD de crédits (relevé du 2026-10-10 dans la page Billing).
Le montant « utilisé » réel est à 0,00 USD tant que la facture n'est pas finalisée.

| Poste | Ordre de grandeur |
| --- | --- |
| Entraînement manuel | environ 0,003 $ (244 s) |
| Pipelines (3 exécutions) et 3 déploiements d'endpoint, supprimés après chaque test | inclus dans le total |

Les estimations AWS sont mises à jour environ toutes les 24 h : les dernières exécutions du 2026-10-10 peuvent ne pas y figurer.
Aucun endpoint actif à la fin du projet (`aws sagemaker list-endpoints` renvoie une liste vide).

