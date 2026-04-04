import { useState, useMemo } from "react";
import { type Company, type SignalType, type Status } from "@/data/mockData";
import ScoreBadge from "./ScoreBadge";
import ProbabilityMeter from "./ProbabilityMeter";
import SignalBadge from "./SignalBadge";
import { ArrowUpDown, Download, FileText, Filter, Search, X } from "lucide-react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import StatusSelect from "./StatusSelect";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";

interface DashboardTableProps {
  companies: Company[];
  onCompanyClick: (companyId: string) => void;
  statuses: Record<string, Status>;
  onStatusChange: (companyId: string, status: Status) => void;
}

const DashboardTable = ({ companies, onCompanyClick, statuses, onStatusChange }: DashboardTableProps) => {
  const [sortAsc, setSortAsc] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedIndustry, setSelectedIndustry] = useState<string>("");
  const [selectedSignal, setSelectedSignal] = useState<string>("");
  const [selectedFunding, setSelectedFunding] = useState<string>("");
  const [minScore, setMinScore] = useState(0);
  const [employeeRange, setEmployeeRange] = useState<string>("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState<Date | undefined>(undefined);
  const [dateTo, setDateTo] = useState<Date | undefined>(undefined);

  const industries = useMemo(() => [...new Set(companies.map(c => c.industry))], [companies]);
  const signalTypes = useMemo(() => [...new Set(companies.flatMap(c => c.signals.map(s => s.type)))] as SignalType[], [companies]);
  const fundingStages = useMemo(() => [...new Set(companies.map(c => c.fundingStage))], [companies]);

  const filtered = useMemo(() => {
    let data = [...companies];
    if (search) data = data.filter(c => c.name.toLowerCase().includes(search.toLowerCase()));
    if (selectedIndustry) data = data.filter(c => c.industry === selectedIndustry);
    if (selectedSignal) data = data.filter(c => c.signals.some(s => s.type === selectedSignal));
    if (selectedFunding) data = data.filter(c => c.fundingStage === selectedFunding);
    if (minScore > 0) data = data.filter(c => c.opportunityScore >= minScore);
    if (employeeRange) {
      const [min, max] = employeeRange.split("-").map(Number);
      data = data.filter(c => c.employeeCount >= min && (!max || c.employeeCount <= max));
    }
    if (dateFrom || dateTo) {
      data = data.filter(c => {
        const hasSignalInRange = c.signals.some(s => {
          const signalDate = new Date(s.date);
          if (dateFrom && signalDate < dateFrom) return false;
          if (dateTo && signalDate > dateTo) return false;
          return true;
        });
        return hasSignalInRange;
      });
    }
    data.sort((a, b) => sortAsc ? a.opportunityScore - b.opportunityScore : b.opportunityScore - a.opportunityScore);
    return data;
  }, [selectedIndustry, selectedSignal, selectedFunding, minScore, employeeRange, sortAsc, search, dateFrom, dateTo]);

  const hasFilters = selectedIndustry || selectedSignal || selectedFunding || minScore > 0 || employeeRange || dateFrom || dateTo;

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map(c => c.id)));
    }
  };

  const getExportData = () => {
    const data = selectedIds.size > 0 ? filtered.filter(c => selectedIds.has(c.id)) : filtered;
    return data;
  };

  const exportCSV = () => {
    const toExport = getExportData();
    if (!toExport.length) return;
    const headers = ["Company", "Industry", "Employees", "Funding Stage", "Score", "Probability", "Status", "Signals", "Why Now", "Buyer Persona", "Outreach Angle"];
    const rows = toExport.map(c => [
      c.name, c.industry, c.employeeCount, c.fundingStage,
      c.opportunityScore, `${Math.round(c.opportunityProbability * 100)}%`,
      statuses[c.id] || c.status,
      c.signals.map(s => s.description).join("; "),
      c.whyNow,
      c.recommendedBuyerPersona.join("; "),
      c.suggestedOutreachAngle,
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "signal-radar-export.csv";
    a.click();
    URL.revokeObjectURL(url);
    
    toast({
      title: "CSV Exported",
      description: `Successfully exported ${toExport.length} ${toExport.length === 1 ? 'company' : 'companies'} to CSV`,
    });
  };

  const exportPDF = () => {
    const toExport = getExportData();
    if (!toExport.length) return;
    const doc = new jsPDF({ orientation: "landscape" });
    doc.setFontSize(16);
    doc.text("Signal Radar — Export Report", 14, 18);
    doc.setFontSize(9);
    doc.text(`Generated ${new Date().toLocaleDateString()} · ${toExport.length} companies`, 14, 25);

    autoTable(doc, {
      startY: 30,
      head: [["Company", "Industry", "Emp.", "Stage", "Score", "Prob.", "Status", "Why Now"]],
      body: toExport.map(c => [
        c.name, c.industry, c.employeeCount, c.fundingStage,
        c.opportunityScore, `${Math.round(c.opportunityProbability * 100)}%`,
        statuses[c.id] || c.status,
        c.whyNow.slice(0, 80) + (c.whyNow.length > 80 ? "…" : ""),
      ]),
      styles: { fontSize: 7, cellPadding: 2 },
      headStyles: { fillColor: [30, 30, 30] },
    });

    doc.save("signal-radar-export.pdf");
    
    toast({
      title: "PDF Exported",
      description: `Successfully exported ${toExport.length} ${toExport.length === 1 ? 'company' : 'companies'} to PDF`,
    });
  };

  const clearFilters = () => {
    setSelectedIndustry("");
    setSelectedSignal("");
    setSelectedFunding("");
    setMinScore(0);
    setEmployeeRange("");
    setDateFrom(undefined);
    setDateTo(undefined);
  };

  return (
    <div className="px-4 pb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Opportunities Dashboard</h2>
          <div className="relative">
            <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search companies..."
              className="text-xs border rounded pl-6 pr-2 py-1.5 bg-background text-foreground w-48 focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded border transition-colors ${filtersOpen ? "bg-primary text-primary-foreground border-primary" : "bg-card text-foreground border-border hover:bg-surface-hover"}`}
          >
            <Filter size={12} />
            Filters
            {hasFilters && <span className="w-1.5 h-1.5 rounded-full bg-success" />}
          </button>
          <button
            onClick={exportCSV}
            className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded border bg-card text-foreground border-border hover:bg-surface-hover transition-colors"
            title={selectedIds.size > 0 ? `Export ${selectedIds.size} selected` : "Export all filtered"}
          >
            <Download size={12} />
            CSV {selectedIds.size > 0 ? `(${selectedIds.size})` : `(${filtered.length})`}
          </button>
          <button
            onClick={exportPDF}
            className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded border bg-card text-foreground border-border hover:bg-surface-hover transition-colors"
            title={selectedIds.size > 0 ? `Export ${selectedIds.size} selected` : "Export all filtered"}
          >
            <FileText size={12} />
            PDF {selectedIds.size > 0 ? `(${selectedIds.size})` : `(${filtered.length})`}
          </button>
        </div>
      </div>

      {filtersOpen && (
        <div className="bg-card border rounded-md p-3 mb-3 flex flex-wrap items-end gap-3">
          <FilterSelect label="Industry" value={selectedIndustry} onChange={setSelectedIndustry} options={industries} />
          <FilterSelect label="Signal Type" value={selectedSignal} onChange={setSelectedSignal} options={signalTypes.map(s => s)} displayMap={{ funding: "Funding", hiring: "Hiring", growth: "Growth", product_launch: "Product Launch", positioning_shift: "Positioning Shift", partnership: "Partnership" }} />
          <FilterSelect label="Funding Stage" value={selectedFunding} onChange={setSelectedFunding} options={fundingStages} />
          <FilterSelect label="Employees" value={employeeRange} onChange={setEmployeeRange} options={["1-50", "51-100", "101-200", "201-500"]} />
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Min Score</label>
            <input
              type="number"
              value={minScore || ""}
              onChange={e => setMinScore(Number(e.target.value))}
              placeholder="0"
              className="w-20 text-xs border rounded px-2 py-1.5 bg-background text-foreground"
            />
          </div>
          <DatePicker label="From" date={dateFrom} onSelect={setDateFrom} />
          <DatePicker label="To" date={dateTo} onSelect={setDateTo} />
          {hasFilters && (
            <button onClick={clearFilters} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
              <X size={12} /> Clear
            </button>
          )}
        </div>
      )}

      <div className="bg-card border rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="w-8 px-3 py-2">
                  <input type="checkbox" checked={selectedIds.size === filtered.length && filtered.length > 0} onChange={toggleAll} className="rounded" />
                </th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground">Company</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground">Industry</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground w-20">Emp.</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground cursor-pointer select-none w-20" onClick={() => setSortAsc(!sortAsc)}>
                  <span className="inline-flex items-center gap-1">Score <ArrowUpDown size={10} /></span>
                </th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground w-24">Prob.</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground">Signals</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground max-w-[200px]">Why Now</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground">Buyer</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-muted-foreground w-24">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <tr key={c.id} onClick={() => onCompanyClick(c.id)} className="border-b last:border-0 hover:bg-surface-hover cursor-pointer transition-colors">
                  <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                    <input type="checkbox" checked={selectedIds.has(c.id)} onChange={() => toggleSelect(c.id)} className="rounded" />
                  </td>
                  <td className="px-3 py-2.5 font-medium text-foreground whitespace-nowrap">{c.name}</td>
                  <td className="px-3 py-2.5 text-muted-foreground whitespace-nowrap">{c.industry}</td>
                  <td className="px-3 py-2.5 font-mono text-xs text-muted-foreground">{c.employeeCount}</td>
                  <td className="px-3 py-2.5"><ScoreBadge score={c.opportunityScore} /></td>
                  <td className="px-3 py-2.5"><ProbabilityMeter probability={c.opportunityProbability} /></td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-wrap gap-1">{c.signals.map((s, i) => <SignalBadge key={i} type={s.type} />)}</div>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground max-w-[200px] truncate">{c.whyNow}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground whitespace-nowrap">{c.recommendedBuyerPersona[0]}</td>
                  <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                    <StatusSelect status={statuses[c.id] || c.status} onChange={(s) => {
                      onStatusChange(c.id, s);
                      toast({
                        title: "Status Updated",
                        description: `${c.name} status changed to ${s}`,
                      });
                    }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};


const FilterSelect = ({ label, value, onChange, options, displayMap }: { label: string; value: string; onChange: (v: string) => void; options: string[]; displayMap?: Record<string, string> }) => (
  <div>
    <label className="block text-xs text-muted-foreground mb-1">{label}</label>
    <select value={value} onChange={e => onChange(e.target.value)} className="text-xs border rounded px-2 py-1.5 bg-background text-foreground min-w-[120px]">
      <option value="">All</option>
      {options.map(o => <option key={o} value={o}>{displayMap?.[o] || o}</option>)}
    </select>
  </div>
);

const DatePicker = ({ label, date, onSelect }: { label: string; date: Date | undefined; onSelect: (date: Date | undefined) => void }) => (
  <div>
    <label className="block text-xs text-muted-foreground mb-1">{label}</label>
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "h-8 w-[120px] justify-start text-left text-xs font-normal px-2 py-1.5",
            !date && "text-muted-foreground"
          )}
        >
          {date ? format(date, "PP") : <span>Pick date</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={date}
          onSelect={onSelect}
          initialFocus
          className={cn("p-3 pointer-events-auto")}
        />
      </PopoverContent>
    </Popover>
  </div>
);

export default DashboardTable;
