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
      retry: 1,
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
