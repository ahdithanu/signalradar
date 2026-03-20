import { useState } from "react";
import SignalFeed from "@/components/SignalFeed";
import TopOpportunities from "@/components/TopOpportunities";
import DashboardTable from "@/components/DashboardTable";
import CompanyDrawer from "@/components/CompanyDrawer";
import AppHeader from "@/components/AppHeader";
import { companies, type Status } from "@/data/mockData";

const Index = () => {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<Record<string, Status>>(
    Object.fromEntries(companies.map(c => [c.id, c.status]))
  );

  const handleStatusChange = (companyId: string, status: Status) => {
    setStatuses(prev => ({ ...prev, [companyId]: status }));
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      <SignalFeed onCompanyClick={setSelectedCompanyId} />
      <TopOpportunities onCompanyClick={setSelectedCompanyId} />
      <div className="border-t mx-4" />
      <DashboardTable onCompanyClick={setSelectedCompanyId} statuses={statuses} onStatusChange={handleStatusChange} />

      {selectedCompanyId && (
        <CompanyDrawer
          companyId={selectedCompanyId}
          status={statuses[selectedCompanyId]}
          onStatusChange={handleStatusChange}
          onClose={() => setSelectedCompanyId(null)}
        />
      )}
    </div>
  );
};

export default Index;
