# Rôles IAM (moindre privilège)

Région : eu-north-1 · Compte : 174797531196 · Bucket : `cybersecurity-threat-detection-174797531196`

Le projet est piloté avec le compte root (protégé par MFA), car IAM Identity Center n'est pas disponible sur le plan gratuit
et l'accès console n'a pas pu être activé pour un utilisateur IAM. Aucune clé d'accès root n'est créée : le code s'exécute avec des rôles de service.

## ctds-lambda-role

Utilisé par : les Lambdas `ctds-preprocessing` (US-08, US-11) et `ctds-inference` (US-13, US-14).
Relation de confiance : `lambda.amazonaws.com`.

### Policy `ctds-lambda-policy` (prétraitement)

| Permission | Ressource | Raison |
| --- | --- | --- |
| `s3:GetObject` | `bucket/raw/*` | Lire les logs bruts |
| `s3:PutObject` | `bucket/processed/*` | Écrire train, validation, test, columns.json |
| `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` | log groups `/aws/lambda/ctds-*` | Écrire les logs dans CloudWatch |

Écriture interdite dans `raw/` : évite une boucle infinie du déclencheur S3.

### Policy `ctds-lambda-inference-policy` (inférence, ajoutée le 2026-10-08)

| Permission | Ressource | Raison |
| --- | --- | --- |
| `s3:GetObject` | `bucket/processed/*` | Lire `columns.json` et `defaults.json` |
| `sagemaker:InvokeEndpoint` | endpoint `ctds-endpoint` | Obtenir la probabilité de l'endpoint |

### Déclencheur S3 (US-11)

`lambda:InvokeFunction` accordée à `s3.amazonaws.com` sur `ctds-preprocessing`, limitée au bucket du projet et au compte 174797531196.
Filtre : préfixe `raw/`, suffixe `training-set.csv`. Le rôle ne peut pas écrire dans `raw/` : pas de boucle.

## ctds-sagemaker-role

Utilisé par : training jobs, jobs de traitement, pipeline, Model Registry, endpoint (US-09 à US-17).
Relation de confiance : `sagemaker.amazonaws.com`.

### Policy `ctds-sagemaker-policy` (entraînement et endpoint)

| Permission | Ressource | Raison |
| --- | --- | --- |
| `s3:ListBucket`, `s3:GetBucketLocation` | le bucket | Lister et localiser les données |
| `s3:GetObject`, `s3:PutObject` | `bucket/*` | Lire les données, écrire model.tar.gz et les métriques |
| `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogStreams` | `/aws/sagemaker/*` | Logs des jobs et de l'endpoint |
| `cloudwatch:PutMetricData` | `*` | Publier les métriques (action sans restriction de ressource possible) |
| `ecr:GetAuthorizationToken` | `*` | Se connecter à ECR (action sans restriction de ressource possible) |
| `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchCheckLayerAvailability` | `*` | Récupérer l'image du conteneur XGBoost intégré |

### Policy `ctds-sagemaker-pipeline-policy` (US-16, US-17)

Ressource des actions SageMaker : `arn:aws:sagemaker:eu-north-1:174797531196:*`.

| Permission | Raison |
| --- | --- |
| `CreateProcessingJob`, `DescribeProcessingJob`, `StopProcessingJob` | Étapes Preprocess et Evaluate |
| `CreateTrainingJob`, `DescribeTrainingJob`, `StopTrainingJob` | Étape Train |
| `AddTags`, `ListTags` | Étiquetage des jobs par le pipeline |
| `CreateModelPackage`, `DescribeModelPackage` | Étape RegisterModel |
| `CreateModelPackageGroup`, `DescribeModelPackageGroup` | Étape RegisterModel (voir incident ci-dessous) |
| `iam:PassRole` sur `ctds-sagemaker-role` uniquement | Le pipeline passe son propre rôle aux jobs. Condition : `iam:PassedToService = sagemaker.amazonaws.com` |

## Journal des évolutions

| Date | Changement | Justification |
| --- | --- | --- |
| 2026-10-08 | Ajout de `ctds-lambda-inference-policy` | Inférence : lecture de la spec et appel de l'endpoint |
| 2026-10-08 | Autorisation S3 → `ctds-preprocessing` | Déclenchement automatique (US-11) |
| 10/2026 | Ajout de `ctds-sagemaker-pipeline-policy` | Créer et suivre les jobs du pipeline, enregistrer un modèle |
| 10/2026 | Ajout de `sagemaker:CreateModelPackageGroup` | Erreur `AccessDenied` sur l'étape RegisterModel : la policy initiale était incomplète. Corrigée, exécution reprise avec `retry-pipeline-execution` |

Principe appliqué : une permission n'est élargie que lorsqu'une erreur `AccessDenied` le justifie.

## Vérifications

- Aucune policy avec `Action: *` sur `Resource: *`.
- Les `Resource: *` restantes concernent des actions qui n'acceptent pas de restriction de ressource (`PutMetricData`, `GetAuthorizationToken`) et la lecture d'images ECR.
- Rôles testés en conditions réelles : Lambda de prétraitement (US-08), training job (US-09), Lambda d'inférence et endpoint (US-13, US-14, US-18), pipeline (US-16, US-17).

## Écarts documentés

- Compte root utilisé pour le pilotage (MFA actif), faute d'utilisateur IAM avec accès console sur le plan gratuit.
- Pas d'alerte budget configurable sur le plan gratuit : suivi manuel dans Cost Explorer, plafond de 100 $ de crédits.
- Stretch non réalisé : chiffrement KMS et CloudTrail (US-25). Le bucket utilise le chiffrement SSE-S3 (AES256), le versioning et le blocage de l'accès public.