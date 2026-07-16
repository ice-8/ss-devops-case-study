# SpiderSilk DevOps Case Study

CSV-processing web app + infra: kops cluster (spot/on-demand IGs, autoscaled),
Helm-deployed nginx+app pod with shared `emptyDir` static files, HPA, Ansible
config management, S3 with Glacier lifecycle.

See [`docs/architecture.md`](docs/architecture.md) for diagram + full write-up.

## Requirements

- git 2.50+
- Python 3.12+
- Docker 24+ (with `buildx`)
- Minikube 1.33+ / kubectl 1.35+
- Helm 3+
- Ansible (`ansible-core`) 2.21+
- Terraform 1.5+
- AWS CLI v2
- kops 1.35+

Only needed for the parts you're actually running — none of `kops`,
`terraform apply`, or AWS credentials are required to read/validate the code.

## Repo map

```
app/            Flask app — upload/parse CSV, history, push to S3
infra/kops/     kops Cluster + InstanceGroup config (multi-IG, spot+on-demand, autoscaler)
infra/helm/     Helm chart: nginx+app pod, Service, HPA
infra/ansible/  App config management, rendered into Helm values
infra/s3/       Terraform (+ CLI fallback) for the S3 bucket & Glacier rule
scripts/        Docker build/push helper
docs/           Architecture doc + diagram
task/           Original case study brief + sample CSV
```

## Run locally (no Kubernetes)

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
export DB_PATH="./data/history.db" UPLOAD_DIR="./data/uploads"
python app.py                 # http://127.0.0.1:5000
```

Or with Docker:

```bash
docker build -t spidersilk-app:local app/
docker run --rm -p 5000:5000 spidersilk-app:local
```

Upload `task/soh-1-.csv` — no `S3_BUCKET` set locally means the upload step
shows "skipped: S3_BUCKET not configured" instead of failing.

## Deploy to Minikube

```bash
minikube start
eval $(minikube docker-env)
docker build -t spidersilk-app:local app/

helm install spidersilk infra/helm/spidersilk-app \
  -f infra/helm/spidersilk-app/values.yaml \
  -f infra/helm/spidersilk-app/values-minikube.yaml

minikube service spidersilk --url
```

App config (S3 bucket, replicas, log level) is managed via Ansible — see
[`infra/ansible/README.md`](infra/ansible/README.md).

## Publish image to Docker Hub

```bash
docker login
DOCKERHUB_USER=youruser ./scripts/build-and-push.sh v1
```

Builds multi-arch (amd64+arm64) via buildx. Set
`image.app.repository`/`image.app.tag` in `values.yaml` to match.

## kops cluster

Config-only in this repo — see [`infra/kops/README.md`](infra/kops/README.md)
for bring-up, teardown, and troubleshooting.

## S3 + Glacier

Not applied in this repo — see [`infra/s3/README.md`](infra/s3/README.md)
for `terraform apply` / `aws-cli` instructions and the app's IAM policy.

## Notes

- App: Python 3.12 / Flask, `boto3`, SQLite for history, `gunicorn`.
- CSV format: unheadered `"sku","description","price"` (see `task/soh-1-.csv`).
- Validated locally: `helm lint`/`template`, `terraform validate`, a real
  `ansible-playbook` run. `kops` itself wasn't run, per the brief.
