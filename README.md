# SpiderSilk DevOps Case Study

A small CSV-processing web app plus the infrastructure to run it: a kops
cluster config with mixed spot/on-demand instance groups and cluster
autoscaling, a Helm chart that runs Nginx and the app in one pod sharing
static assets through an `emptyDir` (no NFS), an HPA, Ansible-managed app
config, and an S3 bucket with a Glacier lifecycle rule.

See [`docs/architecture.md`](docs/architecture.md) for the full write-up and
architecture diagram.

## Repo map

```
app/            Flask web app — upload/parse CSV, view history, push to S3
infra/kops/     kops Cluster + InstanceGroup config (multi-IG, spot+on-demand,
                cluster autoscaler) — config only, not applied
infra/helm/     Helm chart: nginx+app pod, Service, HPA
infra/ansible/  App config management, rendered into Helm values
infra/s3/       Terraform (+ CLI fallback) for the S3 bucket & Glacier rule
scripts/        Docker build/push helper
docs/           Architecture doc + diagram
task/           Original case study brief + sample CSV
```

## Quickstart — run the app locally (no Kubernetes)

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                     # unit tests for the CSV parser
export DB_PATH="./data/history.db"
export UPLOAD_DIR="./data/uploads"
python app.py                 # http://127.0.0.1:5000
```

Or with Docker:

```bash
docker build -t spidersilk-app:local app/
docker run --rm -p 5000:5000 spidersilk-app:local
```

Upload `task/soh-1-.csv` at `http://127.0.0.1:5000/` — you'll see the parsed
rows and, since no `S3_BUCKET` is set, an S3 status of "skipped: S3_BUCKET
not configured" instead of a crash.

## Quickstart — deploy to Minikube

```bash
minikube start
eval $(minikube docker-env)                  # build straight into Minikube's Docker
docker build -t spidersilk-app:local app/

helm install spidersilk infra/helm/spidersilk-app \
  -f infra/helm/spidersilk-app/values.yaml \
  -f infra/helm/spidersilk-app/values-minikube.yaml

minikube service spidersilk --url            # opens/prints the app URL
```

To manage config the way the case study asks (Ansible as the source of
truth for app config, rendered into Helm values), see
[`infra/ansible/README.md`](infra/ansible/README.md) — it generates the
`-f` file above instead of you hand-editing it.

## Publish the app image to Docker Hub

```bash
docker login
DOCKERHUB_USER=youruser ./scripts/build-and-push.sh v1
```

Then set `image.app.repository`/`image.app.tag` in
`infra/helm/spidersilk-app/values.yaml` (or a `-f` override) to match.

## kops cluster

Config-only — see [`infra/kops/README.md`](infra/kops/README.md) for the
full `kops create` / `kops update` walkthrough. Three instance groups
(`master`, `nodes-ondemand`, `nodes-spot`) using kops' `mixedInstancesPolicy`
for instance-type diversification, plus a Cluster Autoscaler deployment that
auto-discovers and scales every worker instance group via shared AWS tags.

## S3 + Glacier

Not applied in this repo (no AWS credentials were available at build time)
— see [`infra/s3/README.md`](infra/s3/README.md) for `terraform apply` and
`aws-cli` instructions to stand it up, plus the IAM policy the app needs.

## Tech notes

- App: Python 3.12 / Flask, `boto3` for S3, SQLite for processed-file
  history, `gunicorn` in production.
- CSV format: unheadered `"sku","description","price"` rows (see
  `task/soh-1-.csv`).
- Everything under `infra/` was validated locally where tooling allowed:
  `helm lint`/`helm template`, `terraform validate`, and a real
  `ansible-playbook` run (see `infra/ansible/README.md`). `kops` itself
  wasn't run, per the brief's "not expecting to have running cluster."
