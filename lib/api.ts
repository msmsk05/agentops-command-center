export type AgentStatus = 'queued' | 'running' | 'complete' | 'waiting' | 'error';

export type Agent = {
  id: string;
  name: string;
  role: string;
  type: 'sequential' | 'parallel' | 'loop' | 'remote';
  status: AgentStatus;
  duration?: number;
  tokens?: number;
  cost?: number;
  iteration?: number;
};

export type Run = {
  id: string;
  traceId: string;
  sessionId: string;
  status: AgentStatus;
  startedAt: string;
  elapsed: number;
  agents: Agent[];
  events: EventRecord[];
};

export type EventRecord = {
  time: string;
  label: string;
  detail: string;
  kind: 'agent' | 'tool' | 'protocol' | 'system';
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function startRun(task: string): Promise<{ runId: string }> {
  if (!API_BASE) return { runId: `demo-${Date.now()}` };
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task }),
  });
  if (!response.ok) throw new Error('Unable to start workflow');
  return response.json();
}

export function streamRun(runId: string, onEvent: (event: EventRecord) => void, onDone: () => void) {
  if (!API_BASE || runId.startsWith('demo-')) return undefined;
  const source = new EventSource(`${API_BASE}/api/runs/${runId}/events`);
  source.onmessage = (message) => onEvent(JSON.parse(message.data) as EventRecord);
  source.onerror = () => { source.close(); onDone(); };
  return source;
}

// ---------------------------------------------------------------------------
// Monitoring API - all types mirror backend/app/api/monitoring.py responses.
// `estimated_cost`/latency fields are `null` (not 0) whenever the backend
// genuinely couldn't compute them (e.g. no pricing match, no samples yet).
// ---------------------------------------------------------------------------

export type MonitoringSummary = {
  total_runs: number;
  active_runs: number;
  completed_runs: number;
  failed_runs: number;
  success_rate: number | null;
  avg_latency_ms: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  p99_latency_ms: number | null;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  estimated_cost: number | null;
  agent_executions: number;
  tool_calls: number;
  mcp_calls: number;
  a2a_calls: number;
  errors: number;
};

export type MonitoringRun = {
  run_id: string;
  trace_id: string;
  status: AgentStatus;
  task_summary: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  total_tokens: number;
  estimated_cost: number | null;
  error: string | null;
};

export type LatencySeries = {
  points: Array<Record<string, unknown>>;
  avg_latency_ms: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  p99_latency_ms: number | null;
  sample_size: number;
};

export type MonitoringLatency = {
  workflow: LatencySeries;
  agent: LatencySeries;
  mcp: LatencySeries;
  a2a: LatencySeries;
};

export type UsageByRun = { run_id: string; input_tokens: number; output_tokens: number; total_tokens: number; estimated_cost: number | null };
export type UsageByAgent = { agent_name: string; input_tokens: number; output_tokens: number; total_tokens: number; estimated_cost: number | null };

export type MonitoringUsage = {
  by_run: UsageByRun[];
  by_agent: UsageByAgent[];
  totals: { input_tokens: number; output_tokens: number; total_tokens: number; estimated_cost: number | null };
};

export type ProtocolStats = {
  protocol: string;
  call_count: number;
  success_count: number;
  failure_count: number;
  average_latency_ms: number | null;
  p95_latency_ms: number | null;
  recent_calls: Array<{ run_id: string; time: string; label: string; status?: string; duration_ms?: number }>;
};

export type MonitoringProtocols = { mcp: ProtocolStats; a2a: ProtocolStats };

export type AgentStats = {
  agent_name: string;
  executions: number;
  successes: number;
  failures: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  average_latency_ms: number | null;
  estimated_cost: number | null;
};

export type MonitoringAgents = { agents: AgentStats[] };

export type TraceEvent = EventRecord & { category: 'ADK' | 'MCP' | 'A2A' | 'system' | 'error'; [key: string]: unknown };

export type RunTrace = {
  run_id: string;
  trace_id: string;
  session_id: string;
  status: AgentStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error: string | null;
  events: TraceEvent[];
};

async function getJson<T>(path: string): Promise<T> {
  if (!API_BASE) throw new Error('NEXT_PUBLIC_API_BASE_URL is not configured');
  const response = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Request to ${path} failed with ${response.status}`);
  return response.json();
}

export const getMonitoringSummary = () => getJson<MonitoringSummary>('/api/monitoring/summary');
export const getRecentRuns = (limit = 20) => getJson<{ runs: MonitoringRun[] }>(`/api/monitoring/runs?limit=${limit}`);
export const getMonitoringLatency = () => getJson<MonitoringLatency>('/api/monitoring/latency');
export const getMonitoringUsage = () => getJson<MonitoringUsage>('/api/monitoring/usage');
export const getMonitoringProtocols = () => getJson<MonitoringProtocols>('/api/monitoring/protocols');
export const getMonitoringAgents = () => getJson<MonitoringAgents>('/api/monitoring/agents');
export const getRunTrace = (runId: string) => getJson<RunTrace>(`/api/monitoring/runs/${runId}/trace`);
