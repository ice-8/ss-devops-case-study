# S3 storage + Glacier transition

## Option A — Terraform

```bash
cd infra/s3
terraform init
terraform apply -var="bucket_name=your-unique-bucket-name"
```

Private, versioned, SSE-encrypted bucket; lifecycle rule transitions
`processed/*` to **Glacier** after `glacier_transition_days` (default 30).

## Option B — AWS CLI fallback

```bash
aws s3api create-bucket --bucket your-unique-bucket-name --region eu-west-1
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-unique-bucket-name --lifecycle-configuration file://lifecycle.json
aws s3api put-public-access-block \
  --bucket your-unique-bucket-name --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Wiring it to the app

Permissions are granted via the kops **node instance profile**, not IRSA —
`infra/kops/cluster.yaml` has `spec.additionalPolicies.node` with the same
statements as `iam-app-policy.json`, attached to the shared node IAM role
both worker IGs use. To apply:

1. Replace `spidersilk-app-*` in both `iam-app-policy.json` and
   `cluster.yaml`'s `additionalPolicies.node` with your real bucket name
   (keep them in sync — `iam-app-policy.json` is the reference copy).
2. `kops update cluster --yes && kops rolling-update cluster --yes` to roll
   the policy onto the nodes.
3. Set `app_s3_bucket` in `infra/ansible/group_vars/production.yml`,
   re-render config, `helm upgrade`.

The app uploads under `processed/` — matches the lifecycle rule and IAM
policy scope above.

IRSA (`values.yaml` → `serviceAccount.annotations` →
`eks.amazonaws.com/role-arn`) is left as an optional upgrade path — it needs
an OIDC provider configured on the cluster, which this kops config doesn't
set up.
