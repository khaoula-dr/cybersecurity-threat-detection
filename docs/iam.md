# Rôles IAM (moindre privilège)

Région : eu-north-1 · Compte : 174797531196 · Bucket : `cybersecurity-threat-detection-174797531196`

Note : le projet est piloté avec le compte root (protégé par MFA), car IAM Identity Center
n'est pas disponible sur le plan gratuit et l'accès console n'a pas pu être activé pour
un utilisateur IAM. Aucune clé d'accès root n'est créée ; le code utilise des rôles de service.

## ctds-lambda-role

Utilisé par : la Lambda de prétraitement (US-08, US-11).
Relation de confiance : `lambda.amazonaws.com`.

| Permission | Ressource | Raison |
| --- | --- | --- |
| `s3:GetObject` | `bucket/raw/*` | Lire les logs bruts |
| `s3:PutObject` | `bucket/processed/*` | Écrire train, validation, test, columns.json |
| `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` | log groups `/aws/lambda/ctds-*` | Écrire les logs dans CloudWatch |

Écriture interdite dans `raw/` : évite une boucle infinie du déclencheur S3 (US-11).

## ctds-sagemaker-role

Utilisé par : training jobs, Model Registry, endpoint (US-09 à US-17).
Relation de confiance : `sagemaker.amazonaws.com`.

| Permission | Ressource | Raison |
| --- | --- | --- |
| `s3:ListBucket`, `s3:GetBucketLocation` | le bucket | Lister et localiser les données |
| `s3:GetObject`, `s3:PutObject` | `bucket/*` | Lire les données, écrire model.tar.gz et les métriques |
| `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogStreams` | `/aws/sagemaker/*` | Logs des jobs et de l'endpoint |
| `cloudwatch:PutMetricData` | `*` | Publier les métriques (action sans restriction possible) |
| `ecr:GetAuthorizationToken` | `*` | Se connecter à ECR (action sans restriction possible) |
| `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchCheckLayerAvailability` | `*` | Récupérer l'image du conteneur XGBoost intégré |

## Vérifications

- Aucune policy avec `Action: *` sur `Resource: *`.
- Rôles testés lors des premiers appels (US-08 pour Lambda, US-09 pour SageMaker).
- Évolution : toute permission ajoutée plus tard sera notée ici avec la date et l'erreur `AccessDenied` qui la justifie.