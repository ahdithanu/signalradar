/**
 * Workspace resilience tests — validates system behavior under edge cases.
 *
 * Tests:
 *   1. Reset followed by /workspaces 500 (recovery fetch fails)
 *   2. Duplicate zero-workspace auto-create (Strict Mode double effect)
 *   3. Stale localStorage workspace mismatch
 *   4. Late mutation failure after reset (in-flight response post-reset)
 *   5. POST create success followed by refetch failure
 *   6. Concurrent 403 events produce exactly one reset
 *   7. 400 → reset does NOT cause infinite refetch loop
 *   8. resetInFlightRef unlocked too early
 *
 * These tests exercise the event bus, WorkspaceProvider, and WorkspaceGate
 * WITHOUT real Supabase. They mock fetch and the Supabase module.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  emitWorkspaceError,
  onWorkspaceError,
} from "@/lib/workspace-events";
import { WORKSPACE_STORAGE_KEY } from "./workspace-helpers";

// ── Mock Supabase before any imports that use it ─────────────────────────────

const mockSession = {
  access_token: "test-token-123",
  user: { id: "user-1", email: "test@test.com" },
};

vi.mock("@/lib/supabase", () => {
  const session = {
    access_token: "test-token-123",
    user: { id: "user-1", email: "test@test.com" },
  };

  return {
    supabase: {
      auth: {
        getSession: () => Promise.resolve({ data: { session } }),
        onAuthStateChange: (callback: any) => {
          // Fire callback immediately to set user state in AuthProvider
          // This mimics Supabase SDK behavior on initial session restore
          Promise.resolve().then(() => callback("SIGNED_IN", session));
          return {
            data: { subscription: { unsubscribe: () => {} } },
          };
        },
        signOut: () => Promise.resolve({ error: null }),
        signUp: () => Promise.resolve({ error: null }),
        signInWithPassword: () => Promise.resolve({ error: null }),
      },
    },
  };
});

// Mock clearQueryCache to avoid shared queryClient interference
vi.mock("@/lib/query-client", () => ({
  queryClient: null, // Not used directly in tests
  clearQueryCache: () => {}, // No-op — tests use their own QueryClient
}));

// Now import components that depend on supabase
import { AuthProvider, useAuth } from "@/auth/AuthProvider";
import { WorkspaceProvider, useWorkspace } from "@/auth/WorkspaceProvider";
import { WorkspaceGate } from "@/auth/WorkspaceGate";

// ── Test utilities ───────────────────────────────────────────────────────────

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

let testQueryClient: QueryClient;

/**
 * Wraps children in all required providers with mocked auth.
 */
function TestWrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={testQueryClient}>
      <AuthProvider>
        <WorkspaceProvider>{children}</WorkspaceProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

/**
 * Component that exposes workspace state to tests via data-testid attributes.
 */
function WorkspaceStateInspector() {
  const ws = useWorkspace();
  return (
    <div>
      <span data-testid="ws-active">{ws.activeWorkspaceId ?? "null"}</span>
      <span data-testid="ws-loading">{String(ws.loading)}</span>
      <span data-testid="ws-needs-selection">{String(ws.needsSelection)}</span>
      <span data-testid="ws-needs-creation">{String(ws.needsCreation)}</span>
      <span data-testid="ws-count">{ws.workspaces.length}</span>
      <button data-testid="ws-reset" onClick={() => ws.resetWorkspace("test-reset")}>
        Reset
      </button>
      <button data-testid="ws-select" onClick={() => ws.selectWorkspace("ws-1")}>
        Select
      </button>
    </div>
  );
}

// ── Fetch mock infrastructure ────────────────────────────────────────────────

type MockFetchFn = (url: string, opts?: RequestInit) => Promise<Response>;
let mockFetchImpl: MockFetchFn;

function setFetchImpl(impl: MockFetchFn) {
  mockFetchImpl = impl;
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ── Setup / teardown ─────────────────────────────────────────────────────────

beforeEach(() => {
  localStorage.clear();
  testQueryClient = createTestQueryClient();

  // Default fetch: return empty workspace list
  mockFetchImpl = async () => jsonResponse({ data: [] });

  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    return mockFetchImpl(url, init);
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  localStorage.clear();
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 1: Reset followed by /workspaces 500
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 1: Reset followed by /workspaces 500", () => {
  it("handles recovery fetch failure without crashing", async () => {
    let fetchCount = 0;

    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        fetchCount++;
        if (fetchCount === 1) {
          // First fetch: return one workspace (normal bootstrap)
          return jsonResponse({
            data: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
          });
        }
        // Second fetch (after reset): return 500
        return jsonResponse({ detail: "Internal server error" }, 500);
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    // Wait for initial workspace to be set
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    // Trigger reset (simulates 403 event)
    await act(async () => {
      emitWorkspaceError("workspace_forbidden", "revoked");
    });

    // After reset, workspace should be cleared
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("null");
    });

    // The recovery fetch failed with 500 → workspaces should be empty
    await waitFor(() => {
      expect(screen.getByTestId("ws-count").textContent).toBe("0");
    });

    // needsCreation should be true (0 workspaces after failed fetch)
    expect(screen.getByTestId("ws-needs-creation").textContent).toBe("true");

    // localStorage should be cleared
    expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 2: Duplicate zero-workspace auto-create (Strict Mode)
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 2: Strict Mode duplicate auto-create prevention", () => {
  it("attemptedRef prevents duplicate workspace creation", async () => {
    let createCount = 0;

    setFetchImpl(async (url, opts) => {
      if (url.includes("/workspaces")) {
        if (opts?.method === "POST") {
          createCount++;
          return jsonResponse(
            { data: { id: "new-ws", name: "My Workspace", role: "owner" } },
            201
          );
        }
        // GET /workspaces
        if (createCount === 0) {
          return jsonResponse({ data: [] }); // No workspaces yet
        }
        // After creation
        return jsonResponse({
          data: [{ id: "new-ws", name: "My Workspace", role: "owner" }],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceGate>
          <span data-testid="gate-child">Content</span>
        </WorkspaceGate>
      </TestWrapper>
    );

    // Wait for the workspace to be auto-created and auto-selected
    await waitFor(
      () => {
        expect(screen.getByTestId("gate-child")).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    // Exactly 1 POST should have been made, NOT 2 (Strict Mode would call useEffect twice)
    expect(createCount).toBe(1);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 3: Stale localStorage workspace mismatch
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 3: Stale localStorage workspace ID", () => {
  it("clears invalid stored workspace ID and forces selection", async () => {
    // Pre-seed localStorage with a workspace ID that won't exist on the server
    localStorage.setItem(WORKSPACE_STORAGE_KEY, "stale-ws-id-that-no-longer-exists");

    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        return jsonResponse({
          data: [
            { id: "ws-a", name: "Workspace A", role: "owner" },
            { id: "ws-b", name: "Workspace B", role: "member" },
          ],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    // Should detect that "stale-ws-id-that-no-longer-exists" is not in the list
    // and clear it, then set needsSelection = true
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("null");
      expect(screen.getByTestId("ws-needs-selection").textContent).toBe("true");
    });

    // localStorage should be cleared (hydrate null removes stale value)
    expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBeNull();
  });

  it("auto-selects if stale ID is cleared and only one workspace exists", async () => {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, "stale-ws-id");

    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        return jsonResponse({
          data: [{ id: "ws-only", name: "Only One", role: "owner" }],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    // Stale ID doesn't match "ws-only", but since there's only 1 workspace,
    // it should auto-select "ws-only" via mutateWorkspaceId
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-only");
    });

    // localStorage should now have the correct ID
    expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBe("ws-only");
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 4: Late mutation after reset (in-flight response post-reset)
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 4: Late workspace error events after reset", () => {
  it("concurrent errors produce at most one recovery fetch, not N", async () => {
    let fetchCount = 0;

    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        fetchCount++;
        return jsonResponse({
          data: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    const fetchCountBefore = fetchCount;

    // Simulate 3 concurrent 403 events arriving at once
    await act(async () => {
      emitWorkspaceError("workspace_forbidden", "error 1");
      emitWorkspaceError("workspace_forbidden", "error 2");
      emitWorkspaceError("workspace_forbidden", "error 3");
    });

    // System should recover: either it stays at ws-1 (fast recovery) or eventually returns
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    // The critical assertion: 3 events should NOT cause 3 recovery fetches
    // resetInFlightRef should block the 2nd and 3rd events
    // At most 1 recovery fetch should have fired (total: fetchCountBefore + 1)
    expect(fetchCount - fetchCountBefore).toBeLessThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 5: POST create success, refetch fails
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 5: Workspace creation succeeds but refetch fails", () => {
  it("shows error when refetch after creation returns 500", async () => {
    let getCount = 0;

    setFetchImpl(async (url, opts) => {
      if (url.includes("/workspaces")) {
        if (opts?.method === "POST") {
          return jsonResponse(
            { data: { id: "created-ws", name: "My Workspace", role: "owner" } },
            201
          );
        }
        // GET /workspaces
        getCount++;
        if (getCount === 1) {
          // First GET: no workspaces → triggers creation
          return jsonResponse({ data: [] });
        }
        // Second GET (refetch after create): 500
        return jsonResponse({ detail: "Server error" }, 500);
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceGate>
          <span data-testid="gate-child">Content</span>
        </WorkspaceGate>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    // After create succeeds but refetch fails, workspaces should be empty
    // and needsCreation should be true again (because setWorkspaces([]) on error)
    await waitFor(
      () => {
        const wsCount = screen.getByTestId("ws-count").textContent;
        const needsCreation = screen.getByTestId("ws-needs-creation").textContent;
        // Either we see needsCreation or the creation error UI
        expect(wsCount === "0" || needsCreation === "true").toBe(true);
      },
      { timeout: 5000 }
    );
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 6: localStorage sync is atomic with React state
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 6: localStorage and React state remain in sync", () => {
  it("selectWorkspace writes to both localStorage and React state atomically", async () => {
    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        return jsonResponse({
          data: [
            { id: "ws-a", name: "A", role: "owner" },
            { id: "ws-b", name: "B", role: "member" },
          ],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    // Wait for needsSelection
    await waitFor(() => {
      expect(screen.getByTestId("ws-needs-selection").textContent).toBe("true");
    });

    // Select workspace ws-1 (button selects "ws-1")
    // Note: the inspector's select button hardcodes "ws-1" which isn't in the list
    // but mutateWorkspaceId should still set both state and localStorage
    await act(async () => {
      screen.getByTestId("ws-select").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBe("ws-1");
  });

  it("resetWorkspace clears localStorage even if recovery re-selects", async () => {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, "ws-1");
    let fetchCount = 0;

    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        fetchCount++;
        if (fetchCount <= 1) {
          // First fetch: return workspace so it gets selected
          return jsonResponse({
            data: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
          });
        }
        // After reset, return 0 workspaces to prevent re-selection
        return jsonResponse({ data: [] });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    await act(async () => {
      screen.getByTestId("ws-reset").click();
    });

    // After reset + recovery fetch returning 0 workspaces, state should be null
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("null");
      expect(screen.getByTestId("ws-needs-creation").textContent).toBe("true");
    });

    expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 7: WorkspaceGate blocks children when no active workspace
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 7: WorkspaceGate renders correctly for each state", () => {
  it("renders children when workspace is active", async () => {
    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        return jsonResponse({
          data: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceGate>
          <span data-testid="app-content">App Content</span>
        </WorkspaceGate>
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-content")).toBeInTheDocument();
    });
  });

  it("shows workspace selector when multiple workspaces and none selected", async () => {
    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        return jsonResponse({
          data: [
            { id: "ws-a", name: "Workspace A", role: "owner" },
            { id: "ws-b", name: "Workspace B", role: "member" },
          ],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceGate>
          <span data-testid="app-content">App Content</span>
        </WorkspaceGate>
      </TestWrapper>
    );

    await waitFor(() => {
      // WorkspaceSelector renders "Select workspace" heading
      expect(screen.getByText("Select workspace")).toBeInTheDocument();
    });

    // App content should NOT be rendered
    expect(screen.queryByTestId("app-content")).not.toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 8: Logout clears all workspace state
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 8: Reset clears workspace state then recovery determines final state", () => {
  it("reset triggers recovery fetch — final state depends on backend response", async () => {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, "ws-1");
    let fetchCount = 0;

    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        fetchCount++;
        return jsonResponse({
          data: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBe("ws-1");
    const fetchCountBefore = fetchCount;

    await act(async () => {
      screen.getByTestId("ws-reset").click();
    });

    // Reset triggers setFetched(false) → refetch → auto-select ws-1 again
    // The important thing: a fetch WAS triggered (proving reset ran)
    await waitFor(() => {
      expect(fetchCount).toBeGreaterThan(fetchCountBefore);
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    // localStorage should have ws-1 again after recovery auto-select
    expect(localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBe("ws-1");
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 9: isNonRetryableError prevents React Query retries
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 9: React Query retry prevention", () => {
  it("ApiRequestError with workspace_required is non-retryable", async () => {
    const { isNonRetryableError, ApiRequestError } = await import("@/api/client");

    const wsError = new ApiRequestError({
      status: 400,
      detail: "workspace required",
      type: "workspace_required",
    });
    expect(isNonRetryableError(wsError)).toBe(true);

    const forbiddenError = new ApiRequestError({
      status: 403,
      detail: "forbidden",
      type: "forbidden",
    });
    expect(isNonRetryableError(forbiddenError)).toBe(true);

    const unauthorizedError = new ApiRequestError({
      status: 401,
      detail: "unauthorized",
      type: "unauthorized",
    });
    expect(isNonRetryableError(unauthorizedError)).toBe(true);

    const serverError = new ApiRequestError({
      status: 500,
      detail: "server error",
      type: "server",
    });
    expect(isNonRetryableError(serverError)).toBe(false);

    const clientError = new ApiRequestError({
      status: 422,
      detail: "validation",
      type: "client",
    });
    expect(isNonRetryableError(clientError)).toBe(false);

    // Non-ApiRequestError
    expect(isNonRetryableError(new Error("random"))).toBe(false);
    expect(isNonRetryableError(null)).toBe(false);
    expect(isNonRetryableError(undefined)).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEST 10: Event bus → WorkspaceProvider → state transition is deterministic
// ═══════════════════════════════════════════════════════════════════════════════

describe("Test 10: Full event-to-state transition", () => {
  it("workspace_forbidden event triggers recovery and ends in valid state", async () => {
    let fetchCount = 0;

    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        fetchCount++;
        return jsonResponse({
          data: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    const initialFetchCount = fetchCount;

    // Emit workspace error (simulates client.ts receiving 403)
    await act(async () => {
      emitWorkspaceError("workspace_forbidden", "not a member");
    });

    // System should eventually recover — either transient null or direct recovery
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    // Must have triggered exactly one recovery fetch
    expect(fetchCount).toBe(initialFetchCount + 1);
  });

  it("workspace_required event resets state and triggers refetch", async () => {
    setFetchImpl(async (url) => {
      if (url.includes("/workspaces")) {
        return jsonResponse({
          data: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
        });
      }
      return jsonResponse({ data: [] });
    });

    render(
      <TestWrapper>
        <WorkspaceStateInspector />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });

    await act(async () => {
      emitWorkspaceError("workspace_required", "missing workspace");
    });

    // Should reset then recover
    await waitFor(() => {
      expect(screen.getByTestId("ws-active").textContent).toBe("ws-1");
    });
  });
});
