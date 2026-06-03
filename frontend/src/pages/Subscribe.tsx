import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { billing } from "../api";
import { useAuthStore } from "../stores/auth";

/**
 * Subscribe page — list plans, pick one, redirect to Razorpay Checkout.
 *
 * Backend returns either:
 *   - status='active' + null checkout_url (mock provider)
 *   - status='pending' + a checkout URL (Razorpay)
 *
 * For Razorpay Orders mode the checkout_url points at our dev /test-checkout
 * HTML helper. In prod, this component will instead instantiate Razorpay
 * Checkout JS directly with the order_id parsed from the URL.
 */
export default function Subscribe() {
  const qc = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [busyCode, setBusyCode] = useState<string | null>(null);

  const plansQ = useQuery({ queryKey: ["plans"], queryFn: () => billing.plans() });
  const subQ = useQuery({ queryKey: ["my-subscription"], queryFn: () => billing.mySubscription() });

  const subscribeM = useMutation({
    mutationFn: (planCode: string) => billing.subscribe(planCode),
    onMutate: (planCode) => setBusyCode(planCode),
    onSettled: () => {
      setBusyCode(null);
      qc.invalidateQueries({ queryKey: ["my-subscription"] });
    },
    onSuccess: (sub) => {
      if (sub.checkout_url) {
        // Append our access token so the test-checkout page can call /payments/verify
        const sep = sub.checkout_url.includes("?") ? "&" : "?";
        window.location.href = `${sub.checkout_url}${sep}token=${accessToken}`;
      }
    },
  });

  const cancelM = useMutation({
    mutationFn: () => billing.cancel(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-subscription"] }),
  });

  return (
    <div className="mx-auto max-w-[1100px] px-4 md:px-8 py-12">
      <h1 className="mb-8 text-[2rem] font-bold">Choose your plan</h1>

      {/* Current sub state */}
      {subQ.data && (
        <div className="mb-8 rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
          <div className="text-sm text-white/60">Current subscription</div>
          <div className="mt-1 text-lg font-semibold">
            {subQ.data.status === "active"
              ? "Active"
              : subQ.data.status === "pending"
              ? "Pending payment"
              : subQ.data.status}
          </div>
          {subQ.data.status === "active" && (
            <div className="mt-2 text-sm text-white/60">
              Renews on {new Date(subQ.data.current_period_end).toLocaleDateString()}
            </div>
          )}
          {subQ.data.status === "pending" && subQ.data.checkout_url && (
            <button
              type="button"
              className="btn-primary mt-4"
              onClick={() => {
                const sep = subQ.data!.checkout_url!.includes("?") ? "&" : "?";
                window.location.href = `${subQ.data!.checkout_url}${sep}token=${accessToken}`;
              }}
            >
              Complete checkout
            </button>
          )}
          {subQ.data.status === "active" && !subQ.data.cancel_at_period_end && (
            <button
              type="button"
              className="mt-4 text-sm text-white/60 hover:text-white"
              onClick={() => cancelM.mutate()}
            >
              Cancel subscription
            </button>
          )}
        </div>
      )}

      {/* Plans */}
      <div className="grid gap-4 md:grid-cols-2">
        {plansQ.data?.map((p) => {
          const isCurrent = subQ.data?.plan_id === p.id && subQ.data?.status === "active";
          return (
            <div
              key={p.id}
              className="flex flex-col rounded border border-white/10 bg-[var(--color-bg-elevated)] p-6"
            >
              <div className="mb-1 text-sm uppercase tracking-wider text-white/60">{p.code}</div>
              <h3 className="text-xl font-semibold">{p.name}</h3>
              <div className="mt-3 text-3xl font-bold">
                {p.currency === "INR" ? "₹" : p.currency} {(p.price_cents / 100).toFixed(0)}
                <span className="text-sm font-normal text-white/60"> / {p.billing_interval}</span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-white/80">
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> Unlimited streaming</li>
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> HD + 4K where available</li>
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> Watch on web, mobile, TV</li>
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> Cancel anytime</li>
              </ul>
              <div className="mt-6 flex-1" />
              {isCurrent ? (
                <button disabled className="btn-secondary opacity-60">Current plan</button>
              ) : (
                <button
                  type="button"
                  className="btn-primary"
                  disabled={busyCode === p.code}
                  onClick={() => subscribeM.mutate(p.code)}
                >
                  {busyCode === p.code ? "Starting…" : `Subscribe`}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
