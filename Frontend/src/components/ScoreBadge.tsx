interface ScoreBadgeProps {
  score: number;
}

const ScoreBadge = ({ score }: ScoreBadgeProps) => {
  const color = score >= 80 ? "bg-success text-success-foreground" 
    : score >= 60 ? "bg-primary text-primary-foreground" 
    : "bg-muted text-muted-foreground";

  return (
    <span className={`font-mono text-sm font-semibold px-2 py-0.5 rounded ${color}`}>
      {score}
    </span>
  );
};

export default ScoreBadge;
