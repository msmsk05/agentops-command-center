'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { AlertTriangle, ArrowLeft, Clock3, Coins, Cpu, Database, Layers3, Radio, RefreshCw, TriangleAlert, Zap } from 'lucide-react';
import {
  AgentStats, MonitoringLatency, MonitoringProtocols, MonitoringRun,
  MonitoringSummary, MonitoringUsage, RunTrace, getMonitoringAgents, getMonitoringLatency,
  getMonitoringProtocols, getMonitoringSummary, getMonitoringUsage, getRecentRuns, getRunTrace,
} from '@/lib/api';

const CATEGORY_COLOR: Record<string, string> = {
  ADK: '#4179c7',
  MCP: '#176b70',
  A2A: '#d8902d',
  error: '#d86455',
  system: '#89958e',
};

const REFRESH_INTERVAL_MS = 15000;

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return value < 1000 ? `${Math.round(value)}ms` : `${(value / 1000).toFixed(2)}s`;
}

function formatCost(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'unknown';
  return `$${value.toFixed(value < 0.01 ? 6 : 4)}`;
}

function formatTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString();
}

type Snapshot = {
  summary: MonitoringSummary;
  runs: MonitoringRun[];
  latency: MonitoringLatency;
  usage: MonitoringUsage;
  protocols: MonitoringProtocols;
  agents: AgentStats[];
};

export default function MonitoringView() {
  const configured = Boolean(process.env.NEXT_PUBLIC_API_BASE_URL);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [trace, setTrace] = useState<RunTrace | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!configured) { setLoading(false); return; }
    try {
      const [summary, runsResponse, latency, usage, protocols, agentsResponse] = await Promise.all([
        getMonitoringSummary(), getRecentRuns(50), getMonitoringLatency(), getMonitoringUsage(),
        getMonitoringProtocols(), getMonitoringAgents(),
      ]);
      setSnapshot({ summary, runs: runsResponse.runs, latency, usage, protocols, agents: agentsResponse.agents });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load monitoring telemetry');
    } finally {
      setLoading(false);
    }
  }, [configured]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!selectedRunId) { setTrace(null); return; }
    let cancelled = false;
    setTraceError(null);
    getRunTrace(selectedRunId)
      .then((data) => { if (!cancelled) setTrace(data); })
      .catch((err) => { if (!cancelled) setTraceError(err instanceof Error ? err.message : 'Failed to load trace'); });
    return () => { cancelled = true; };
  }, [selectedRunId]);

  if (!configured) {
    return (
      <div className="monitoring-empty">
        <TriangleAlert size={22} />
        <h3>No live backend connected</h3>
        <p>Set <code>NEXT_PUBLIC_API_BASE_URL</code> to the AgentOps API to see real production telemetry. This tab never shows sample or randomized metrics.</p>
      </div>
    );
  }

  if (loading) return <div className="monitoring-empty"><RefreshCw size={20} className="spin" /><p>Loading real telemetry…</p></div>;

  if (error || !snapshot) {
    return (
      <div className="monitoring-empty">
        <AlertTriangle size={22} />
        <h3>Couldn&apos;t load monitoring telemetry</h3>
        <p>{error}</p>
        <button className="run-button" onClick={load}><RefreshCw size={14} /> Retry</button>
      </div>
    );
  }

  const { summary, runs, latency, usage, protocols, agents } = snapshot;
  const noRunsYet = summary.total_runs === 0;

  return (
    <div className="monitoring">
      <div className="monitoring-banner">
        <span><Database size={14} /> In-memory telemetry — one Azure Container Apps replica. History resets on redeploy/restart; not yet durable.</span>
        <button className="icon-button" onClick={load} aria-label="Refresh"><RefreshCw size={14} /></button>
      </div>

      {noRunsYet ? (
        <div className="monitoring-empty">
          <Database size={22} />
          <h3>No production runs recorded yet</h3>
          <p>Kick off a run from the Overview tab — this dashboard reflects real telemetry only, with nothing pre-populated.</p>
        </div>
      ) : (
        <>
          <div className="kpi-grid">
            <KpiCard icon={<Layers3 size={16} />} label="Total Runs" value={summary.total_runs.toLocaleString()} />
            <KpiCard icon={<Zap size={16} />} label="Success Rate" value={summary.success_rate === null ? '—' : `${summary.success_rate}%`} />
            <KpiCard icon={<Clock3 size={16} />} label="Avg Latency" value={formatMs(summary.avg_latency_ms)} />
            <KpiCard icon={<Clock3 size={16} />} label="P95 Latency" value={formatMs(summary.p95_latency_ms)} />
            <KpiCard icon={<Cpu size={16} />} label="Total Tokens" value={summary.total_tokens.toLocaleString()} />
            <KpiCard icon={<Coins size={16} />} label="Estimated Cost" value={formatCost(summary.estimated_cost)} />
            <KpiCard icon={<Database size={16} />} label="MCP Calls" value={summary.mcp_calls.toLocaleString()} />
            <KpiCard icon={<Radio size={16} />} label="A2A Calls" value={summary.a2a_calls.toLocaleString()} />
            <KpiCard icon={<AlertTriangle size={16} />} label="Errors" value={summary.errors.toLocaleString()} tone={summary.errors > 0 ? 'warn' : undefined} />
          </div>

          <div className="chart-grid">
            <ChartCard title="Workflow latency over time" subtitle={`${latency.workflow.sample_size} runs measured`}>
              {latency.workflow.points.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={[...latency.workflow.points].sort((a, b) => String(a.started_at).localeCompare(String(b.started_at)))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dde4de" />
                    <XAxis dataKey="started_at" tickFormatter={(value) => formatTime(String(value))} tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} width={48} />
                    <Tooltip formatter={(value) => formatMs(Number(value))} labelFormatter={(value) => formatTime(String(value))} />
                    <Line type="monotone" dataKey="duration_ms" stroke="#4179c7" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : <EmptyChart />}
            </ChartCard>

            <ChartCard title="Token usage by agent" subtitle="input vs output tokens">
              {usage.by_agent.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={usage.by_agent}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dde4de" />
                    <XAxis dataKey="agent_name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
                    <YAxis tick={{ fontSize: 10 }} width={40} />
                    <Tooltip />
                    <Bar dataKey="input_tokens" stackId="tokens" fill="#4179c7" name="input" />
                    <Bar dataKey="output_tokens" stackId="tokens" fill="#c9f073" name="output" />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyChart />}
            </ChartCard>

            <ChartCard title="Estimated cost by agent" subtitle="null = pricing unavailable, not $0">
              {usage.by_agent.some((row) => row.estimated_cost !== null) ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={usage.by_agent.map((row) => ({ ...row, cost: row.estimated_cost ?? 0 }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dde4de" />
                    <XAxis dataKey="agent_name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
                    <YAxis tick={{ fontSize: 10 }} width={56} />
                    <Tooltip formatter={(value) => `$${Number(value).toFixed(6)}`} />
                    <Bar dataKey="cost" fill="#d8902d" name="estimated cost" />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyChart message="No priced usage yet" />}
            </ChartCard>

            <ChartCard title="Agent activity" subtitle="completed executions">
              {agents.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={agents} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#dde4de" />
                    <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals={false} />
                    <YAxis type="category" dataKey="agent_name" tick={{ fontSize: 10 }} width={90} />
                    <Tooltip />
                    <Bar dataKey="executions" fill="#247a58" name="executions" />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyChart />}
            </ChartCard>

            <ChartCard title="Protocol activity" subtitle="MCP vs A2A calls">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'MCP', value: protocols.mcp.call_count },
                      { name: 'A2A', value: protocols.a2a.call_count },
                    ].filter((slice) => slice.value > 0)}
                    dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}
                  >
                    <Cell fill="#176b70" />
                    <Cell fill="#d8902d" />
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="protocol-stat-row">
                <ProtocolStat label="MCP" stats={protocols.mcp} />
                <ProtocolStat label="A2A" stats={protocols.a2a} />
              </div>
            </ChartCard>
          </div>

          <div className="section-header"><div><span className="section-kicker">RECENT RUNS</span><h2>Production executions</h2></div></div>
          <div className="runs-table-card">
            <table className="runs-table">
              <thead>
                <tr><th>Run</th><th>Status</th><th>Task</th><th>Duration</th><th>Tokens</th><th>Cost</th><th>Started</th></tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.run_id} className="clickable-row" onClick={() => setSelectedRunId(run.run_id)}>
                    <td><code>{run.run_id}</code></td>
                    <td><span className={`run-status-badge ${run.status}`}>{run.status}</span></td>
                    <td className="task-cell">{run.task_summary || '—'}</td>
                    <td>{formatMs(run.duration_ms)}</td>
                    <td>{run.total_tokens.toLocaleString()}</td>
                    <td>{formatCost(run.estimated_cost)}</td>
                    <td>{formatTime(run.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {selectedRunId && (
        <div className="trace-drawer">
          <div className="trace-drawer-header">
            <button className="icon-button" onClick={() => setSelectedRunId(null)} aria-label="Close trace"><ArrowLeft size={16} /></button>
            <div><span className="section-kicker">TRACE</span><h3>{selectedRunId}</h3></div>
          </div>
          {traceError && <p className="trace-error">{traceError}</p>}
          {trace && (
            <>
              <div className="trace-meta">
                <span>trace_id: <code>{trace.trace_id}</code></span>
                <span>session_id: <code>{trace.session_id}</code></span>
                <span>status: <b>{trace.status}</b></span>
                <span>duration: {formatMs(trace.duration_ms)}</span>
              </div>
              <ol className="trace-timeline">
                {trace.events.map((event, index) => (
                  <li key={`${event.time}-${index}`} style={{ borderColor: CATEGORY_COLOR[event.category] ?? CATEGORY_COLOR.system }}>
                    <span className="trace-badge" style={{ background: CATEGORY_COLOR[event.category] ?? CATEGORY_COLOR.system }}>{event.category}</span>
                    <div className="trace-body">
                      <b>{event.label}</b>
                      <span>{event.detail}</span>
                      <small>{formatTime(event.time)}{typeof event.duration_ms === 'number' ? ` · ${formatMs(event.duration_ms)}` : ''}</small>
                    </div>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function KpiCard({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone?: 'warn' }) {
  return (
    <div className={`kpi-card ${tone ?? ''}`}>
      <span className="kpi-icon">{icon}</span>
      <div><small>{label}</small><b>{value}</b></div>
    </div>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="chart-card">
      <div className="chart-card-head"><h4>{title}</h4><span>{subtitle}</span></div>
      {children}
    </div>
  );
}

function EmptyChart({ message = 'No measured samples yet' }: { message?: string }) {
  return <div className="chart-empty">{message}</div>;
}

function ProtocolStat({ label, stats }: { label: string; stats: MonitoringProtocols['mcp'] }) {
  return (
    <div className="protocol-stat">
      <b>{label}</b>
      <span>{stats.call_count} calls</span>
      <span>{stats.success_count} ok · {stats.failure_count} failed</span>
      <span>avg {formatMs(stats.average_latency_ms)} · p95 {formatMs(stats.p95_latency_ms)}</span>
    </div>
  );
}
