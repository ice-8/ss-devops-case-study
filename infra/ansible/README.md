# Ansible — application configuration management

App config lives in Ansible (`group_vars/*.yml`), rendered into a Helm
values fragment consumed by `infra/helm/spidersilk-app`. One chart, many
environments; Ansible owns what each environment's config is.

```
inventory/hosts.ini            environment groups (minikube, production)
group_vars/all.yml             shared defaults
group_vars/minikube.yml        minikube overrides
group_vars/production.yml      production overrides
roles/app_config/              renders + optionally applies the config
playbook.yml                   entrypoint
```

## Run it

```bash
cd infra/ansible

# Render config only (safe, no cluster access needed):
ansible-playbook -i inventory/hosts.ini playbook.yml -l minikube
# -> writes infra/helm/spidersilk-app/generated/minikube-app-config.yaml

# Render AND deploy with Helm:
ansible-playbook -i inventory/hosts.ini playbook.yml -l production -e deploy_with_helm=true
```

Generated file:

```yaml
appConfig:
  s3Bucket: "spidersilk-app-spidersilk-processed-files"
  s3Prefix: "processed/"
  awsRegion: "eu-west-1"
  maxUploadMb: "10"
  logLevel: "INFO"
autoscaling:
  minReplicas: 2
  maxReplicas: 8
```

Applied on top of the chart's own `values.yaml`:

```bash
helm upgrade --install spidersilk infra/helm/spidersilk-app \
  -f infra/helm/spidersilk-app/values.yaml \
  -f infra/helm/spidersilk-app/generated/production-app-config.yaml
```

## Adding an environment

1. Add a group to `inventory/hosts.ini`.
2. Add `group_vars/<env>.yml` with `app_s3_bucket`, `app_min_replicas`,
   `app_max_replicas`, `helm_values_file`, `helm_release_name`.
3. `ansible-playbook -i inventory/hosts.ini playbook.yml -l <env>`.

No chart or app changes needed.
