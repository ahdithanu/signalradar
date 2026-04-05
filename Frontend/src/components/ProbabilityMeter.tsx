interface ProbabilityMeterProps {
  probability: number;
}

const ProbabilityMeter = ({ probability }: ProbabilityMeterProps) => {
  const pct = Math.round(probability * 100);
  const color = pct >= 75 ? "bg-success" : pct >= 55 ? "bg-primary" : "bg-muted-foreground";

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-muted-foreground">{pct}%</span>
    </div>
  );
};

export default ProbabilityMeter;
