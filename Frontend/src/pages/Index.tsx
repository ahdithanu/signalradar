import { useState, useMemo } from "react";
import SignalFeed from "@/components/SignalFeed";
import TopOpportunities from "@/components/TopOpportunities";
import DashboardTable from "@/components/DashboardTable";
import CompanyDrawer from "@/components/CompanyDrawer";
import AppHeader from "@/components/AppHeader";
import { useDashboard } from "@/hooks/useDashboard";
import type { Status } from "@/data/mockData";
import { Loader2, AlertCircle, Inbox } from "lucide-react";

const Index = () => {
  const { data: companies, isLoading, isError, error } = useDashboard();
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<Record<string, Status>>({});

  // Initialize statuses from backend data when it loads
  const effectiveStatuses = useMemo(() => {
    if (!companies) return statuses;
    const fromBackend: Record<string, Status> = {};
    for (const c of companies) {
      fromBackend[c.id] = (statuses[c.id] ?? c.status) as Status;
    }
    return fromBackend;
  }, [companies, statuses]);

  const handleStatusChange = (companyId: string, status: Status) => {
    setStatuses(prev => ({ ...prev, [companyId]: status }));
  };

  const signalFeedItems = useMemo(() => {
    if (!companies) return [];
    return companies
      .flatMap((company) =>
        company.signals.map((signal) => ({
          companyId: company.id,
          companyName: company.name,
          signal,
        }))
      )
      .sort((a, b) => a.signal.daysAgo - b.signal.daysAgo);
  }, [companies]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <div className="flex flex-col items-center justify-center py-32 text-muted-foreground">
          <Loader2 size={24} className="animate-spin mb-3" />
          <p className="text-sm">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <div className="flex flex-col items-center justify-center py-32 text-destructive">
          <AlertCircle size={24} className="mb-3" />
          <p className="text-sm font-medium">Failed to load dashboard</p>
          <p className="text-xs text-muted-foreground mt-1">{error?.message || "Unknown error"}</p>
        </div>
      </div>
    );
  }

  if (!companies || companies.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <div className="flex flex-col items-center justify-center py-32 text-muted-foreground">
          <Inbox size={24} className="mb-3" />
          <p className="text-sm font-medium">No accounts found</p>
          <p className="text-xs mt-1">Add accounts to start tracking signals.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      <SignalFeed items={signalFeedItems} onCompanyClick={setSelectedCompanyId} />
      <TopOpportunities companies={companies} onCompanyClick={setSelectedCompanyId} />
      <div className="border-t mx-4" />
      <DashboardTable companies={companies} onCompanyClick={setSelectedCompanyId} statuses={effectiveStatuses} onStatusChange={handleStatusChange} />

      {selectedCompanyId && (
        <CompanyDrawer
          companyId={selectedCompanyId}
          companies={companies}
          status={effectiveStatuses[selectedCompanyId]}
          onStatusChange={handleStatusChange}
          onClose={() => setSelectedCompanyId(null)}
        />
      )}
    </div>
  );
};

export default Index;
