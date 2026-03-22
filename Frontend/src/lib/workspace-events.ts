/**
 * Workspace event bus — decouples API client from WorkspaceProvider.
 *
 * client.ts emits events here.
 * WorkspaceProvider subscribes and owns all state transitions.
 *
 * This exists because client.ts is a plain module (no React context access)
 * but needs to signal workspace errors to WorkspaceProvider.
 */

export type WorkspaceErrorReason =
  | "workspace_required"   // 400 — missing or ambiguous workspace
  | "workspace_forbidden"  // 403 — not a member of the specified workspace
  | "workspace_invalid";   // workspace ID failed validation

export type WorkspaceEventHandler = (reason: WorkspaceErrorReason, detail: string) => void;

let listener: WorkspaceEventHandler | null = null;

/**
 * Called by WorkspaceProvider on mount. Only one listener at a time.
 */
export function onWorkspaceError(handler: WorkspaceEventHandler): () => void {
  listener = handler;
  return () => {
    if (listener === handler) {
      listener = null;
    }
  };
}

/**
 * Called by client.ts when a workspace-related error occurs.
 * If no listener is registered, the event is silently dropped
 * (the thrown ApiRequestError still propagates to the caller).
 */
export function emitWorkspaceError(reason: WorkspaceErrorReason, detail: string): void {
  if (listener) {
    listener(reason, detail);
  }
}
