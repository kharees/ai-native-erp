# Security Notes

Operational security requirements that aren't (and in some cases can't
be) enforced purely by code — required manual setup steps, and the
reasoning behind them. Keep this updated as new requirements like this
come up; it's the canonical checklist for standing up a new environment
safely.

## Supabase Storage: the order-capture photo bucket must be PRIVATE

**Setting:** `ORDER_CAPTURE_STORAGE_BUCKET` in `app/core/config.py`
(default: `order-captures`).

**Why this matters:** `app/services/order_capture.py`'s photo-capture
pipeline uploads a photo of a customer's handwritten order to this
bucket. That photo is real customer data — handwriting that may include
names, phone numbers, addresses, or anything else written on the order
chit. If the bucket is public, **anyone who has or guesses an object
path can view it with no authentication at all** — Supabase Storage's
access control is bucket-level, not per-object, so there is no
finer-grained setting to fall back on.

### Required setup (do this once per Supabase project, before the bucket is used)

1. Open the Supabase dashboard for the project.
2. Go to **Storage** in the left sidebar.
3. Click **New bucket**.
4. Name it to match `ORDER_CAPTURE_STORAGE_BUCKET` exactly (default:
   `order-captures`).
5. **Leave the "Public bucket" toggle OFF.** This is the entire fix —
   do not enable it "temporarily" or "just for testing"; use a signed
   URL instead (see below).
6. Save/create the bucket.

If the bucket already exists and was created public by mistake: open the
bucket's settings in the dashboard and turn "Public bucket" OFF. Existing
objects are unaffected by the toggle change other than becoming
un-fetchable without a signed URL going forward, which is the intended
effect.

### How the backend enforces this

- **Upload** (`order_capture.py`'s `upload_and_parse`): the `.upload()`
  call sets no public/ACL option — there isn't one to set at the object
  level. Visibility is entirely the bucket setting above.
- **Read** (`order_capture.py`'s `get_draft_image_signed_url`, exposed via
  `GET /omnichannel-billing/order-capture/{draft_id}/image-url`): every
  read of the photo — by the backend, or by a client requesting to view
  it — goes through a fresh, short-lived **signed URL**
  (`storage.from_(bucket).create_signed_url(path, expires_in=300)`, i.e.
  5 minutes), never a stored or public URL. The vision-extraction call
  that reads the photo for AI parsing doesn't even do this much: it sends
  the raw bytes it already has in memory directly to the AI provider, so
  it never needs to fetch the image back from Storage at all.
- **Startup check** (`app/core/storage_security.py`'s
  `verify_order_capture_bucket_is_private`, called from `main.py`'s
  `lifespan`): on every application startup, the backend calls Supabase's
  Storage API to check the bucket's own `public` flag.
  - If it's public: logs a `CRITICAL` structured log line explaining the
    problem and exactly how to fix it, and — if `ENVIRONMENT=production`
    — **raises and refuses to start**. Non-production environments only
    log (so a misconfigured local/staging bucket doesn't block everyday
    development), but the log is never silent.
  - If the bucket doesn't exist yet, this logs a `WARNING` (not
    `CRITICAL`) and continues — a fresh environment before anyone has
    created the bucket is a setup gap, not a security incident.

### Frontend

The frontend never stores or constructs a Supabase Storage URL itself. To
display the uploaded photo (e.g. on the order-capture review screen), it
calls `GET /omnichannel-billing/order-capture/{draft_id}/image-url` and
uses the `url` it gets back — which expires in `expires_in_seconds`
(5 minutes) — requesting a fresh one on each page load/mount rather than
caching it.

---

## Adding a new entry to this file

When you add a new operational security requirement (a manual dashboard
step, a required env var that must be secret, a startup check that
guards against a misconfiguration), document it here the same way:
**what** the requirement is, **why** it matters (what's actually exposed
if it's missed), the **exact steps** to configure it correctly, and
**how the backend verifies/enforces it**, if it does.
