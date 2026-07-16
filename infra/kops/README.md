# kops cluster — spidersilk.k8s.local

Config-only, as noted in the case study brief ("not expecting to have running
cluster"). This directory is a valid `kops` input set; nothing here has been
applied.

## Layout

| File | Purpose |
|---|---|
| `cluster.yaml` | Cluster resource — AWS, 3 AZs (`eu-west-1a/b/c`), Calico networking, gossip DNS (`.k8s.local`, no real domain needed) |
| `ig-master.yaml` | Control-plane instance group — single on-demand `t3.medium` |
| `ig-nodes-ondemand.yaml` | Worker instance group — `mixedInstancesPolicy` across `t3.medium`/`t3a.medium`/`t3.large`, 100% on-demand, min 2 / max 6 |
| `ig-nodes-spot.yaml` | Worker instance group — same instance-type mix, 100% spot (`onDemandBase: 0`), `capacity-optimized` allocation, min 0 / max 10, tainted `node-lifecycle=spot:PreferNoSchedule` so workloads must opt in |
| `cluster-autoscaler.yaml` | Cluster Autoscaler Deployment + RBAC, AWS ASG auto-discovery |
| `iam/cluster-autoscaler-policy.json` | Least-privilege IAM policy for the autoscaler, scoped by the `k8s.io/cluster-autoscaler/spidersilk.k8s.local=owned` tag |

Both worker instance groups carry the same two `cloudLabels`:

```
k8s.io/cluster-autoscaler/enabled: "true"
k8s.io/cluster-autoscaler/spidersilk.k8s.local: owned
```

kops propagates `cloudLabels` onto the underlying ASG, so Cluster
Autoscaler's `--node-group-auto-discovery=asg:tag=...` flag picks up *every*
worker instance group automatically — new instance groups only need the same
two tags to be covered, no autoscaler redeploy required.


## SSH (22) / API (443) access

For testing purposes access to nodes port 22 and 443 is allowed from `0.0.0.0/0`.

Set it to appropriate value for any production setup or other security requiremtns in `cluster.yaml`.

## Bring-up walkthrough (not executed here)

```bash
# 1. One-time: an S3 bucket to hold kops cluster state
aws s3api create-bucket --bucket spidersilk-app-kops-state-store \
--region eu-west-1 \
--create-bucket-configuration LocationConstraint=eu-west-1
export KOPS_STATE_STORE=s3://spidersilk-app-kops-state-store

# 2. Register the cluster + instance groups
kops create -f cluster.yaml
kops create -f ig-master.yaml
kops create -f ig-nodes-ondemand.yaml
kops create -f ig-nodes-spot.yaml

# 3. SSH key for the nodes
kops create secret --name spidersilk.k8s.local sshpublickey admin -i ~/.ssh/id_rsa.pub

# 4. Validate the config, then build the AWS resources
kops update cluster --name spidersilk.k8s.local
kops update cluster --name spidersilk.k8s.local --yes
kops validate cluster --wait 10m
kops export kubeconfig spidersilk.k8s.local --admin
kubectl get nodes

# 5. Attach the autoscaler IAM policy to the node instance profile, then:
kubectl apply -f cluster-autoscaler.yaml

# Later, roll out a config change (e.g. edit an IG):
kops edit ig nodes-spot
kops update cluster --yes
kops rolling-update cluster --yes
```

`cluster.yaml` uses `configBase: s3://spidersilk-app-kops-state-store/...` and the
IAM policy references the literal cluster name — replace `spidersilk-app-*`
placeholders before use.

## Pod containers crash-looping with "exec format error"

CPU architecture mismatch, not a kops issue. The worker instance types
(`t3.medium`, `t3a.medium`, `t3.large`) are all `amd64` — a `spidersilk-app`
image built with a plain `docker build` on an Apple Silicon (`arm64`)
machine only targets the host architecture, so it runs fine locally but
fails on these nodes with `exec /usr/bin/sh: exec format error`.

Build/push a multi-arch image instead — `scripts/build-and-push.sh` already
does this via `docker buildx`:

```bash
DOCKERHUB_USER=youruser ./scripts/build-and-push.sh v1
```

which builds and pushes `linux/amd64,linux/arm64` in one go (override with
`PLATFORMS=...` if you only need one).
