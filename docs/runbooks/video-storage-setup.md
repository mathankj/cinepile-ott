# Video storage setup — dev

The verdict after surveying every free tier (research in `docs/research/`):

**Cloudflare R2** is the right pick for dev. **10 GB storage + free unlimited egress + no credit card.** S3-compatible API, so we use `boto3` exactly like AWS S3.

For reference, here's the comparison the research turned up:

| Provider | Free storage | Free egress | CC required | Notes |
|---|---|---|---|---|
| **Cloudflare R2** | **10 GB** | **Unlimited** (via CF CDN) | **No** | ⭐ pick this |
| Storj | 25 GB | 25 GB/month | No | Bigger limits but harder DX |
| Backblaze B2 | 10 GB | ~30 GB/mo dynamic | No | Pair with CF CDN for unlimited egress |
| IDrive e2 | 5 GB | 5 GB/mo | No | Tight |
| Bunny Stream | $20 trial credit | included | No at signup | Burns out fast |
| AWS S3 | 5 GB (always-free) | 100 GB/mo | **Yes** | New accounts get $200 credit instead |
| GCS | 5 GB (US only) | 100 GB/mo | **Yes** | Region-locked |
| GitHub Releases + jsDelivr | 2 GB/file | "unlimited" (CDN-cached) | No | Public-only, hacky-but-free |
| Vimeo / YouTube | n/a | n/a | n/a | TOS prohibits direct re-hosting |

## Setting up Cloudflare R2 (5 minutes)

1. Sign up at **https://dash.cloudflare.com/sign-up** (or log in to your existing account)
2. Left sidebar → **R2 Object Storage** → **Get Started**
3. Cloudflare will ask you to confirm payment details. You won't be charged unless you exceed 10 GB. **They do NOT require a credit card** for the R2 free tier — just an account.
4. Click **Create bucket**:
   - Name: `anjaneya-dev-media`
   - Location hint: `Asia-Pacific` (closer to India users; egress is the same price = free)
   - Click **Create bucket**
5. In the bucket page → **Settings** tab → scroll to **Public access** → **Allow Access** (this enables the `r2.dev` URL for dev use; for production you'd attach a custom domain)
6. Copy the **Public R2.dev Bucket URL** — it'll look like `https://pub-<hash>.r2.dev`
7. Top-right → **Manage R2 API Tokens** → **Create API token**:
   - Token name: `anjaneya-dev`
   - Permissions: **Object Read & Write**
   - Specify bucket: `anjaneya-dev-media`
   - Click **Create API token**
8. Copy these three values (only shown once):
   - **Access Key ID**
   - **Secret Access Key**
   - **Endpoint** (looks like `https://<account-id>.r2.cloudflarestorage.com`)

## What to paste me

The env var names are **provider-agnostic** (`STORAGE_*` not `R2_*`) so the same backend works with Cloudflare R2, Backblaze B2, AWS S3, Storj, or any other S3-compatible object store.

```
STORAGE_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY_ID=...
STORAGE_SECRET_ACCESS_KEY=...
STORAGE_BUCKET=anjaneya-dev-media
# Leave STORAGE_PUBLIC_URL empty for private buckets (recommended) — playback
# generates short-lived presigned URLs each call. Only set this if you've made
# the bucket public.
STORAGE_PUBLIC_URL=https://pub-<hash>.r2.dev
```

## What I'll do once I have those

1. Add `boto3` to dependencies
2. Create `app/services/storage.py` — a thin wrapper around boto3 that:
   - `upload_file(local_path, key)` → uploads, returns the public URL
   - `delete_file(key)` → removes from bucket
   - `generate_presigned_url(key, ttl=3600)` → for private-bucket alternatives
3. Add an admin endpoint `POST /v1/admin/titles/{id}/upload-video` that:
   - Accepts a multipart file upload
   - Streams it into R2 under a deterministic key (`titles/{id}/master.mp4`)
   - Stores the public URL on the title's `TitleAsset` row
4. Same for episodes: `POST /v1/admin/episodes/{id}/upload-video`
5. Tests using `moto` (boto3 mock) so we don't hit real R2 in CI
6. Document the upload flow in the runbook

## Why not transcode for dev

Bunny Stream auto-transcodes on upload (MP4 → multi-bitrate HLS). R2 doesn't. For dev/testing, **we serve the raw MP4 directly** — `hls.js` (and every native HTML5 player) can play MP4 natively, no manifest needed. This is fine for end-to-end backend validation.

When you go to production:
- **If you stay with R2:** add a transcoding step. Easiest option is Cloudflare Stream ($0.001/min delivered), which can ingest from R2 and serve HLS. Or self-hosted FFmpeg workers on the VPS.
- **If you switch to Bunny Stream:** transcoding is included; one less component to manage.

That decision can wait until you have real content.

## Cost ceiling for dev usage

Realistic worst case during dev (you accidentally upload 50 MB × 100 times = 5 GB):
- Storage: **$0** (free up to 10 GB)
- Egress: **$0** (free, period)
- Operations: **$0** (free up to 1M writes / 10M reads per month)

You literally cannot incur a bill from R2 with normal dev usage.
