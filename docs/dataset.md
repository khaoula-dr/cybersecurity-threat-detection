# Dataset - UNSW-NB15

## Choix du dataset

Le projet utilise le dataset UNSW-NB15 pour entraîner un système
de détection des menaces réseau.

UNSW-NB15 a été choisi car il constitue un compromis entre réalisme,
taille des données et facilité d'utilisation dans une architecture AWS.

## Fichiers utilisés

- UNSW_NB15_training-set.csv
- UNSW_NB15_testing-set.csv

## Variable cible

La colonne `label` est utilisée comme variable cible :

- 0 : trafic normal
- 1 : trafic malveillant

La colonne `attack_cat` décrit le type d'attaque et ne sera pas utilisée
comme variable d'entrée du modèle afin d'éviter une fuite de données.

## Features

Les principales caractéristiques comprennent notamment :

- `dur`
- `proto`
- `service`
- `state`
- `sbytes`
- `dbytes`

Les features seront analysées et transformées lors de l'étape
de prétraitement.

## Utilisation dans le projet

Le dataset sera utilisé pour :

1. analyser les données ;
2. effectuer le prétraitement ;
3. entraîner le modèle XGBoost ;
4. évaluer les performances ;
5. déployer le modèle sur Amazon SageMaker.

## Licence et source

La licence et les conditions d'utilisation du dataset seront vérifiées
et documentées à partir de la source officielle avant son utilisation
dans le projet.
