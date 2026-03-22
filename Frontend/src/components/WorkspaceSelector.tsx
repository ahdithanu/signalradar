/**
 * Workspace selector — shown when user belongs to multiple workspaces
 * and hasn't selected one yet.
 */

import { useWorkspace } from "@/auth/WorkspaceProvider";
import { Radar, Building2 } from "lucide-react";

const WorkspaceSelector = () => {
  const { workspaces, selectWorkspace } = useWorkspace();

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Radar size={24} className="text-primary" />
          <span className="text-lg font-semibold text-foreground">Signal Radar</span>
        </div>

        <div className="border rounded-lg bg-card p-6">
          <h1 className="text-base font-semibold text-foreground mb-1">
            Select workspace
          </h1>
          <p className="text-xs text-muted-foreground mb-4">
            You belong to multiple workspaces. Choose one to continue.
          </p>

          <div className="space-y-2">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => selectWorkspace(ws.id)}
                className="w-full flex items-center gap-3 p-3 rounded border text-left hover:bg-secondary/50 transition-colors"
              >
                <Building2 size={16} className="text-muted-foreground shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {ws.name}
                  </p>
                  <p className="text-xs text-muted-foreground">{ws.role}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceSelector;
