import { companies, type Status } from "@/data/mockData";
import StatusSelect from "./StatusSelect";
import ScoreBadge from "./ScoreBadge";
import ProbabilityMeter from "./ProbabilityMeter";
import SignalBadge from "./SignalBadge";
import { X, Globe, Users, ChevronDown, ChevronUp, Brain, Send } from "lucide-react";
import { useState } from "react";
import { Textarea } from "./ui/textarea";
import { toast } from "@/hooks/use-toast";

interface CompanyDrawerProps {
  companyId: string | null;
  status: Status;
  onStatusChange: (companyId: string, status: Status) => void;
  onClose: () => void;
}

const CompanyDrawer = ({ companyId, status, onStatusChange, onClose }: CompanyDrawerProps) => {
  const [intelOpen, setIntelOpen] = useState(false);
  const [notes, setNotes] = useState<Record<string, { text: string; timestamp: string }[]>>({});
  const [noteInput, setNoteInput] = useState("");
  const company = companies.find(c => c.id === companyId);

  if (!company) return null;

  return (
    <>
      <div className="fixed inset-0 bg-foreground/10 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-[420px] bg-card border-l z-50 overflow-y-auto animate-slide-in-right">
        <div className="sticky top-0 bg-card border-b px-4 py-3 flex items-center justify-between z-10">
          <h2 className="text-sm font-semibold text-foreground">{company.name}</h2>
          <div className="flex items-center gap-2">
            <StatusSelect status={status} onChange={(s) => onStatusChange(company.id, s)} />
            <button onClick={onClose} className="p-1 hover:bg-surface-hover rounded transition-colors">
              <X size={16} className="text-muted-foreground" />
            </button>
          </div>
        </div>

        <div className="p-4 space-y-5">
          {/* Overview */}
          <Section title="Company Overview">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <InfoRow icon={<Globe size={12} />} label="Website" value={company.website} />
              <InfoRow label="Industry" value={company.industry} />
              <InfoRow icon={<Users size={12} />} label="Employees" value={String(company.employeeCount)} />
              <InfoRow label="Funding" value={company.fundingStage} />
            </div>
          </Section>

          {/* Score */}
          <Section title="Opportunity Score">
            <div className="flex items-center gap-3 mb-3">
              <ScoreBadge score={company.opportunityScore} />
              <ProbabilityMeter probability={company.opportunityProbability} />
            </div>
          </Section>

          {/* Signals */}
          <Section title="Signal Breakdown">
            <div className="space-y-2">
              {company.signals.map((s, i) => (
                <div key={i} className="flex items-start justify-between border rounded p-2.5">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <SignalBadge type={s.type} />
                      <span className="text-xs text-muted-foreground font-mono">{s.daysAgo}d ago</span>
                    </div>
                    <p className="text-xs text-foreground">{s.description}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{s.interpretation}</p>
                  </div>
                  <span className="text-xs font-mono font-semibold text-success ml-2">+{s.scoreContribution}</span>
                </div>
              ))}
              <div className="flex justify-between items-center pt-2 border-t">
                <span className="text-xs font-medium text-muted-foreground">Total Score</span>
                <span className="font-mono text-sm font-semibold text-foreground">{company.signals.reduce((sum, s) => sum + s.scoreContribution, 0)}</span>
              </div>
            </div>
          </Section>

          {/* Why Now */}
          <Section title="Why Now">
            <p className="text-xs text-foreground leading-relaxed">{company.whyNow}</p>
          </Section>

          {/* Outreach */}
          <Section title="Suggested Outreach Strategy">
            <div className="mb-2">
              <span className="text-xs text-muted-foreground">Recommended Buyer Personas</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {company.recommendedBuyerPersona.map((p, i) => (
                  <span key={i} className="text-xs bg-muted text-foreground px-2 py-0.5 rounded">{p}</span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Outreach Angle</span>
              <p className="text-xs text-foreground mt-0.5">{company.suggestedOutreachAngle}</p>
            </div>
          </Section>

          {/* Notes */}
          <Section title="Notes & Comments">
            <div className="space-y-2 mb-3">
              {(notes[company.id] || []).map((note, i) => (
                <div key={i} className="border rounded p-2.5 bg-muted/30">
                  <p className="text-xs text-foreground">{note.text}</p>
                  <span className="text-[10px] text-muted-foreground font-mono mt-1 block">{note.timestamp}</span>
                </div>
              ))}
              {!(notes[company.id] || []).length && (
                <p className="text-xs text-muted-foreground italic">No notes yet.</p>
              )}
            </div>
            <div className="flex gap-2">
              <Textarea
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
                placeholder="Add a note..."
                className="min-h-[60px] text-xs resize-none"
              />
              <button
                onClick={() => {
                  if (!noteInput.trim()) return;
                  setNotes(prev => ({
                    ...prev,
                    [company.id]: [
                      ...(prev[company.id] || []),
                      { text: noteInput.trim(), timestamp: new Date().toLocaleString() },
                    ],
                  }));
                  setNoteInput("");
                  toast({ title: "Note added", description: `Note saved for ${company.name}` });
                }}
                className="self-end p-2 rounded bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
              >
                <Send size={14} />
              </button>
            </div>
          </Section>

          {/* Strategic Intelligence */}
          <div className="border rounded-md overflow-hidden">
            <button
              onClick={() => setIntelOpen(!intelOpen)}
              className="w-full flex items-center justify-between px-3 py-2.5 bg-intelligence-bg hover:opacity-90 transition-opacity"
            >
              <div className="flex items-center gap-2">
                <Brain size={14} className="text-intelligence" />
                <span className="text-xs font-semibold text-intelligence">Strategic Intelligence</span>
              </div>
              {intelOpen ? <ChevronUp size={14} className="text-intelligence" /> : <ChevronDown size={14} className="text-intelligence" />}
            </button>
            {intelOpen && (
              <div className="bg-intelligence-bg p-3 border-t border-intelligence/10 space-y-2">
                <IntelRow label="Strategic Theme" value={company.strategicIntelligence.strategicTheme} />
                <IntelRow label="Management Tone" value={company.strategicIntelligence.managementTone} />
                <IntelRow label="Commercial Pressure" value={company.strategicIntelligence.commercialPressureScore} />
                <IntelRow label="Narrative Shift" value={company.strategicIntelligence.narrativeShift} />
                <IntelRow label="GTM Relevance" value={company.strategicIntelligence.suggestedGTMRelevance} />
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div>
    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">{title}</h3>
    {children}
  </div>
);

const InfoRow = ({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) => (
  <div className="flex items-center gap-1.5">
    {icon && <span className="text-muted-foreground">{icon}</span>}
    <span className="text-muted-foreground">{label}:</span>
    <span className="text-foreground font-medium">{value}</span>
  </div>
);

const IntelRow = ({ label, value }: { label: string; value: string }) => (
  <div>
    <span className="text-xs text-intelligence/70">{label}</span>
    <p className="text-xs text-foreground capitalize">{value}</p>
  </div>
);

export default CompanyDrawer;
