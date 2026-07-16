#!/usr/bin/env bash
# Builds (multi-arch, via buildx) and pushes the app image to Docker Hub.
# Usage: DOCKERHUB_USER=myuser ./scripts/build-and-push.sh [tag]
# Requires: docker login. See infra/kops/README.md Troubleshooting for why
# multi-arch matters here.
set -euo pipefail

TAG="${1:-latest}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
: "${DOCKERHUB_USER:?Set DOCKERHUB_USER, e.g. DOCKERHUB_USER=myuser $0}"

IMAGE="${DOCKERHUB_USER}/spidersilk-app:${TAG}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is required (ships with recent Docker Desktop / docker-buildx-plugin)." >&2
  exit 1
fi
docker buildx inspect spidersilk-builder >/dev/null 2>&1 || \
  docker buildx create --name spidersilk-builder --use >/dev/null
docker buildx use spidersilk-builder

echo "==> Building and pushing ${IMAGE} for ${PLATFORMS}"
docker buildx build --platform "${PLATFORMS}" -t "${IMAGE}" --push "${ROOT_DIR}/app"

echo "==> Done. Reference this image in infra/helm/spidersilk-app/values.yaml:"
echo "    image.repository: ${DOCKERHUB_USER}/spidersilk-app"
echo "    image.tag: ${TAG}"
