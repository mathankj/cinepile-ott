# Razorpay webhook setup — connecting test mode to your local backend

This is what you do **once**, after Razorpay test keys are wired in. It connects Razorpay's test-mode webhooks to your local uvicorn so you can test the real end-to-end subscription flow (subscribe → user pays via test card → Razorpay calls our webhook → local DB flips to `active`).

---

## Why ngrok

Razorpay's webhooks call **your server from the internet**. Your local `http://localhost:8000` isn't reachable from the internet, so ngrok creates a public HTTPS tunnel that forwards to your local port.

**Free tier of ngrok is enough for this** — you get one tunnel + a random URL that changes each restart (paid plan keeps the URL stable). For dev, that's fine; you'll just update the Razorpay webhook URL when ngrok rotates it.

## Step 1 — Install ngrok (one-time, 2 min)

**Windows (choose one):**
- **Scoop** (recommended if you have scoop): `scoop install ngrok`
- **Direct download**: https://ngrok.com/download → Windows .zip → extract `ngrok.exe` to anywhere on PATH (e.g. `C:\Users\matha\bin\`)
- **winget**: `winget install Ngrok.Ngrok`

Verify:
```powershell
ngrok version
```

## Step 2 — Authenticate ngrok (one-time)

1. Sign up at **https://dashboard.ngrok.com/signup** (free, GitHub/Google SSO works)
2. After signup you land on **Your Authtoken** page (or **Setup & Installation** → **Your Authtoken**)
3. Copy the authtoken and run:
   ```powershell
   ngrok config add-authtoken <your-token>
   ```
   This writes the token to `~/.ngrok2/ngrok.yml` (or `%LOCALAPPDATA%\ngrok\ngrok.yml`).

## Step 3 — Start the local backend

In one terminal:
```powershell
cd C:\Users\matha\temp\anjaneya-ott\backend
.venv\Scripts\activate
uvicorn app.main:app --port 8000 --reload
```

Confirm:
```
curl http://localhost:8000/healthz
# → {"status":"ok","db":"ok",...}
```

## Step 4 — Start ngrok tunnel

In another terminal:
```powershell
ngrok http 8000
```

You'll see something like:
```
Session Status    online
Forwarding        https://abc1-203-0-113-42.ngrok-free.app -> http://localhost:8000
```

Copy that `https://abc1-....ngrok-free.app` URL. **Leave this terminal running for the whole dev session.**

## Step 5 — Create the webhook in Razorpay dashboard

1. Open https://dashboard.razorpay.com → make sure you're in **Test Mode** (top-right toggle)
2. Sidebar → **Account & Settings** → **Webhooks**
3. Click **Add New Webhook**
4. **Webhook URL**:
   ```
   https://abc1-....ngrok-free.app/v1/webhooks/razorpay
   ```
   (replace with your actual ngrok URL)
5. **Secret**: click **Generate** — Razorpay shows you a random secret. Copy it now.
6. **Alert Email**: your email
7. **Active Events** — tick these:
   - `subscription.activated`
   - `subscription.authenticated`
   - `subscription.charged`
   - `subscription.cancelled`
   - `subscription.completed`
   - `subscription.halted`
   - `subscription.paused`
   - `subscription.pending`
8. Click **Create Webhook**

## Step 6 — Save the webhook secret to backend

Open `backend/.env` and set:
```
RAZORPAY_WEBHOOK_SECRET=<the secret from step 5>
```

Restart uvicorn (Ctrl+C → re-run). The webhook handler now verifies signatures with this secret.

## Step 7 — Full end-to-end test

1. **Sign up and login** in the backend:
   ```bash
   curl -X POST http://localhost:8000/v1/auth/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password123","full_name":"Test"}'
   ```
   Copy the `access_token`.

2. **Subscribe** (triggers Razorpay Plan + Subscription creation):
   ```bash
   curl -X POST http://localhost:8000/v1/subscriptions \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"plan_code":"monthly"}'
   ```
   Response includes `"status":"pending"` and `"checkout_url":"https://rzp.io/i/..."`.

3. **Open the checkout_url in a browser.** Razorpay shows the test checkout. Use one of their test cards:
   - Card: `4111 1111 1111 1111`
   - CVV: any 3 digits
   - Expiry: any future date
   - OTP: `1234`

4. **After successful payment**, Razorpay will hit your ngrok URL → your `/v1/webhooks/razorpay` endpoint → flips your local subscription row to `status='active'`.

5. **Verify**:
   ```bash
   curl http://localhost:8000/v1/subscriptions/me -H "Authorization: Bearer <token>"
   # → {"status":"active", "checkout_url": null, ...}
   ```

## Step 8 — Triggering individual events for testing (without checkout)

Razorpay dashboard → **Webhooks** → click your webhook → **Test** tab → pick an event → **Send Test**. This fires a synthetic payload at your endpoint so you can validate handlers without doing the full payment flow.

You can also use **ngrok's web inspector** at http://localhost:4040 to see every webhook hit (with the raw payload + your response). Excellent for debugging.

---

## Common pitfalls

| Symptom | Fix |
|---|---|
| Webhook returns 401 "invalid_signature" | `RAZORPAY_WEBHOOK_SECRET` doesn't match what's in Razorpay dashboard. Copy-paste again. |
| Webhook returns 200 "unknown_subscription_..." | The subscription was created via a different DB (you reset/reseeded). Subscribe again. |
| ngrok URL stopped working | Free tier rotates URLs on restart. Update the URL in Razorpay dashboard. Or upgrade ngrok for a stable URL ($8/mo). |
| Razorpay subscription stays `pending` | You haven't completed the test-card payment. Open the `checkout_url`. |
| `curl` POST hangs | uvicorn may be in `--reload` rebuild. Wait 2 seconds. |

## Cleanup

When you're done for the day:
- Ctrl+C the ngrok terminal
- Ctrl+C uvicorn

Razorpay's webhook stays configured with a stale ngrok URL — next session, update it. Or use a [reusable subdomain on ngrok paid](https://ngrok.com/pricing) if you want it stable forever ($8/mo).

## When you go to production

Replace ngrok with your real production URL (`https://api.anjaneya.in/v1/webhooks/razorpay`) and:
- Switch Razorpay from Test Mode to Live Mode (top-right toggle in dashboard)
- Create a NEW webhook (live mode has separate webhook config from test mode)
- Generate a NEW webhook secret for live
- Put live keys + live webhook secret in your prod `.env`

Test webhook config and live webhook config are independent — useful so you can keep testing in dev without affecting prod.
