/**
 * Centralized API client — attaches auth headers and handles errors.
 *
 * All backend requests go through this module.
 * - Authorization: Bearer <token> on every request when logged in
 * - X-Workspace-Id when an active workspace is set
 * - Centralized error handling for 401, 403, 400
 *
 * OWNERSHIP RULES:
 * - This module NEVER mutates localStorage.
 * - Workspace state changes are signaled via workspace-events.ts.
 * - WorkspaceProvider is the single owner of workspace state.
 */

import { supabase } from "@/lib/supabase";
import { emitWorkspaceError } from "@/lib/workspace-events";

const WORKSPACE_STORAGE_KEY = "signal_radar_workspace_id";

function getBaseUrl(): string {
  return import.meta.env.VITE_API_URL || "";
}

async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/**
 * Read workspace ID from localStorage (read-only).
 * WorkspaceProvider owns writes; this module only reads.
 */
function getWorkspaceId(): string | null {
  return localStorage.getItem(WORKSPACE_STORAGE_KEY);
}

interface ApiError {
  status: number;
  detail: string;
  type: "unauthorized" | "forbidden" | "workspace_required" | "client" | "server";
}

export class ApiRequestError extends Error {
  status: number;
  detail: string;
  type: ApiError["type"];

  constructor(error: ApiError) {
    super(error.detail);
    this.status = error.status;
    this.detail = error.detail;
    this.type = error.type;
  }
}

/**
 * Returns true if the error should NOT be retried by React Query.
 */
export function isNonRetryableError(error: unknown): boolean {
  if (error instanceof ApiRequestError) {
    return (
      error.type === "unauthorized" ||
      error.type === "forbidden" ||
      error.type === "workspace_required"
    );
  }
  return false;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) {
    return res.json();
  }

  let detail = `Request failed: ${res.status}`;
  try {
    const body = await res.json();
    detail = body.detail || detail;
  } catch {
    // Non-JSON error response
  }

  // ── 401: Token expired or invalid ──────────────────────────────────
  if (res.status === 401) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new ApiRequestError({
      status: 401,
      detail: "Session expired. Please log in again.",
      type: "unauthorized",
    });
  }

  // ── 403: Forbidden (includes workspace access denied) ──────────────
  if (res.status === 403) {
    const isWorkspaceError =
      detail.toLowerCase().includes("workspace") ||
      detail.toLowerCase().includes("not a member");

    if (isWorkspaceError) {
      emitWorkspaceError("workspace_forbidden", detail);
    }

    throw new ApiRequestError({
      status: 403,
      detail: detail || "You do not have access to this resource.",
      type: "forbidden",
    });
  }

  // ── 400: Workspace required ────────────────────────────────────────
  if (res.status === 400 && detail.toLowerCase().includes("workspace")) {
    emitWorkspaceError("workspace_required", detail);
    throw new ApiRequestError({
      status: 400,
      detail,
      type: "workspace_required",
    });
  }

  // ── Other errors ───────────────────────────────────────────────────
  const type = res.status >= 500 ? "server" : "client";
  throw new ApiRequestError({ status: res.status, detail, type });
}

async function buildHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const token = await getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const wsId = getWorkspaceId();
  if (wsId) {
    headers["X-Workspace-Id"] = wsId;
  }

  return headers;
}

/**
 * GET request to the backend API.
 */
export async function apiGet<T = any>(
  path: string,
  params?: Record<string, string>
): Promise<T> {
  const url = new URL(`${getBaseUrl()}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) {
        url.searchParams.set(k, v);
      }
    }
  }

  const headers = await buildHeaders();
  const res = await fetch(url.toString(), { headers });
  return handleResponse<T>(res);
}

/**
 * POST request to the backend API.
 */
export async function apiPost<T = any>(
  path: string,
  body?: unknown
): Promise<T> {
  const headers = await buildHeaders();
  const res = await fetch(`${getBaseUrl()}${path}`, {
    method: "POST",
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

// ── Convenience wrappers for known endpoints ────────────────────────────

export const api = {
  /** GET /accounts/dashboard */
  dashboard: () => apiGet<{ data: any[] }>("/accounts/dashboard"),

  /** GET /accounts */
  accounts: (params?: Record<string, string>) =>
    apiGet<{ data: any[]; total: number }>("/accounts", params),

  /** GET /accounts/:id */
  account: (id: string) => apiGet<{ data: any }>(`/accounts/${id}`),

  /** GET /signals */
  signals: (params?: Record<string, string>) =>
    apiGet<{ data: any[]; total: number }>("/signals", params),

  /** GET /signals/:id */
  signal: (id: string) => apiGet<{ data: any }>(`/signals/${id}`),

  /** GET /signals/:id/evidence */
  signalEvidence: (id: string) =>
    apiGet<{ data: any }>(`/signals/${id}/evidence`),

  /** GET /workspaces */
  workspaces: () => apiGet<{ data: any[] }>("/workspaces"),

  /** POST /workspaces */
  createWorkspace: (name: string) =>
    apiPost<{ data: any }>("/workspaces", { name }),

  /** GET /health */
  health: () => apiGet<{ status: string }>("/health"),
};
