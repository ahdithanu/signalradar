export type SignalType = "funding" | "hiring" | "growth" | "product_launch";
export type Status = "New" | "Reviewing" | "Ready for Outreach" | "Dismissed";

export interface Signal {
  type: SignalType;
  description: string;
  date: string;
  daysAgo: number;
  scoreContribution: number;
  interpretation: string;
}

export interface StrategicIntelligence {
  strategicTheme: string;
  managementTone: string;
  commercialPressureScore: "low" | "medium" | "high";
  narrativeShift: string;
  suggestedGTMRelevance: string;
}

export interface Company {
  id: string;
  name: string;
  website: string;
  industry: string;
  employeeCount: number;
  fundingStage: string;
  opportunityScore: number;
  opportunityProbability: number;
  signals: Signal[];
  whyNow: string;
  recommendedBuyerPersona: string[];
  suggestedOutreachAngle: string;
  status: Status;
  strategicIntelligence: StrategicIntelligence;
}

export const companies: Company[] = [
  {
    id: "1",
    name: "Nova Payments",
    website: "novapayments.io",
    industry: "Fintech",
    employeeCount: 85,
    fundingStage: "Series A",
    opportunityScore: 88,
    opportunityProbability: 0.81,
    signals: [
      { type: "funding", description: "Raised $18M Series A", date: "2026-01-28", daysAgo: 45, scoreContribution: 30, interpretation: "Entering rapid scaling phase and likely expanding GTM team." },
      { type: "hiring", description: "Hiring 3 Sales Development Representatives", date: "2026-02-15", daysAgo: 28, scoreContribution: 25, interpretation: "Expanding outbound pipeline generation." },
      { type: "hiring", description: "Hiring Revenue Operations Manager", date: "2026-02-20", daysAgo: 23, scoreContribution: 20, interpretation: "Investing in revenue infrastructure and sales systems." },
    ],
    whyNow: "Recently raised Series A funding and is building out its sales organization, suggesting a need for improved pipeline generation and revenue infrastructure.",
    recommendedBuyerPersona: ["Head of Sales", "VP Revenue", "Revenue Operations Lead"],
    suggestedOutreachAngle: "Scaling go-to-market infrastructure after funding and hiring new sales roles.",
    status: "New",
    strategicIntelligence: {
      strategicTheme: "Payments infrastructure expansion",
      managementTone: "Confident but efficiency-focused",
      commercialPressureScore: "medium",
      narrativeShift: "Increasing emphasis on enterprise sales motion",
      suggestedGTMRelevance: "Tools that accelerate revenue growth without increasing headcount significantly.",
    },
  },
  {
    id: "2",
    name: "Ramp AI",
    website: "rampai.com",
    industry: "AI / ML",
    employeeCount: 42,
    fundingStage: "Series A",
    opportunityScore: 82,
    opportunityProbability: 0.76,
    signals: [
      { type: "funding", description: "Raised $12M Series A funding", date: "2026-02-01", daysAgo: 42, scoreContribution: 30, interpretation: "Entering rapid scaling phase and likely expanding GTM team." },
      { type: "hiring", description: "Hiring Head of Growth", date: "2026-02-25", daysAgo: 18, scoreContribution: 25, interpretation: "Prioritizing growth and customer acquisition." },
    ],
    whyNow: "Just closed Series A and is actively hiring growth leadership, indicating readiness to invest in scalable acquisition channels.",
    recommendedBuyerPersona: ["Head of Growth", "CEO", "VP Marketing"],
    suggestedOutreachAngle: "Building scalable growth engine post-funding with new growth leadership.",
    status: "Reviewing",
    strategicIntelligence: {
      strategicTheme: "AI-powered automation",
      managementTone: "Aggressive growth-oriented",
      commercialPressureScore: "high",
      narrativeShift: "Shifting from product-led to sales-assisted growth",
      suggestedGTMRelevance: "Tools that bridge PLG with outbound sales motions.",
    },
  },
  {
    id: "3",
    name: "Vector Labs",
    website: "vectorlabs.dev",
    industry: "Developer Tools",
    employeeCount: 120,
    fundingStage: "Series B",
    opportunityScore: 79,
    opportunityProbability: 0.72,
    signals: [
      { type: "hiring", description: "Hiring Revenue Operations Manager", date: "2026-02-10", daysAgo: 33, scoreContribution: 20, interpretation: "Investing in revenue infrastructure and sales systems." },
      { type: "growth", description: "Revenue grew 140% YoY", date: "2026-01-15", daysAgo: 59, scoreContribution: 25, interpretation: "Rapid growth likely straining existing GTM processes." },
      { type: "product_launch", description: "Launched enterprise tier", date: "2026-02-28", daysAgo: 15, scoreContribution: 15, interpretation: "Moving upmarket requires new sales infrastructure." },
    ],
    whyNow: "Rapid revenue growth and enterprise launch signal a transition to a more structured GTM motion requiring new tooling.",
    recommendedBuyerPersona: ["Revenue Operations Lead", "Head of Sales", "VP Engineering"],
    suggestedOutreachAngle: "Supporting enterprise go-to-market transition with scalable revenue operations.",
    status: "New",
    strategicIntelligence: {
      strategicTheme: "Enterprise expansion",
      managementTone: "Measured and strategic",
      commercialPressureScore: "medium",
      narrativeShift: "From developer community to enterprise sales",
      suggestedGTMRelevance: "Enterprise sales enablement and CRM infrastructure.",
    },
  },
  {
    id: "4",
    name: "Cobalt Health",
    website: "cobalthealth.co",
    industry: "Healthcare Tech",
    employeeCount: 200,
    fundingStage: "Series B",
    opportunityScore: 74,
    opportunityProbability: 0.68,
    signals: [
      { type: "hiring", description: "Hiring VP of Sales", date: "2026-03-01", daysAgo: 14, scoreContribution: 28, interpretation: "Building senior sales leadership for aggressive expansion." },
      { type: "growth", description: "Customer base grew 90% in Q4", date: "2026-01-20", daysAgo: 54, scoreContribution: 22, interpretation: "Strong product-market fit driving commercial pressure." },
    ],
    whyNow: "Hiring senior sales leadership while experiencing rapid customer growth signals readiness for structured outbound.",
    recommendedBuyerPersona: ["VP of Sales", "Head of Business Development"],
    suggestedOutreachAngle: "Enabling sales team scaling during rapid customer acquisition phase.",
    status: "New",
    strategicIntelligence: {
      strategicTheme: "Healthcare digitization",
      managementTone: "Optimistic with urgency",
      commercialPressureScore: "high",
      narrativeShift: "Accelerating from pilot programs to full deployment",
      suggestedGTMRelevance: "Tools for managing complex enterprise sales cycles in healthcare.",
    },
  },
  {
    id: "5",
    name: "Prism Analytics",
    website: "prismanalytics.io",
    industry: "Data Analytics",
    employeeCount: 55,
    fundingStage: "Seed",
    opportunityScore: 71,
    opportunityProbability: 0.65,
    signals: [
      { type: "funding", description: "Closed $5M seed round", date: "2026-02-18", daysAgo: 25, scoreContribution: 25, interpretation: "Early-stage company beginning to build GTM function." },
      { type: "hiring", description: "Hiring first Account Executive", date: "2026-03-05", daysAgo: 10, scoreContribution: 22, interpretation: "Transitioning from founder-led sales to dedicated sales team." },
    ],
    whyNow: "Transitioning from founder-led sales to a dedicated sales team, creating demand for sales tooling and processes.",
    recommendedBuyerPersona: ["CEO", "Head of Sales", "Founding Team"],
    suggestedOutreachAngle: "Helping build the first sales stack as they transition from founder-led to team-based selling.",
    status: "Reviewing",
    strategicIntelligence: {
      strategicTheme: "Data democratization",
      managementTone: "Experimental and lean",
      commercialPressureScore: "low",
      narrativeShift: "Moving from technical product to commercial readiness",
      suggestedGTMRelevance: "Lightweight sales tools suited for early-stage teams.",
    },
  },
  {
    id: "6",
    name: "Meridian Logistics",
    website: "meridianlogistics.com",
    industry: "Supply Chain",
    employeeCount: 310,
    fundingStage: "Series C",
    opportunityScore: 67,
    opportunityProbability: 0.61,
    signals: [
      { type: "growth", description: "Expanded to 3 new markets", date: "2026-01-30", daysAgo: 44, scoreContribution: 20, interpretation: "Geographic expansion creates new GTM requirements." },
      { type: "hiring", description: "Hiring Regional Sales Directors", date: "2026-02-22", daysAgo: 21, scoreContribution: 24, interpretation: "Building regional sales capacity for market expansion." },
    ],
    whyNow: "Geographic expansion and regional sales hiring indicate a need for scalable outbound infrastructure across multiple markets.",
    recommendedBuyerPersona: ["VP Sales", "Head of Revenue", "Regional Sales Director"],
    suggestedOutreachAngle: "Supporting multi-market GTM expansion with unified sales infrastructure.",
    status: "New",
    strategicIntelligence: {
      strategicTheme: "Supply chain modernization",
      managementTone: "Methodical and growth-focused",
      commercialPressureScore: "medium",
      narrativeShift: "From domestic leader to international expansion",
      suggestedGTMRelevance: "Multi-region sales coordination and pipeline management tools.",
    },
  },
  {
    id: "7",
    name: "Athena Security",
    website: "athenasecurity.io",
    industry: "Cybersecurity",
    employeeCount: 150,
    fundingStage: "Series B",
    opportunityScore: 63,
    opportunityProbability: 0.58,
    signals: [
      { type: "product_launch", description: "Launched compliance automation suite", date: "2026-02-12", daysAgo: 31, scoreContribution: 18, interpretation: "New product line requires dedicated sales motion." },
      { type: "hiring", description: "Hiring 2 Enterprise AEs", date: "2026-03-02", daysAgo: 13, scoreContribution: 22, interpretation: "Building enterprise sales capacity." },
    ],
    whyNow: "New product launch paired with enterprise AE hiring signals a new sales motion requiring outbound support.",
    recommendedBuyerPersona: ["VP Sales", "Head of Enterprise Sales"],
    suggestedOutreachAngle: "Accelerating enterprise pipeline for newly launched compliance product.",
    status: "Dismissed",
    strategicIntelligence: {
      strategicTheme: "Compliance automation",
      managementTone: "Cautiously optimistic",
      commercialPressureScore: "medium",
      narrativeShift: "Adding compliance layer to core security offering",
      suggestedGTMRelevance: "Enterprise sales tools for regulated industry verticals.",
    },
  },
  {
    id: "8",
    name: "Flux Commerce",
    website: "fluxcommerce.co",
    industry: "E-commerce",
    employeeCount: 95,
    fundingStage: "Series A",
    opportunityScore: 59,
    opportunityProbability: 0.54,
    signals: [
      { type: "funding", description: "Raised $10M Series A", date: "2026-02-05", daysAgo: 38, scoreContribution: 28, interpretation: "Post-funding expansion phase beginning." },
    ],
    whyNow: "Fresh funding with a lean team suggests they'll be building out GTM capabilities soon.",
    recommendedBuyerPersona: ["CEO", "Head of Growth"],
    suggestedOutreachAngle: "Building GTM foundation post-Series A for rapid market capture.",
    status: "Ready for Outreach",
    strategicIntelligence: {
      strategicTheme: "Commerce platform expansion",
      managementTone: "Ambitious and fast-moving",
      commercialPressureScore: "high",
      narrativeShift: "From niche player to broad commerce platform",
      suggestedGTMRelevance: "Growth tools for scaling customer acquisition post-funding.",
    },
  },
];

export const signalFeedItems = companies.flatMap((company) =>
  company.signals.map((signal) => ({
    companyId: company.id,
    companyName: company.name,
    signal,
  }))
).sort((a, b) => a.signal.daysAgo - b.signal.daysAgo);
