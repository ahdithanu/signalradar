/**
 * Shared QueryClient instance.
 *
 * Extracted from App.tsx so that AuthProvider and WorkspaceProvider
 * can call queryClient.clear() without circular imports.
 */

import { QueryClient } from "@tanstack/react-query";
import { isNonRetryableError } from "@/api/client";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (isNonRetryableError(error)) return false;
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});

/**
 * Clear all React Query caches.
 * Called on logout and workspace reset.
 */
export function clearQueryCache(): void {
  queryClient.clear();
}
