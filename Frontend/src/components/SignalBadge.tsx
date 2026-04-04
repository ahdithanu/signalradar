import { DollarSign, Users, TrendingUp, Rocket, Crosshair, Handshake } from "lucide-react";
import type { SignalType } from "@/data/mockData";

interface SignalBadgeProps {
  type: SignalType;
  size?: "sm" | "md";
}

const config: Record<SignalType, { label: string; icon: typeof DollarSign; className: string }> = {
  funding: { label: "Funding", icon: DollarSign, className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  hiring: { label: "Hiring", icon: Users, className: "bg-blue-50 text-blue-700 border-blue-200" },
  growth: { label: "Growth", icon: TrendingUp, className: "bg-amber-50 text-amber-700 border-amber-200" },
  product_launch: { label: "Launch", icon: Rocket, className: "bg-purple-50 text-purple-700 border-purple-200" },
  positioning_shift: { label: "Positioning", icon: Crosshair, className: "bg-rose-50 text-rose-700 border-rose-200" },
  partnership: { label: "Partnership", icon: Handshake, className: "bg-cyan-50 text-cyan-700 border-cyan-200" },
};

const SignalBadge = ({ type, size = "sm" }: SignalBadgeProps) => {
  const entry = config[type];
  if (!entry) return <span className="text-xs text-muted-foreground">{type}</span>;
  const { label, icon: Icon, className } = entry;
  const sizeClass = size === "sm" ? "text-xs px-1.5 py-0.5 gap-1" : "text-sm px-2 py-1 gap-1.5";

  return (
    <span className={`inline-flex items-center rounded border font-medium ${className} ${sizeClass}`}>
      <Icon size={size === "sm" ? 10 : 12} />
      {label}
    </span>
  );
};

export default SignalBadge;
