/**
 * Tests for the workspace event bus (workspace-events.ts).
 *
 * Validates:
 *   - single listener enforcement
 *   - emit with no listener (no crash)
 *   - cleanup
 *   - listener replacement
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  emitWorkspaceError,
  onWorkspaceError,
  type WorkspaceErrorReason,
} from "@/lib/workspace-events";

describe("workspace-events", () => {
  let handler: ReturnType<typeof vi.fn>;
  let cleanup: () => void;

  beforeEach(() => {
    handler = vi.fn();
    // Ensure no leftover listener from previous test
    cleanup = onWorkspaceError(handler);
  });

  afterEach(() => {
    cleanup();
  });

  it("delivers events to the registered listener", () => {
    emitWorkspaceError("workspace_required", "missing workspace header");

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith(
      "workspace_required",
      "missing workspace header"
    );
  });

  it("does not crash when emitting with no listener", () => {
    cleanup(); // Remove listener
    expect(() => {
      emitWorkspaceError("workspace_forbidden", "not a member");
    }).not.toThrow();
  });

  it("unsubscribe prevents further delivery", () => {
    cleanup();
    emitWorkspaceError("workspace_required", "test");
    expect(handler).not.toHaveBeenCalled();
  });

  it("replaces previous listener when a new one is registered", () => {
    const handler2 = vi.fn();
    const cleanup2 = onWorkspaceError(handler2);

    emitWorkspaceError("workspace_forbidden", "replaced");

    expect(handler).not.toHaveBeenCalled();
    expect(handler2).toHaveBeenCalledTimes(1);
    expect(handler2).toHaveBeenCalledWith("workspace_forbidden", "replaced");

    cleanup2();
  });

  it("delivers all three event types correctly", () => {
    const reasons: WorkspaceErrorReason[] = [
      "workspace_required",
      "workspace_forbidden",
      "workspace_invalid",
    ];

    for (const reason of reasons) {
      emitWorkspaceError(reason, `detail-${reason}`);
    }

    expect(handler).toHaveBeenCalledTimes(3);
    expect(handler.mock.calls[0]).toEqual(["workspace_required", "detail-workspace_required"]);
    expect(handler.mock.calls[1]).toEqual(["workspace_forbidden", "detail-workspace_forbidden"]);
    expect(handler.mock.calls[2]).toEqual(["workspace_invalid", "detail-workspace_invalid"]);
  });

  it("unsubscribing handler A does not affect handler B registered after", () => {
    // cleanup removes handler A (from beforeEach)
    cleanup();

    const handlerB = vi.fn();
    const cleanupB = onWorkspaceError(handlerB);

    emitWorkspaceError("workspace_required", "test");
    expect(handler).not.toHaveBeenCalled();
    expect(handlerB).toHaveBeenCalledTimes(1);

    cleanupB();
  });

  it("unsubscribing an already-replaced handler does not remove the current one", () => {
    // handler is currently registered (from beforeEach)
    const handler2 = vi.fn();
    const cleanup2 = onWorkspaceError(handler2); // replaces handler

    // Now call the OLD cleanup — should NOT remove handler2
    cleanup();

    emitWorkspaceError("workspace_required", "still works");
    expect(handler2).toHaveBeenCalledTimes(1);

    cleanup2();
  });
});
