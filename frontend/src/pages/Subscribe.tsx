import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import { billing } from "../api";

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
  const { t } = useTranslation();
  const qc = useQueryClient();
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
        // Navigate as-is — the backend embeds a scoped short-TTL token in the
        // URL itself. We must NOT append our long-lived access token here: it
        // would leak into browser history, referrers, and server logs.
        window.location.href = sub.checkout_url;
      }
    },
  });

  const cancelM = useMutation({
    mutationFn: () => billing.cancel(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-subscription"] }),
  });

  return (
    <div className="mx-auto max-w-[1100px] px-4 md:px-8 py-12">
      <h1 className="mb-8 text-[2rem] font-bold">{t("subscribe.title")}</h1>

      {/* Current sub state */}
      {subQ.data && (
        <div className="mb-8 rounded border border-white/10 bg-[var(--color-bg-elevated)] p-5">
          <div className="text-sm text-white/60">{t("subscribe.current_subscription")}</div>
          <div className="mt-1 text-lg font-semibold">
            {subQ.data.status === "active"
              ? t("subscribe.active")
              : subQ.data.status === "pending"
              ? t("subscribe.pending")
              : subQ.data.status}
          </div>
          {subQ.data.status === "active" && (
            <div className="mt-2 text-sm text-white/60">
              {t("subscribe.renews_on", { date: new Date(subQ.data.current_period_end).toLocaleDateString() })}
            </div>
          )}
          {subQ.data.status === "pending" && subQ.data.checkout_url && (
            <button
              type="button"
              className="btn-primary mt-4"
              onClick={() => {
                window.location.href = subQ.data!.checkout_url!;
              }}
            >
              {t("subscribe.complete_checkout")}
            </button>
          )}
          {subQ.data.status === "active" && !subQ.data.cancel_at_period_end && (
            <button
              type="button"
              className="mt-4 text-sm text-white/60 hover:text-white"
              onClick={() => cancelM.mutate()}
            >
              {t("subscribe.cancel")}
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
                <span className="text-sm font-normal text-white/60">
                  {" / "}
                  {p.billing_interval === "month"
                    ? t("subscribe.per_month")
                    : p.billing_interval === "year"
                    ? t("subscribe.per_year")
                    : p.billing_interval}
                </span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-white/80">
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> {t("subscribe.feature_unlimited")}</li>
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> {t("subscribe.feature_quality")}</li>
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> {t("subscribe.feature_devices")}</li>
                <li className="flex items-center gap-2"><Check size={14} className="text-green-400" /> {t("subscribe.feature_cancel")}</li>
              </ul>
              <div className="mt-6 flex-1" />
              {isCurrent ? (
                <button disabled className="btn-secondary opacity-60">{t("subscribe.current_plan")}</button>
              ) : (
                <button
                  type="button"
                  className="btn-primary"
                  disabled={busyCode === p.code}
                  onClick={() => subscribeM.mutate(p.code)}
                >
                  {busyCode === p.code ? t("subscribe.starting") : t("subscribe.subscribe_cta")}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
