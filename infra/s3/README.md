# S3 storage + Glacier transition

Not applied — no AWS credentials at build time. Ready to run once you have
an account.

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

1. Replace `spidersilk-app-*` placeholders in `iam-app-policy.json` with your
   real bucket name; attach to the app's instance profile or IRSA role
   (`values.yaml` → `serviceAccount.annotations`).
2. Set `app_s3_bucket` in `infra/ansible/group_vars/production.yml`,
   re-render config, `helm upgrade`.

The app uploads under `processed/` — matches the lifecycle rule and IAM
policy scope above.
