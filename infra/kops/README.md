# kops cluster — spidersilk.k8s.local

Config-only, per the case study brief. Valid `kops` input set; nothing here
has been applied.

## Layout

| File | Purpose |
|---|---|
| `cluster.yaml` | Cluster resource — AWS, 3 AZs (`eu-west-1a/b/c`), Calico, gossip DNS (`.k8s.local`) |
| `ig-master.yaml` | Control-plane IG — single on-demand `t3.medium` |
| `ig-nodes-ondemand.yaml` | Worker IG — `mixedInstancesPolicy` across `t3.medium`/`t3a.medium`/`t3.large`, 100% on-demand, min 2 / max 6 |
| `ig-nodes-spot.yaml` | Worker IG — same instance mix, 100% spot, `capacity-optimized`, min 0 / max 10, tainted `node-lifecycle=spot:PreferNoSchedule` |
| `cluster-autoscaler.yaml` | Cluster Autoscaler Deployment + RBAC, AWS ASG auto-discovery |
| `iam/cluster-autoscaler-policy.json` | Least-privilege IAM policy for the autoscaler |

Both worker IGs carry the same `cloudLabels`:

```
k8s.io/cluster-autoscaler/enabled: "true"
k8s.io/cluster-autoscaler/spidersilk.k8s.local: owned
```

kops propagates these onto the ASG, so Cluster Autoscaler's
`--node-group-auto-discovery` picks up every worker IG automatically — no
per-ASG config needed.

## SSH (22) / API (443) access

Open to `0.0.0.0/0` for testing. Scope down in `cluster.yaml` for production.

## Bring-up

```bash
# 1. State store
aws s3api create-bucket --bucket spidersilk-app-kops-state-store \
  --region eu-west-1 --create-bucket-configuration LocationConstraint=eu-west-1
export KOPS_STATE_STORE=s3://spidersilk-app-kops-state-store

# 2. Register cluster + instance groups
kops create -f cluster.yaml
kops create -f ig-master.yaml
kops create -f ig-nodes-ondemand.yaml
kops create -f ig-nodes-spot.yaml

# 3. SSH key
kops create secret --name spidersilk.k8s.local sshpublickey admin -i ~/.ssh/id_rsa.pub

# 4. Build it
kops update cluster --name spidersilk.k8s.local --yes
kops validate cluster --wait 10m
kops export kubeconfig spidersilk.k8s.local --admin
kubectl get nodes

# 5. Autoscaler (attach the IAM policy to the node instance profile first)
kubectl apply -f cluster-autoscaler.yaml

# Later: roll out a config change
kops edit ig nodes-spot
kops update cluster --yes
kops rolling-update cluster --yes
```

Replace `spidersilk-app-*` placeholders (`configBase`, IAM policy) before use.

## Teardown

```bash
export KOPS_STATE_STORE=s3://spidersilk-app-kops-state-store
kops delete cluster --name spidersilk.k8s.local --yes
```

Deletes ASGs, instances, NLB, VPC, security groups, and IAM roles in one
pass — don't delete individual InstanceGroups first (`kops delete -f` on a
lone master IG fails with "cannot delete the only control plane instance
group" anyway). Doesn't delete the state-store bucket itself:

```bash
aws s3 rm s3://spidersilk-app-kops-state-store/spidersilk.k8s.local --recursive
aws s3api delete-bucket --bucket spidersilk-app-kops-state-store --region eu-west-1
```

## Troubleshooting

**`kubectl get nodes` prompts "Please enter Username:"** — no kubeconfig
credentials yet (kops doesn't use basic auth). Run
`kops export kubeconfig spidersilk.k8s.local --admin`.

**Pods crash-looping with `exec format error`** — CPU architecture mismatch.
Worker nodes are `amd64`; a plain `docker build` on Apple Silicon only
targets `arm64`. Use `scripts/build-and-push.sh` (builds multi-arch via
`buildx`) instead of a manual `docker build`/`push`.
