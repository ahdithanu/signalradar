import type { Company } from "@/data/mockData";
import { api } from "./client";

interface DashboardResponse {
  data: Company[];
}

export async function fetchDashboard(): Promise<Company[]> {
  const json: DashboardResponse = await api.dashboard();
  return json.data;
}
