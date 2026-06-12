import { useQuery } from "@tanstack/react-query";
import { billing } from "../api";
import { useAuthStore } from "../stores/auth";

/**
 * Cached "is this viewer a subscriber?" answer.
 *
 * Fetched once per session (the global 5-min staleTime applies) and shared via
 * the same ["my-subscription"] key the Subscribe page uses, so subscribing or
 * cancelling invalidates everyone at once. This lets the title page show
 * "Subscribe to Watch" IMMEDIATELY instead of letting a non-subscriber click
 * Play and wait for the server's 402 round-trip to say no.
 *
 * While the answer is still loading (`isResolved` false) callers should give
 * the user the benefit of the doubt and show the normal Play CTA — the Watch
 * page's paywall still catches non-subscribers, just less politely.
 */
export function useSubscription() {
  const isLoggedIn = useAuthStore((s) => !!s.accessToken);
  const q = useQuery({
    queryKey: ["my-subscription"],
    queryFn: () => billing.mySubscription(),
    enabled: isLoggedIn,
  });
  return {
    subscription: q.data ?? null,
    isSubscriber: q.data?.status === "active",
    isResolved: !isLoggedIn || q.isFetched,
    isLoggedIn,
  };
}
