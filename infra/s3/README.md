# S3 storage + Glacier transition

Not applied in this environment — no AWS credentials were configured when
this repo was built (see main README). Everything here is ready to run
once you have an account.

## Option A — Terraform (recommended)

```bash
cd infra/s3
terraform init
terraform plan  -var="bucket_name=your-unique-bucket-name"
terraform apply -var="bucket_name=your-unique-bucket-name"
```

Creates a private, versioned, SSE-encrypted bucket with a lifecycle rule
that transitions everything under `processed/` to **S3 Glacier** after
`glacier_transition_days` (default 30 — override with `-var`).

## Option B — AWS CLI fallback (no Terraform)

```bash
aws s3api create-bucket --bucket your-unique-bucket-name --region eu-west-1
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-unique-bucket-name \
  --lifecycle-configuration file://lifecycle.json
aws s3api put-public-access-block \
  --bucket your-unique-bucket-name \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Wiring it to the app

1. Replace `spidersilk-app-*` placeholders in `iam-app-policy.json` with your real
   bucket name, and attach that policy to whatever the app runs as (node
   instance profile, or an IRSA role referenced in
   `infra/helm/spidersilk-app/values.yaml` under `serviceAccount.annotations`).
2. Set `app_s3_bucket` in `infra/ansible/group_vars/production.yml` to the
   same bucket name, then re-render config (`infra/ansible/README.md`) and
   `helm upgrade`.

The app itself (`app/s3_utils.py`) uploads under the `processed/` prefix,
which is exactly what the lifecycle rule and IAM policy above are scoped to.
