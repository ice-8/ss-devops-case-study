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
export RECORDS_DIR="./data/records" UPLOAD_DIR="./data/uploads"
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

## Deploy to production (kops)

Five steps, each detailed in its own README:

1. **Provision the cluster** — [`infra/kops/README.md`](infra/kops/README.md)
   (bring-up, teardown, troubleshooting).
2. **Create the S3 bucket + Glacier lifecycle** — [`infra/s3/README.md`](infra/s3/README.md)
   (`terraform apply` or the `aws-cli` fallback), then attach its IAM policy
   to the cluster per that README (kops node role via `additionalPolicies`).
3. **Build and push the app image**:
   ```bash
   docker login
   DOCKERHUB_USER=youruser ./scripts/build-and-push.sh v1
   ```
   Multi-arch (amd64+arm64) via buildx. Set `image.app.repository`/`image.app.tag`
   in `infra/helm/spidersilk-app/values.yaml` to match.
4. **Set the environment's app config** — bucket name, region, replica
   bounds — in `infra/ansible/group_vars/production.yml`.
5. **Render config and deploy** — [`infra/ansible/README.md`](infra/ansible/README.md):
   ```bash
   cd infra/ansible
   ansible-playbook -i inventory/hosts.ini playbook.yml -l production -e deploy_with_helm=true
   ```
   Renders `group_vars/production.yml` into a Helm values fragment and runs
   `helm upgrade --install` in one step — this is what actually deploys the
   Helm chart from step 3/4 onto the cluster from step 1.
