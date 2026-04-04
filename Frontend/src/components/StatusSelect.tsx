import { useState } from "react";
import type { Status } from "@/data/mockData";

const allStatuses: Status[] = ["New", "Reviewing", "Ready for Outreach", "Dismissed"];

const styles: Record<Status, string> = {
  "New": "bg-blue-50 text-blue-700 border-blue-200",
  "Reviewing": "bg-amber-50 text-amber-700 border-amber-200",
  "Ready for Outreach": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "Dismissed": "bg-muted text-muted-foreground border-border",
};

interface StatusSelectProps {
  status: Status;
  onChange: (status: Status) => void;
}

const StatusSelect = ({ status, onChange }: StatusSelectProps) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className={`text-xs font-medium px-1.5 py-0.5 rounded border cursor-pointer hover:opacity-80 transition-opacity ${styles[status]}`}
      >
        {status}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={(e) => { e.stopPropagation(); setOpen(false); }} />
          <div className="absolute right-0 top-full mt-1 bg-card border rounded-md shadow-md z-40 min-w-[160px] py-1">
            {allStatuses.map(s => (
              <button
                key={s}
                onClick={(e) => { e.stopPropagation(); onChange(s); setOpen(false); }}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-surface-hover transition-colors ${s === status ? "font-semibold" : ""}`}
              >
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${s === "New" ? "bg-blue-500" : s === "Reviewing" ? "bg-amber-500" : s === "Ready for Outreach" ? "bg-emerald-500" : "bg-muted-foreground"}`} />
                {s}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default StatusSelect;
