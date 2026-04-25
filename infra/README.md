# Infrastructure - Trash Classification

Terraform + Terragrunt infrastructure cho Trash Classification System trên AWS ECS Fargate.

## Cấu trúc

```
infra/aws/
├── root.hcl                          # Terragrunt root config (provider, backend)
├── global.hcl                        # Project-level variables
│
├── 4_deployments/                    # CI/CD resources
│   ├── __modules__/                  # Terraform modules
│   │   ├── ecr/                      # ECR repository
│   │   ├── kms/                      # KMS encryption key
│   │   ├── artifacts/                # S3 artifact bucket
│   │   ├── codebuild/                # CodeBuild project
│   │   ├── codepipeline/             # CodePipeline base
│   │   └── codepipeline_deploy_ecs/  # Pipeline: Source -> Build Docker -> Deploy ECS
│   ├── __templates__/
│   │   └── push_image.yml            # Buildspec: build & push Docker image to ECR
│   └── main/ap-southeast-1/          # Terragrunt configs
│       ├── ecr/
│       ├── kms/
│       ├── artifacts/
│       └── pipeline/
│
└── 5_workloads/                      # Application resources
    ├── __modules__/
    │   ├── vpc/                      # VPC with public/private subnets
    │   └── ecs/
    │       ├── cluster/              # ECS Cluster + ALB
    │       └── service/              # ECS Fargate Service + Task Definition
    ├── __shared__/                   # Shared terragrunt configs
    │   ├── vpc.hcl
    │   ├── ecs_cluster.hcl
    │   └── ecs_service.hcl
    └── ap-southeast-1/prod/          # Environment
        ├── vpc/
        └── ecs/
            ├── cluster/
            └── service/
```

## Trước khi bắt đầu

1. Thay `REPLACE_WITH_YOUR_AWS_ACCOUNT_ID` trong các file:
   - `aws/global.hcl`
   - `aws/5_workloads/ap-southeast-1/prod/account.hcl`
   - `aws/4_deployments/main/account.hcl`

2. Tạo CodeStar Connection trong AWS Console (Settings > Connections) và cập nhật ARN vào
   `aws/4_deployments/main/ap-southeast-1/pipeline/terragrunt.hcl`

3. Cập nhật GitHub owner/repo trong file pipeline trên.

4. Cấu hình AWS CLI profile `trash-classification`:
   ```bash
   aws configure --profile trash-classification
   ```

## Deploy theo thứ tự

```bash
# 1. VPC
cd infra/aws/5_workloads/ap-southeast-1/prod/vpc
terragrunt apply

# 2. ECS Cluster + ALB
cd ../ecs/cluster
terragrunt apply

# 3. ECR Repository
cd ../../../../4_deployments/main/ap-southeast-1/ecr
terragrunt apply

# 4. Build & push Docker image lần đầu (local)
# Chạy ở root project (nơi có Dockerfile + model files)
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com
docker build -t trash-classification .
docker tag trash-classification:latest <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/trash-classification:latest
docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/trash-classification:latest

# 5. ECS Service
cd ../../../../5_workloads/ap-southeast-1/prod/ecs/service
terragrunt apply

# 6. CI/CD Pipeline (KMS -> Artifacts -> Pipeline)
cd ../../../../../4_deployments/main/ap-southeast-1/kms
terragrunt apply
cd ../artifacts
terragrunt apply
cd ../pipeline
terragrunt apply
```

## CI/CD Flow

```
Git push (main) -> CodePipeline -> CodeBuild (docker build + push ECR) -> ECS Deploy
```

Model files (`model_trash/best.pt`, `model_liquid/best.pt`) được đóng gói trong Docker image,
không push lên Git.
