/**
 * WorkspaceGate — renders children only when a valid workspace is active.
 *
 * Handles three blocking states:
 *   1. loading       → spinner
 *   2. needsCreation → creates first workspace automatically
 *   3. needsSelection → shows WorkspaceSelector
 *
 * Only passes through to children when activeWorkspaceId is set.
 */

import { useEffect, useRef, useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { useAuth } from "./AuthProvider";
import WorkspaceSelector from "@/components/WorkspaceSelector";
import { Loader2 } from "lucide-react";

export function WorkspaceGate({ children }: { children: React.ReactNode }) {
  const { loading, needsSelection, needsCreation, activeWorkspaceId, refetchWorkspaces } =
    useWorkspace();
  const { accessToken } = useAuth();
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const attemptedRef = useRef(false);

  // ── Auto-create workspace for new users with 0 workspaces ────────────
  useEffect(() => {
    if (!needsCreation || !accessToken || creating || attemptedRef.current) return;

    attemptedRef.current = true;
    setCreating(true);
    setCreateError(null);

    const apiUrl = import.meta.env.VITE_API_URL || "";
    fetch(`${apiUrl}/workspaces`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ name: "My Workspace" }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Failed to create workspace: ${res.status}`);
        }
        // Workspace created — re-fetch so WorkspaceProvider picks it up
        // and auto-selects it (single workspace → auto-select)
        await refetchWorkspaces();
      })
      .catch((err) => {
        setCreateError(err.message || "Failed to create workspace");
        if (import.meta.env.DEV) {
          console.error("Workspace creation failed:", err);
        }
      })
      .finally(() => {
        setCreating(false);
      });
  }, [needsCreation, accessToken, creating, refetchWorkspaces]);

  // Reset attempt flag when user changes (e.g., logout → login as different user)
  useEffect(() => {
    if (!needsCreation) {
      attemptedRef.current = false;
    }
  }, [needsCreation]);

  // ── Loading states ───────────────────────────────────────────────────

  if (loading || creating) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-3">
        <Loader2 size={24} className="animate-spin text-muted-foreground" />
        {creating && (
          <p className="text-xs text-muted-foreground">Setting up your workspace...</p>
        )}
      </div>
    );
  }

  // ── Error creating workspace ─────────────────────────────────────────

  if (createError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-sm border rounded-lg bg-card p-6 text-center">
          <p className="text-sm text-destructive mb-3">{createError}</p>
          <button
            onClick={() => {
              attemptedRef.current = false;
              setCreateError(null);
            }}
            className="px-4 py-2 text-sm rounded bg-primary text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  // ── Needs selection (2+ workspaces, none active) ─────────────────────

  if (needsSelection) {
    return <WorkspaceSelector />;
  }

  // ── No active workspace but also not loading/creating/selecting ──────
  // This can happen briefly during re-fetch after a workspace reset.

  if (!activeWorkspaceId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 size={24} className="animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ── Active workspace set — render app content ────────────────────────

  return <>{children}</>;
}
