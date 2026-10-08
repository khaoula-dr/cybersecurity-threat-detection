## Entraînement (US-09)
- Job : sagemaker-xgboost-2026-10-08-10-10-11-366 (ml.m5.large, XGBoost 1.7-1)
- Durée facturée : 244 s (~0,003 $)
- AUC validation : 0,9937 · AUC train : 0,9956
## Évaluation sur le test officiel (US-10), seuil 0,5
AUC 0,984 · F1 0,897 · Recall 0,984 · Precision 0,824 · Accuracy 0,875
Matrice : TN 27 449 · FP 9 551 · FN 732 · TP 44 600
Écart : F1 à 0,003 de l'objectif de 0,90. Cause : 25,8 % de fausses alertes,
liées à la différence de distribution entre train et test (attaques 68 % contre 55 %).