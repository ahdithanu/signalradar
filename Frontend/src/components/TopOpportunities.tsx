import { companies, type Company } from "@/data/mockData";
import ScoreBadge from "./ScoreBadge";
import ProbabilityMeter from "./ProbabilityMeter";
import SignalBadge from "./SignalBadge";

interface TopOpportunitiesProps {
  onCompanyClick: (companyId: string) => void;
}

const TopOpportunities = ({ onCompanyClick }: TopOpportunitiesProps) => {
  const top = [...companies].sort((a, b) => b.opportunityScore - a.opportunityScore).slice(0, 3);

  return (
    <div className="px-4 py-5">
      <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Top Opportunities</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {top.map((c) => (
          <OpportunityCard key={c.id} company={c} onClick={() => onCompanyClick(c.id)} />
        ))}
      </div>
    </div>
  );
};

const OpportunityCard = ({ company: c, onClick }: { company: Company; onClick: () => void }) => (
  <button
    onClick={onClick}
    className="bg-card border rounded-md p-4 text-left hover:bg-surface-hover transition-colors cursor-pointer w-full"
  >
    <div className="flex items-start justify-between mb-2">
      <div>
        <h3 className="text-sm font-semibold text-foreground">{c.name}</h3>
        <p className="text-xs text-muted-foreground">{c.industry} · {c.employeeCount} employees</p>
      </div>
      <ScoreBadge score={c.opportunityScore} />
    </div>
    <ProbabilityMeter probability={c.opportunityProbability} />
    <div className="flex flex-wrap gap-1 mt-3">
      {c.signals.map((s, i) => (
        <SignalBadge key={i} type={s.type} />
      ))}
    </div>
    <p className="text-xs text-muted-foreground mt-3 line-clamp-2">{c.whyNow}</p>
  </button>
);

export default TopOpportunities;
