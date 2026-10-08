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