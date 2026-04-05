/**
 * WorkspaceProvider — SINGLE SOURCE OF TRUTH for workspace state.
 *
 * Ownership rules:
 *   - Only this module writes to localStorage for workspace ID.
 *   - Only this module sets activeWorkspaceId in React state.
 *   - client.ts reads localStorage (read-only) and emits events here on errors.
 *   - All workspace resets flow through resetWorkspace().
 *
 * Two named write paths (NO direct setActiveWorkspaceId calls outside these):
 *
 *   hydrateWorkspaceId(id)  — restores a previously-persisted value into React state.
 *                             localStorage is the source of truth. No localStorage write.
 *                             Used during: mount initializer, post-fetch validation.
 *
 *   mutateWorkspaceId(id)   — user or system changes the active workspace.
 *                             Writes to BOTH localStorage and React state atomically.
 *                             Used during: selectWorkspace, clearWorkspace, resetWorkspace,
 *                             auto-select (single workspace), logout cleanup.
 *
 * State machine:
 *   LOADING → FETCHED(0 workspaces) → NEEDS_CREATION
 *   LOADING → FETCHED(1 workspace)  → AUTO_SELECTED → READY
 *   LOADING → FETCHED(2+ workspaces, valid stored) → READY
 *   LOADING → FETCHED(2+ workspaces, no valid stored) → NEEDS_SELECTION
 *   READY   → ERROR(400/403) → resetWorkspace() → re-fetch → one of the above
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { useAuth } from "./AuthProvider";
import { onWorkspaceError, type WorkspaceErrorReason } from "@/lib/workspace-events";
import { clearQueryCache } from "@/lib/query-client";

const STORAGE_KEY = "signal_radar_workspace_id";

export interface WorkspaceInfo {
  id: string;
  name: string;
  role: string;
}

export interface WorkspaceState {
  workspaces: WorkspaceInfo[];
  activeWorkspaceId: string | null;
  loading: boolean;
  /** True when user has 2+ workspaces and hasn't picked one. */
  needsSelection: boolean;
  /** True when user has 0 workspaces and needs one created. */
  needsCreation: boolean;
  selectWorkspace: (id: string) => void;
  clearWorkspace: () => void;
  resetWorkspace: (reason: string) => void;
  refetchWorkspaces: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceState | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { accessToken, user } = useAuth();
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);

  // ── Hydration: mount reads from localStorage, no write ──────────────
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY)
  );

  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  // Track whether we've already been reset by an error event to prevent loops
  const resetInFlightRef = useRef(false);

  // ── Two named write paths ───────────────────────────────────────────

  /**
   * hydrateWorkspaceId — restores a value that ALREADY EXISTS in localStorage
   * into React state. Does NOT write to localStorage because the value is
   * already there. Used when we need to sync React state to match storage
   * after validating the stored ID against the fetched workspace list.
   *
   * Passing null means: the stored value was invalid, clear React state
   * but also clear localStorage (because the stored value is garbage).
   */
  const hydrateWorkspaceId = useCallback((id: string | null) => {
    if (id === null) {
      // Stored value was invalid — clean up localStorage too
      localStorage.removeItem(STORAGE_KEY);
    }
    // If id is non-null, localStorage already has it (we read it from there).
    // No write needed. Just sync React state.
    setActiveWorkspaceId(id);
  }, []);

  /**
   * mutateWorkspaceId — user or system initiates a workspace change.
   * Writes to BOTH localStorage and React state atomically.
   * This is the path for: selectWorkspace, clearWorkspace, resetWorkspace,
   * auto-select (single workspace), logout cleanup.
   */
  const mutateWorkspaceId = useCallback((id: string | null) => {
    if (id) {
      localStorage.setItem(STORAGE_KEY, id);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    setActiveWorkspaceId(id);
  }, []);

  // ── Fetch workspaces from backend ────────────────────────────────────

  const fetchWorkspaces = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    resetInFlightRef.current = false;

    try {
      const apiUrl = import.meta.env.VITE_API_URL || "";
      const res = await fetch(`${apiUrl}/workspaces`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          // No X-Workspace-Id — this endpoint uses AuthenticatedUser, not WorkspaceContext
        },
      });

      if (!res.ok) {
        if (import.meta.env.DEV) {
          console.warn("Failed to fetch workspaces:", res.status);
        }
        setWorkspaces([]);
        setFetched(true);
        return;
      }

      const json = await res.json();
      const ws: WorkspaceInfo[] = (json.data || []).map((w: any) => ({
        id: w.id,
        name: w.name,
        role: w.role,
      }));
      setWorkspaces(ws);
      setFetched(true);

      // ── Resolve active workspace after fetch ────────────────────────
      const storedId = localStorage.getItem(STORAGE_KEY);
      const storedIsValid = storedId && ws.some((w) => w.id === storedId);

      if (storedIsValid) {
        // Value exists in localStorage and is valid — HYDRATE (no storage write)
        hydrateWorkspaceId(storedId);
      } else if (ws.length === 1) {
        // No valid stored ID, but exactly one workspace — MUTATE (new value)
        mutateWorkspaceId(ws[0].id);
      } else {
        // 0 or 2+ workspaces with no valid stored ID — HYDRATE null (cleanup)
        hydrateWorkspaceId(null);
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("Workspace fetch error:", err);
      }
      setWorkspaces([]);
      setFetched(true);
    } finally {
      setLoading(false);
    }
  }, [accessToken, hydrateWorkspaceId, mutateWorkspaceId]);

  // ── Fetch on login, clear on logout ──────────────────────────────────

  useEffect(() => {
    if (user && accessToken && !fetched) {
      fetchWorkspaces();
    }
    if (!user) {
      // Logout — MUTATE to null (intentional state change, must clear storage)
      setWorkspaces([]);
      mutateWorkspaceId(null);
      setFetched(false);
    }
  }, [user, accessToken, fetched, fetchWorkspaces, mutateWorkspaceId]);

  // ── Public actions ───────────────────────────────────────────────────

  /** User picks a workspace from the selector. MUTATE. */
  const selectWorkspace = useCallback(
    (id: string) => {
      mutateWorkspaceId(id);
    },
    [mutateWorkspaceId]
  );

  /** User clicks "switch workspace" in header. MUTATE to null. */
  const clearWorkspace = useCallback(() => {
    mutateWorkspaceId(null);
  }, [mutateWorkspaceId]);

  /**
   * resetWorkspace — called when a workspace error event is received.
   * MUTATE to null + clear query cache + trigger re-fetch.
   */
  const resetWorkspace = useCallback(
    (reason: string) => {
      // Prevent cascading resets from multiple failed queries
      if (resetInFlightRef.current) return;
      resetInFlightRef.current = true;

      if (import.meta.env.DEV) {
        console.warn("Workspace reset triggered:", reason);
      }

      // Clear cached data from the old workspace context
      clearQueryCache();

      // MUTATE to null — intentional state change, must clear storage
      mutateWorkspaceId(null);

      // Trigger re-fetch on next render cycle
      setFetched(false);
    },
    [mutateWorkspaceId]
  );

  // ── Listen for workspace error events from client.ts ─────────────────

  useEffect(() => {
    const unsubscribe = onWorkspaceError(
      (reason: WorkspaceErrorReason, detail: string) => {
        resetWorkspace(`${reason}: ${detail}`);
      }
    );
    return unsubscribe;
  }, [resetWorkspace]);

  // ── Derived state ────────────────────────────────────────────────────

  const needsSelection = fetched && workspaces.length > 1 && !activeWorkspaceId;
  const needsCreation = fetched && workspaces.length === 0;

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        activeWorkspaceId,
        loading,
        needsSelection,
        needsCreation,
        selectWorkspace,
        clearWorkspace,
        resetWorkspace,
        refetchWorkspaces: fetchWorkspaces,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceState {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return ctx;
}
