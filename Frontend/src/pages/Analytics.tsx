import { useEffect, useMemo, useState } from "react";
import { companies } from "@/data/mockData";
import AppHeader from "@/components/AppHeader";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  Legend,
} from "recharts";

interface UserPreferences {
  defaultTimePeriod: "7d" | "30d" | "90d" | "All";
  notifications: {
    newSignals: boolean;
    statusChanges: boolean;
    dailyDigest: boolean;
    weeklyReport: boolean;
    highProbabilityAlerts: boolean;
  };
  display: {
    compactView: boolean;
    showDismissed: boolean;
  };
}

const DEFAULT_PREFS: UserPreferences = {
  defaultTimePeriod: "30d",
  notifications: {
    newSignals: true,
    statusChanges: true,
    dailyDigest: false,
    weeklyReport: true,
    highProbabilityAlerts: true,
  },
  display: {
    compactView: false,
    showDismissed: false,
  },
};

const loadPreferences = (): UserPreferences => {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const saved = localStorage.getItem("user_preferences");
    return saved ? { ...DEFAULT_PREFS, ...JSON.parse(saved) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
};

const TIME_PERIOD_MAP: Record<string, number> = {
  "7d": 7,
  "30d": 30,
  "90d": 90,
  All: Infinity,
};

const STATUS_COLORS: Record<string, string> = {
  New: "hsl(217, 91%, 53%)",
  Reviewing: "hsl(45, 93%, 47%)",
  "Ready for Outreach": "hsl(160, 84%, 39%)",
  Dismissed: "hsl(215, 16%, 47%)",
};

const INDUSTRY_COLORS = [
  "hsl(217, 91%, 53%)",
  "hsl(160, 84%, 39%)",
  "hsl(258, 90%, 66%)",
  "hsl(45, 93%, 47%)",
  "hsl(0, 84%, 60%)",
  "hsl(190, 80%, 42%)",
  "hsl(330, 70%, 50%)",
];

const TIME_PERIODS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "All", days: Infinity },
] as const;

const Analytics = () => {
  const prefs = useMemo(loadPreferences, []);
  const [periodDays, setPeriodDays] = useState<number>(TIME_PERIOD_MAP[prefs.defaultTimePeriod] ?? 30);

  // Filter companies that have at least one signal within the period
  const cutoffDate = useMemo(() => {
    if (periodDays === Infinity) return new Date(0);
    const d = new Date();
    d.setDate(d.getDate() - periodDays);
    return d;
  }, [periodDays]);

  const filteredCompanies = useMemo(
    () => companies.filter((c) => c.signals.some((s) => new Date(s.date) >= cutoffDate)),
    [cutoffDate]
  );

  const filteredSignals = useMemo(
    () => companies.flatMap((c) => c.signals.filter((s) => new Date(s.date) >= cutoffDate).map((s) => ({ ...s, companyName: c.name }))),
    [cutoffDate]
  );

  // Signals over time (grouped by week)
  const signalsOverTime = useMemo(() => {
    const byWeek = new Map<string, { funding: number; hiring: number; growth: number; product_launch: number }>();
    filteredSignals.forEach((s) => {
      const d = new Date(s.date);
      const weekStart = new Date(d);
      weekStart.setDate(d.getDate() - d.getDay());
      const key = weekStart.toISOString().slice(0, 10);
      if (!byWeek.has(key)) byWeek.set(key, { funding: 0, hiring: 0, growth: 0, product_launch: 0 });
      byWeek.get(key)![s.type]++;
    });
    return Array.from(byWeek.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([week, counts]) => ({
        week: new Date(week).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        ...counts,
        total: counts.funding + counts.hiring + counts.growth + counts.product_launch,
      }));
  }, [filteredSignals]);

  // Conversion by status
  const statusBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    filteredCompanies.forEach((c) => { counts[c.status] = (counts[c.status] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [filteredCompanies]);

  // Top industries by avg opportunity score
  const industryPerformance = useMemo(() => {
    const byIndustry = new Map<string, { totalScore: number; count: number; totalProb: number }>();
    filteredCompanies.forEach((c) => {
      const existing = byIndustry.get(c.industry) || { totalScore: 0, count: 0, totalProb: 0 };
      existing.totalScore += c.opportunityScore;
      existing.totalProb += c.opportunityProbability;
      existing.count++;
      byIndustry.set(c.industry, existing);
    });
    return Array.from(byIndustry.entries())
      .map(([industry, data]) => ({
        industry,
        avgScore: Math.round(data.totalScore / data.count),
        avgProbability: Math.round((data.totalProb / data.count) * 100),
        companies: data.count,
      }))
      .sort((a, b) => b.avgScore - a.avgScore);
  }, [filteredCompanies]);

  // Pipeline funnel data
  const funnelData = useMemo(() => {
    const stages = ["New", "Reviewing", "Ready for Outreach"] as const;
    const colors = ["hsl(217, 91%, 53%)", "hsl(45, 93%, 47%)", "hsl(160, 84%, 39%)"];
    const counts = stages.map((stage) => filteredCompanies.filter((c) => c.status === stage).length);
    return stages.map((stage, i) => ({ name: stage, value: counts[i], fill: colors[i] }));
  }, [filteredCompanies]);

  // Summary stats
  const totalSignals = filteredSignals.length;
  const avgScore = filteredCompanies.length ? Math.round(filteredCompanies.reduce((sum, c) => sum + c.opportunityScore, 0) / filteredCompanies.length) : 0;
  const readyCount = filteredCompanies.filter((c) => c.status === "Ready for Outreach").length;

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      {/* Time Period Selector + Summary */}
      <div className="px-4 pt-4 pb-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-1 bg-secondary rounded-lg p-0.5">
          {TIME_PERIODS.map((p) => (
            <button
              key={p.label}
              onClick={() => setPeriodDays(p.days)}
              className={`text-xs px-3 py-1.5 rounded-md transition-colors font-medium ${
                periodDays === p.days
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-muted-foreground font-mono">
          {filteredCompanies.length} companies · {totalSignals} signals in window
        </span>
      </div>
      <div className="px-4 pb-2">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Total Signals" value={String(totalSignals)} />
          <StatCard label="Companies Tracked" value={String(companies.length)} />
          <StatCard label="Avg Opp. Score" value={String(avgScore)} />
          <StatCard label="Ready for Outreach" value={String(readyCount)} />
        </div>
      </div>

      {/* Charts */}
      <div className="px-4 py-4 space-y-6">
        {/* Signals Over Time */}
        <ChartCard title="Signals Detected Over Time">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={signalsOverTime}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(214, 32%, 91%)" />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} stroke="hsl(215, 16%, 47%)" />
              <YAxis tick={{ fontSize: 11 }} stroke="hsl(215, 16%, 47%)" allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(0, 0%, 100%)",
                  border: "1px solid hsl(214, 32%, 91%)",
                  borderRadius: "6px",
                  fontSize: 12,
                }}
              />
              <Area type="monotone" dataKey="funding" stackId="1" fill="hsl(217, 91%, 53%)" stroke="hsl(217, 91%, 53%)" fillOpacity={0.6} />
              <Area type="monotone" dataKey="hiring" stackId="1" fill="hsl(160, 84%, 39%)" stroke="hsl(160, 84%, 39%)" fillOpacity={0.6} />
              <Area type="monotone" dataKey="growth" stackId="1" fill="hsl(45, 93%, 47%)" stroke="hsl(45, 93%, 47%)" fillOpacity={0.6} />
              <Area type="monotone" dataKey="product_launch" stackId="1" fill="hsl(258, 90%, 66%)" stroke="hsl(258, 90%, 66%)" fillOpacity={0.6} />
              <Legend
                formatter={(value: string) =>
                  value === "product_launch" ? "Product Launch" : value.charAt(0).toUpperCase() + value.slice(1)
                }
                wrapperStyle={{ fontSize: 11 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Pipeline Conversion Funnel */}
          <ChartCard title="Pipeline Conversion Funnel">
            <div className="flex flex-col items-center py-4">
              {(() => {
                const allStages = [
                  { name: "New", color: "hsl(217, 91%, 60%)" },
                  { name: "Reviewing", color: "hsl(45, 93%, 55%)" },
                  { name: "Ready for Outreach", color: "hsl(160, 84%, 45%)" },
                  { name: "Dismissed", color: "hsl(215, 16%, 65%)" },
                ];
                const counts = allStages.map((s) => ({
                  ...s,
                  value: filteredCompanies.filter((c) => c.status === s.name).length,
                }));
                const total = filteredCompanies.length || 1;
                return (
                  <div className="w-full max-w-[340px]">
                    {counts.map((stage, i) => {
                      const topWidthPct = 100 - i * 18;
                      const bottomWidthPct = 100 - (i + 1) * 18;
                      const conversionPct = i > 0 && counts[i - 1].value > 0
                        ? Math.round((stage.value / counts[i - 1].value) * 100)
                        : null;
                      return (
                        <div key={stage.name} className="flex items-center gap-3">
                          <div className="flex-1 flex flex-col items-center">
                            <div
                              style={{
                                width: `${topWidthPct}%`,
                                height: 0,
                                borderLeft: `${(topWidthPct - bottomWidthPct) / 2}vw solid transparent`,
                                borderRight: `${(topWidthPct - bottomWidthPct) / 2}vw solid transparent`,
                              }}
                            />
                            <div
                              className="relative flex items-center justify-center transition-all"
                              style={{
                                clipPath: `polygon(${(100 - topWidthPct) / 2}% 0%, ${100 - (100 - topWidthPct) / 2}% 0%, ${100 - (100 - bottomWidthPct) / 2}% 100%, ${(100 - bottomWidthPct) / 2}% 100%)`,
                                backgroundColor: stage.color,
                                width: "100%",
                                height: 52,
                              }}
                            >
                              <span className="text-sm font-bold text-white font-mono drop-shadow-sm">
                                {stage.value}
                              </span>
                            </div>
                          </div>
                          <div className="w-[140px] shrink-0">
                            <span className="text-xs font-medium text-foreground">{stage.name}</span>
                            {conversionPct !== null && (
                              <p className="text-[10px] text-muted-foreground font-mono">{conversionPct}% from prev</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    <div className="text-center mt-4 pt-3 border-t">
                      <p className="text-xs text-muted-foreground">
                        Overall conversion: <span className="font-medium text-foreground font-mono">
                          {counts[0].value > 0
                            ? Math.round((counts[2].value / counts[0].value) * 100)
                            : 0}%
                        </span>
                      </p>
                    </div>
                  </div>
                );
              })()}
            </div>
          </ChartCard>

          {/* Top Industries */}
          <ChartCard title="Top Performing Industries">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={industryPerformance} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214, 32%, 91%)" />
                <XAxis type="number" tick={{ fontSize: 11 }} stroke="hsl(215, 16%, 47%)" domain={[0, 100]} />
                <YAxis type="category" dataKey="industry" tick={{ fontSize: 11 }} stroke="hsl(215, 16%, 47%)" width={110} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(0, 0%, 100%)",
                    border: "1px solid hsl(214, 32%, 91%)",
                    borderRadius: "6px",
                    fontSize: 12,
                  }}
                  formatter={(value: number, name: string) => [
                    name === "avgScore" ? `${value} pts` : `${value}%`,
                    name === "avgScore" ? "Avg Score" : "Avg Probability",
                  ]}
                />
                <Bar dataKey="avgScore" name="Avg Score" radius={[0, 4, 4, 0]}>
                  {industryPerformance.map((_, i) => (
                    <Cell key={i} fill={INDUSTRY_COLORS[i % INDUSTRY_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ label, value }: { label: string; value: string }) => (
  <div className="bg-card border rounded-lg p-3">
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className="text-xl font-semibold font-mono text-foreground mt-0.5">{value}</p>
  </div>
);

const ChartCard = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="bg-card border rounded-lg p-4">
    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">{title}</h3>
    {children}
  </div>
);

export default Analytics;
