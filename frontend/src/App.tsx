import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppRouter } from "./routes";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 5 min stale: navigating Home → Title → Home doesn't refetch — instant.
      // 30 min gcTime: keep cached pages in memory across tab visibility blips.
      staleTime: 5 * 60_000,
      gcTime: 30 * 60_000,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      // 4xx responses are FINAL — a 402 paywall or 404 won't change on retry,
      // and retrying doubles the wait before the user sees the real answer
      // (most visible on Play → "subscription required"). Only retry once on
      // network failures / 5xx, where a second attempt can actually help.
      retry: (failureCount, error) => {
        const status = (error as { response?: { status?: number } })?.response?.status;
        if (status !== undefined && status >= 400 && status < 500) return false;
        return failureCount < 1;
      },
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRouter />
    </QueryClientProvider>
  );
}
