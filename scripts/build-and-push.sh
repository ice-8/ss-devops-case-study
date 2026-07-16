#!/usr/bin/env bash
# Builds the SpiderSilk app image and pushes it to Docker Hub.
#
# Usage:
#   DOCKERHUB_USER=myuser ./scripts/build-and-push.sh [tag]
#
# Requires: docker login (run once beforehand).
set -euo pipefail

TAG="${1:-latest}"
: "${DOCKERHUB_USER:?Set DOCKERHUB_USER, e.g. DOCKERHUB_USER=myuser $0}"

IMAGE="${DOCKERHUB_USER}/spidersilk-app:${TAG}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Building ${IMAGE}"
docker build -t "${IMAGE}" "${ROOT_DIR}/app"

echo "==> Pushing ${IMAGE}"
docker push "${IMAGE}"

echo "==> Done. Reference this image in infra/helm/spidersilk-app/values.yaml:"
echo "    image.repository: ${DOCKERHUB_USER}/spidersilk-app"
echo "    image.tag: ${TAG}"
