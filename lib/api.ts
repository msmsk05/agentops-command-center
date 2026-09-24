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
