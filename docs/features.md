# Features, cible et découpage (US-07)

Dataset : UNSW-NB15 (versions officielles training-set et testing-set).
Les transformations sont implémentées dans `lambda/preprocessing.py`.

## Cible
- `label` : 0 = normal, 1 = attaque.
- `attack_cat` (type d'attaque) n'est pas utilisée comme feature : elle décrit la cible (fuite).

## Features (63)

| Groupe | Nombre | Détail |
| --- | --- | --- |
| Numériques | 36 | Toutes les colonnes numériques sauf celles exclues ci-dessous |
| `proto` | 6 | One-hot des 5 protocoles les plus fréquents du train + `other` |
| `service` | 13 | One-hot sur les valeurs vues dans le train |
| `state` | 8 | One-hot sur les valeurs vues dans le train |

Top 5 des protocoles : <à remplir avec la liste `protos` de `processed/columns.json`>.
L'ordre exact des colonnes est sauvegardé dans `processed/columns.json` et doit être
réutilisé à l'inférence.

## Colonnes exclues

| Colonne | Raison |
| --- | --- |
| `id` | Corrélation de 0,73 avec la cible : artefact de l'ordre du fichier, inutilisable en production |
| `attack_cat` | Fuite de la cible |
| `stcpb`, `dtcpb` | Numéros de séquence TCP, quasi aléatoires |
| `ct_ftp_cmd` | Même moyenne que `is_ftp_login`, information redondante |

Les adresses IP ne sont pas présentes dans cette version du dataset.

## Découpage

| Jeu | Lignes | Origine |
| --- | --- | --- |
| Train | 140 273 | 80 % du training-set, stratifié sur `label`, `random_state=42` |
| Validation | 35 068 | 20 % du training-set, stratifié sur `label` |
| Test | 82 332 | testing-set officiel, conservé tel quel |

Le test officiel sert d'évaluation finale. Il est plus honnête qu'un nouveau découpage
d'un jeu fusionné, mais sa distribution diffère du train (voir plus bas).

## Absence de fuite
- Le découpage train / validation est fait avant l'apprentissage des catégories.
- Les catégories (`proto`, `service`, `state`) sont apprises sur le train uniquement.
- Une valeur inconnue (ex. `ACC` et `CLO` dans `state`, présentes seulement dans le test)
  donne des zéros sur toutes ses colonnes.
- Test unitaire : `tests/test_preprocessing.py` (colonnes alignées, catégorie inconnue,
  découpage stratifié et disjoint).

## Déséquilibre des classes

| Jeu | Part d'attaques |
| --- | --- |
| Train (avant découpage) | 68,1 % |
| Test | 55,1 % |

Les attaques sont majoritaires, donc `scale_pos_weight` reste à 1 et aucun rééchantillonnage
n'est appliqué. Le suivi se fait avec F1, AUC et le recall sur la classe attaque.
Cette répartition est peu réaliste (sur un vrai réseau, les attaques sont rares) :
à mentionner dans les limites du rapport.

## Points de vigilance
- `sttl` (corrélation 0,69) et `ct_state_ttl` (0,58) dominent : risque que le modèle exploite
  des artefacts du banc d'essai. À vérifier avec l'importance des features après l'US-09.
- Les variables `ct_*` sont calculées sur des fenêtres de connexions : à l'inférence
  (US-14), elles doivent être fournies par l'appelant ou approximées.
- La distribution train / test diffère, donc une baisse de score sur le test est attendue.
- Format SageMaker : CSV sans en-tête, cible en première colonne.