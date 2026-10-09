## Entraînement (US-09)
- Job : sagemaker-xgboost-2026-10-08-10-10-11-366 (ml.m5.large, XGBoost 1.7-1)
- Durée facturée : 244 s (~0,003 $)
- AUC validation : 0,9937 · AUC train : 0,9956
## Évaluation sur le test officiel (US-10), seuil 0,5
AUC 0,984 · F1 0,897 · Recall 0,984 · Precision 0,824 · Accuracy 0,875
Matrice : TN 27 449 · FP 9 551 · FN 732 · TP 44 600
Écart : F1 à 0,003 de l'objectif de 0,90. Cause : 25,8 % de fausses alertes,
liées à la différence de distribution entre train et test (attaques 68 % contre 55 %).
## Choix du seuil
Seuil 0,5, choisi sur la validation (meilleur F1 : 0,970). Évaluation sur le test, non utilisée pour choisir.

| Seuil | F1 test | Precision | Recall |
| --- | --- | --- | --- |
| 0,3 | 0,864 | 0,763 | 0,997 |
| 0,5 | 0,897 | 0,824 | 0,984 |
| 0,7 | 0,922 | 0,892 | 0,955 |
Un seuil plus haut réduit les fausses alertes mais manque davantage d'attaques ; 0,5 respecte notre garde-fou de recall ≥ 0,97.

## Attaques manquées (test, seuil 0,5) : 732 au total
Fuzzers 627 (10,3 %) · Exploits 60 (0,5 %) · Analysis 33 (4,9 %) · DoS 5 · Reconnaissance 3 · Shellcode 3 · Generic 1 · Backdoor 0 · Worms 0.
Les Fuzzers (trafic aléatoire proche du normal) représentent 86 % des attaques manquées.

## Importance des features (gain)
sttl 3534 · ct_srv_dst 136 · ct_dst_sport_ltm 100 · proto_other 85 · swin 71 · service_http 64 · proto_udp 56 · smean 55.

## Limites
- sttl domine (26 fois la 2e feature) : probable artefact du banc d'essai, généralisation incertaine sur un vrai réseau.
- Distribution train/test différente (68 % contre 55 % d'attaques) et proportion d'attaques irréaliste.
- Objectif F1 ≥ 0,90 manqué de 0,003 au seuil 0,5.
Latence Lambda (Duration, mesurée dans CloudWatch) :
- à chaud : 132 à 175 ms (objectif < 1 s atteint) ;
- premier appel (démarrage à froid) : 3 355 ms, objectif non atteint.
  Cause probable : initialisation du code (import boto3, lecture de columns.json et defaults.json)
  avec 256 Mo de mémoire. Pistes : charger au démarrage, plus de mémoire, concurrence provisionnée.
  ## MVP : inférence JSON via Lambda (US-13, US-14)
Chaîne : JSON → Lambda `ctds-inference` → endpoint SageMaker (CSV) → `{prediction, probability}`.

| Cas | Résultat | Probabilité |
| --- | --- | --- |
| Attaque Exploits (sttl 254) | Suspicious | 0,999 |
| Normal (sttl 62) | Normal | 0,235 |
| Normal (sttl 254) | Suspicious | 0,608 |

Latence Lambda (Duration, CloudWatch) :
- à chaud : 132 à 175 ms (objectif < 1 s atteint) ;
- premier appel (démarrage à froid) : 3 355 ms, objectif non atteint.
  Cause probable : initialisation (import boto3, lecture de `columns.json` et `defaults.json`) avec 256 Mo.
  Pistes : charger au démarrage, plus de mémoire, concurrence provisionnée (payante).
Latence endpoint seul (test CSV) : 15 à 30 ms, 163 ms au premier appel.

Limite : un trafic normal avec sttl = 254 est classé Suspect (le modèle s'appuie fortement sur sttl).
Cas isolé, non représentatif du taux global de fausses alertes (25,8 % à 0,5).

## Déclencheur S3 (US-11)
Un upload de `raw/UNSW_NB15_training-set.csv` régénère `processed/` automatiquement.
Limite : la Lambda lit des noms de fichiers fixes, donc valable pour ce dataset uniquement.

## Logs CloudWatch (US-15)
Groupes : `/aws/lambda/ctds-preprocessing`, `/aws/lambda/ctds-inference`,
`/aws/sagemaker/TrainingJobs`, `/aws/sagemaker/Endpoints/ctds-endpoint`.
Erreurs réelles retrouvées : ImportModuleError, Task timed out, ValidationError (endpoint absent).
Erreur volontaire (`{"sttl": "abc"}`) : <à compléter au test de bout en bout, US-18>.

## Pipeline SageMaker (US-16, US-17)
Étapes : Preprocess → Train → Evaluate → CheckQuality → RegisterModel.
Paramètres externalisés : `InputData`, `MinF1` (0,89), `MinAUC` (0,95).
Sorties écrites sous `s3://.../pipeline/`, sans toucher à `processed/` ni `models/`.

Reproductibilité (Preprocess + Train, première exécution) :
- AUC de validation 0,99365, identique à l'entraînement manuel ;
- modèle de 218,1 Ko dans les deux cas ;
- 245 s facturées (environ 0,003 $).

Seuil `MinF1 = 0,89` : choisi après avoir vu le F1 du test (0,8966). Un seuil à 0,90 rejetterait le modèle ;
l'écart de 0,003 est expliqué par la différence de distribution entre train et test.

Exécution complète : <à compléter : statut des 5 étapes, version 2 du registre, evaluation.json>.
Test de rejet (`MinF1 = 0,95`) : <à compléter : aucune nouvelle version attendue>.
Exécution complète (MinF1 = 0,89) : Preprocess, Train, Evaluate, CheckQuality, RegisterModel en Succeeded
après correction d'une permission manquante. Version 2 `Approved` dans le registre.
evaluation.json identique à l'évaluation manuelle : AUC 0,9837, F1 0,8966, recall 0,9839,
precision 0,8236, matrice TN 27 449 · FP 9 551 · FN 732 · TP 44 600.

Incident : RegisterModel a échoué (AccessDenied sur sagemaker:CreateModelPackageGroup).
La policy du pipeline était incomplète ; l'action a été ajoutée et l'exécution reprise avec
`retry-pipeline-execution`, sans refaire le prétraitement ni l'entraînement.

Test de rejet (MinF1 = 0,95) : <à compléter : CheckQuality sans RegisterModel, pas de version 3>.