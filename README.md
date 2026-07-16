# SpiderSilk DevOps Case Study

A small CSV-processing web app plus the infrastructure to run it: a kops
cluster config with mixed spot/on-demand instance groups and cluster
autoscaling, a Helm chart that runs Nginx and the app in one pod sharing
static assets through an `emptyDir` (no NFS), an HPA, Ansible-managed app
config, and an S3 bucket with a Glacier lifecycle rule.

See [`docs/architecture.md`](docs/architecture.md) for the full write-up and
architecture diagram.

## Requirements

Nothing here needs everything installed at once — pick the row(s) that match
what you're trying to run. Versions are what this repo was built/tested
against; other recent versions should work fine.

| Tool | Needed for | Tested with |
|---|---|---|
| [git](https://git-scm.com/) | cloning/working with the repo | 2.50 |
| [Python 3.12+](https://www.python.org/) | running the app locally, unit tests | 3.12 |
| [Docker](https://docs.docker.com/get-docker/) | building/running the app image | 29 |
| [Docker Hub](https://hub.docker.com/) account | `scripts/build-and-push.sh` | — |
| [Minikube](https://minikube.sigs.k8s.io/) | running the full stack locally on Kubernetes | 1.33+ |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | talking to Minikube / any cluster | 1.29+ |
| [Helm](https://helm.sh/) 3 | rendering/installing `infra/helm/spidersilk-app` | v4 (Helm 3.x chart syntax) |
| [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/index.html) (`ansible-core`) | rendering app config, `infra/ansible/` | 2.21 |
| [Terraform](https://developer.hashicorp.com/terraform/install) 1.5+ | provisioning the S3 bucket, `infra/s3/` | 1.15 |
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) + credentials (`aws configure`) | S3 CLI fallback, kops state store, IAM | 2.x |
| [kops](https://kops.sigs.k8s.io/getting_started/install/) | actually standing up `infra/kops/` on AWS | 1.29+ |

None of `kops`, `terraform apply`, or a live AWS account are required just to
read/validate the infra code — see the per-directory READMEs
(`infra/kops/README.md`, `infra/s3/README.md`) for what was hand-verified
without them.

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
