#!/usr/bin/env bash
# Build the image, push it, apply the infrastructure, then migrate and seed.
# Extra arguments go to `terraform apply` (for example -auto-approve).
#
#   ./infra/deploy.sh
#
# Needs: aws (profile already selected), terraform, docker with buildx.
set -euo pipefail

cd "$(dirname "$0")"
region="us-east-1"

tag="$(git rev-parse --short=12 HEAD)"
if [ -n "$(git status --porcelain -- .. ':!infra')" ]; then
  # Uncommitted app changes get their own tag so they never pass for the commit.
  tag="${tag}-dirty-$(date +%Y%m%d%H%M%S)"
fi

terraform init -input=false

echo "==> ECR repository"
terraform apply -input=false -target=aws_ecr_repository.app "$@"
repository="$(terraform output -raw ecr_repository_url)"

echo "==> Image ${repository}:${tag}"
aws ecr get-login-password --region "${region}" |
  docker login --username AWS --password-stdin "${repository%%/*}"
# Lambda runs arm64 and rejects the attestation manifests buildx adds by default.
docker buildx build --platform linux/arm64 --provenance=false --sbom=false \
  --tag "${repository}:${tag}" --push ..

echo "==> Infrastructure"
terraform apply -input=false -var "image_tag=${tag}" "$@"

echo "==> Migrate and seed"
result="$(mktemp)"
trap 'rm -f "${result}"' EXIT
status="$(aws lambda invoke \
  --region "${region}" \
  --function-name "$(terraform output -raw ops_function_name)" \
  --cli-binary-format raw-in-base64-out \
  --cli-read-timeout 310 \
  --payload '{"task": "migrate-and-seed"}' \
  --query 'FunctionError' --output text \
  "${result}")"
cat "${result}"
echo
if [ "${status}" != "None" ] || ! grep -q '"migrated"' "${result}"; then
  echo "migrate-and-seed failed" >&2
  exit 1
fi

echo "==> Live at $(terraform output -raw site_url)"
