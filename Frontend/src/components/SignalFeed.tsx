import { signalFeedItems } from "@/data/mockData";
import SignalBadge from "./SignalBadge";

interface SignalFeedProps {
  onCompanyClick: (companyId: string) => void;
}

const SignalFeed = ({ onCompanyClick }: SignalFeedProps) => {
  const items = [...signalFeedItems, ...signalFeedItems]; // duplicate for seamless loop

  return (
    <div className="border-b bg-card overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b">
        <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Live Signal Feed</span>
      </div>
      <div className="overflow-hidden">
        <div className="flex animate-ticker hover:[animation-play-state:paused]">
          {items.map((item, i) => (
            <button
              key={i}
              onClick={() => onCompanyClick(item.companyId)}
              className="flex-shrink-0 flex items-center gap-3 px-4 py-2.5 border-r hover:bg-surface-hover transition-colors cursor-pointer"
            >
              <SignalBadge type={item.signal.type} />
              <span className="text-sm font-medium text-foreground whitespace-nowrap">{item.companyName}</span>
              <span className="text-xs text-muted-foreground whitespace-nowrap max-w-[200px] truncate">{item.signal.description}</span>
              <span className="text-xs text-muted-foreground font-mono whitespace-nowrap">{item.signal.daysAgo}d ago</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SignalFeed;
