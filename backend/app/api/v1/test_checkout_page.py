"""
Dev-only HTML helper page that opens Razorpay Checkout for an order.

Useful before the React frontend is built. The page reads URL query params
(order_id, key_id, amount, currency, name, description) and opens Razorpay's
JS Checkout modal. On success it calls our /v1/payments/verify with the
returned signature, so the subscription is finalised even before the webhook
arrives.

NOT for production. The React frontend will do the same flow with proper UX.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>CinePile — Test Checkout</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 520px; margin: 60px auto; padding: 0 16px; color: #111; }
    .card { background: #fafafa; border: 1px solid #e2e2e2; border-radius: 12px; padding: 24px; }
    h1 { font-size: 22px; margin: 0 0 4px; }
    p { color: #555; margin: 4px 0; }
    .row { display: flex; justify-content: space-between; margin: 12px 0; padding: 8px 0; border-bottom: 1px solid #eee; }
    .row:last-child { border-bottom: none; }
    .label { color: #555; }
    .value { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    button { display: block; width: 100%; padding: 14px; background: #E50914; color: white; border: 0; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer; margin-top: 16px; }
    button:hover { background: #c1080f; }
    .status { margin-top: 16px; padding: 12px; border-radius: 8px; }
    .ok { background: #ecfdf3; color: #0a6d3b; border: 1px solid #b6e5cc; }
    .err { background: #fef0f0; color: #8e0e0e; border: 1px solid #f3b8b8; }
    .muted { font-size: 13px; color: #888; margin-top: 24px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>CinePile — Test Checkout</h1>
    <p>Razorpay one-time payment for one billing period.</p>
    <div id="summary"></div>
    <button id="pay">Pay now</button>
    <div id="status"></div>
  </div>
  <p class="muted">
    Test card: <b>4111 1111 1111 1111</b> &nbsp;·&nbsp; expiry <b>12/30</b> &nbsp;·&nbsp; CVV <b>123</b> &nbsp;·&nbsp; OTP <b>1234</b>
  </p>

  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <script>
    const qs = new URLSearchParams(location.search);
    const order_id = qs.get('order_id');
    const key_id = qs.get('key_id');
    const amount = qs.get('amount');
    const currency = qs.get('currency') || 'INR';
    const name = qs.get('name') || 'CinePile';
    const description = qs.get('description') || 'Subscription';
    const access_token = qs.get('token'); // backend access token, passed for the verify call

    document.getElementById('summary').innerHTML = `
      <div class="row"><span class="label">Plan</span><span class="value">${description}</span></div>
      <div class="row"><span class="label">Amount</span><span class="value">${currency} ${(amount/100).toFixed(2)}</span></div>
      <div class="row"><span class="label">Order ID</span><span class="value">${order_id}</span></div>
    `;

    function setStatus(msg, ok) {
      const el = document.getElementById('status');
      el.className = 'status ' + (ok ? 'ok' : 'err');
      el.textContent = msg;
    }

    document.getElementById('pay').addEventListener('click', () => {
      const rzp = new Razorpay({
        key: key_id,
        order_id: order_id,
        amount: amount,
        currency: currency,
        name: name,
        description: description,
        handler: async function (response) {
          setStatus('Payment captured — verifying with backend...', true);
          try {
            const verify = await fetch('/v1/payments/verify', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + access_token,
              },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              })
            });
            if (verify.ok) {
              const body = await verify.json();
              setStatus('Subscription is now ' + body.status + '. You can close this tab.', true);
            } else {
              const body = await verify.json().catch(() => ({}));
              setStatus('Verify failed: ' + (body?.detail?.error?.message || verify.status), false);
            }
          } catch (e) {
            setStatus('Verify network error: ' + e.message, false);
          }
        },
        modal: { ondismiss: () => setStatus('Checkout closed without payment.', false) },
        prefill: {},
        theme: { color: '#E50914' }
      });
      rzp.open();
    });
  </script>
</body>
</html>
"""


@router.get("/test-checkout", response_class=HTMLResponse, include_in_schema=False)
async def test_checkout_page() -> HTMLResponse:
    return HTMLResponse(content=_PAGE)
