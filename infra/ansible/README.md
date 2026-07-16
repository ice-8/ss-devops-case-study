# Ansible — application configuration management

The app runs in Kubernetes, so Ansible isn't managing VMs here — it plays the
role the brief asks for literally: **application config lives in Ansible**
(`group_vars/*.yml`), and gets rendered into the Helm values fragment that
`infra/helm/spidersilk-app` consumes. This keeps one chart reusable across
environments (per the "use Helm to render K8s objects for re-using while
creating new environments" requirement) while Ansible owns *what* each
environment's config actually is.

```
inventory/hosts.ini            environment groups (minikube, production)
group_vars/all.yml             shared defaults
group_vars/minikube.yml        minikube overrides (no S3 bucket, debug logging)
group_vars/production.yml      production overrides (real S3 bucket, replica counts)
roles/app_config/              renders + optionally applies the config
playbook.yml                   entrypoint
```

## Run it

```bash
cd infra/ansible

# Render config only (safe, no cluster access needed):
ansible-playbook -i inventory/hosts.ini playbook.yml -l minikube

# -> writes infra/helm/spidersilk-app/generated/minikube-app-config.yaml

# Render AND deploy with Helm in one step:
ansible-playbook -i inventory/hosts.ini playbook.yml -l production -e deploy_with_helm=true
```

The generated file is a small Helm values fragment:

```yaml
appConfig:
  s3Bucket: "CHANGEME-spidersilk-processed-files"
  s3Prefix: "processed/"
  awsRegion: "us-east-1"
  maxUploadMb: "10"
  logLevel: "INFO"
autoscaling:
  minReplicas: 2
  maxReplicas: 8
```

which is applied on top of the chart's own `values.yaml`:

```bash
helm upgrade --install spidersilk infra/helm/spidersilk-app \
  -f infra/helm/spidersilk-app/values.yaml \
  -f infra/helm/spidersilk-app/generated/production-app-config.yaml
```

## Adding a new environment

1. Add a group to `inventory/hosts.ini`.
2. Add `group_vars/<env>.yml` with at least `app_s3_bucket`,
   `app_min_replicas`, `app_max_replicas`, `helm_values_file`,
   `helm_release_name`.
3. `ansible-playbook -i inventory/hosts.ini playbook.yml -l <env>`.

No changes to the Helm chart or the app itself are needed — that's the reuse
this split is buying.
