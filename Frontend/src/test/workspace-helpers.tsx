/**
 * Test helpers — mock providers, fetch interceptors, and workspace test utilities.
 *
 * These helpers let us:
 *   1. Render components inside AuthProvider + WorkspaceProvider without real Supabase
 *   2. Control fetch responses per-URL
 *   3. Inspect workspace state transitions
 *   4. Control timing of async operations
 */

import React, { type ReactNode } from "react";
import { render, type RenderResult } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface MockWorkspace {
  id: string;
  name: string;
  role: string;
}

export interface FetchCall {
  url: string;
  options: RequestInit;
}

// ── Fetch interceptor ──────────────────────────────────────────────────────────

type FetchHandler = (url: string, options: RequestInit) => Promise<Response>;

let fetchHandlers: FetchHandler[] = [];
let fetchCalls: FetchCall[] = [];

/**
 * Register a fetch handler. Handlers are checked in order; first match wins.
 * Returns a cleanup function.
 */
export function interceptFetch(handler: FetchHandler): () => void {
  fetchHandlers.push(handler);
  return () => {
    fetchHandlers = fetchHandlers.filter((h) => h !== handler);
  };
}

/**
 * Get all captured fetch calls.
 */
export function getFetchCalls(): FetchCall[] {
  return [...fetchCalls];
}

/**
 * Clear captured fetch calls.
 */
export function clearFetchCalls(): void {
  fetchCalls = [];
}

/**
 * Install mock fetch globally. Call in beforeEach.
 */
export function installMockFetch(): void {
  fetchCalls = [];
  fetchHandlers = [];

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const options = init || {};
      fetchCalls.push({ url, options });

      for (const handler of fetchHandlers) {
        try {
          const response = await handler(url, options);
          return response;
        } catch {
          // Handler didn't match, try next
        }
      }

      // Default: 404
      return new Response(JSON.stringify({ detail: "Not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    })
  );
}

/**
 * Remove mock fetch. Call in afterEach.
 */
export function uninstallMockFetch(): void {
  vi.unstubAllGlobals();
  fetchHandlers = [];
  fetchCalls = [];
}

// ── Response helpers ───────────────────────────────────────────────────────────

export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function workspaceListResponse(workspaces: MockWorkspace[]): Response {
  return jsonResponse({ data: workspaces });
}

export function errorResponse(status: number, detail: string): Response {
  return jsonResponse({ detail }, status);
}

// ── Common fetch handler factories ─────────────────────────────────────────────

export function handleWorkspaceList(workspaces: MockWorkspace[]): FetchHandler {
  return async (url: string) => {
    if (url.includes("/workspaces") && !url.includes("/workspaces/")) {
      return workspaceListResponse(workspaces);
    }
    throw new Error("no match");
  };
}

export function handleWorkspaceCreate(
  created: MockWorkspace
): FetchHandler {
  return async (url: string, options: RequestInit) => {
    if (url.includes("/workspaces") && options.method === "POST") {
      return jsonResponse({ data: created }, 201);
    }
    throw new Error("no match");
  };
}

export function handleDashboard(status: number, body: unknown): FetchHandler {
  return async (url: string) => {
    if (url.includes("/accounts/dashboard")) {
      return jsonResponse(body, status);
    }
    throw new Error("no match");
  };
}

export function handleSignals(status: number, body: unknown): FetchHandler {
  return async (url: string) => {
    if (url.includes("/signals")) {
      return jsonResponse(body, status);
    }
    throw new Error("no match");
  };
}

export function handleAccounts(status: number, body: unknown): FetchHandler {
  return async (url: string) => {
    if (url.includes("/accounts") && !url.includes("dashboard")) {
      return jsonResponse(body, status);
    }
    throw new Error("no match");
  };
}

// ── QueryClient for tests ─────────────────────────────────────────────────────

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        refetchOnWindowFocus: false,
        // gcTime was cacheTime in v4; use gcTime in v5
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// ── Flush helpers ──────────────────────────────────────────────────────────────

/**
 * Flush all pending microtasks and one macrotask tick.
 */
export async function flushAsync(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

/**
 * Flush multiple rounds of async work.
 */
export async function flushAsyncMultiple(rounds = 3): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await flushAsync();
  }
}

// ── Storage key constant (must match WorkspaceProvider) ────────────────────────

export const WORKSPACE_STORAGE_KEY = "signal_radar_workspace_id";
