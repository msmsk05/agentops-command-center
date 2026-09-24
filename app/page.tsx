'use client';

import { useEffect, useMemo, useState } from 'react';
import { Activity, ArrowUpRight, Bot, Check, ChevronRight, CircleDot, Clock3, Cpu, Database, GitBranch, Layers3, Play, Radio, RefreshCw, Search, Sparkles, Zap } from 'lucide-react';
import { Agent, EventRecord, startRun, streamRun } from '@/lib/api';

const initialAgents: Agent[] = [
  { id: 'orchestrator', name: 'Orchestrator', role: 'Workflow control', type: 'sequential', status: 'complete', duration: 420, tokens: 742, cost: 0.004 },
  { id: 'planner', name: 'Planning Agent', role: 'Strategy & scope', type: 'sequential', status: 'complete', duration: 1160, tokens: 1210, cost: 0.008 },
  { id: 'decomposer', name: 'Task Decomposer', role: 'Subtask routing', type: 'sequential', status: 'complete', duration: 930, tokens: 884, cost: 0.006 },
  { id: 'research', name: 'Research Agent', role: 'Evidence discovery', type: 'parallel', status: 'running', duration: 2840, tokens: 2918, cost: 0.019 },
  { id: 'analyst', name: 'Data Analyst', role: 'Structured reasoning', type: 'parallel', status: 'running', duration: 2510, tokens: 2341, cost: 0.016 },
  { id: 'risk', name: 'Risk Analyst', role: 'Uncertainty mapping', type: 'parallel', status: 'complete', duration: 2980, tokens: 2670, cost: 0.018 },
  { id: 'aggregator', name: 'Aggregator', role: 'Shared state merge', type: 'sequential', status: 'waiting', tokens: 0, cost: 0 },
  { id: 'critic', name: 'Critic Agent', role: 'Quality loop', type: 'loop', status: 'waiting', iteration: 2, tokens: 0, cost: 0 },
  { id: 'compliance', name: 'Compliance Agent', role: 'Remote policy review', type: 'remote', status: 'waiting', tokens: 0, cost: 0 },
  { id: 'synthesis', name: 'Synthesis Agent', role: 'Executive output', type: 'sequential', status: 'waiting', tokens: 0, cost: 0 },
];

const demoEvents: EventRecord[] = [
  { time: '14:32:08.412', label: 'ParallelAgent', detail: '3 specialists dispatched concurrently', kind: 'agent' },
  { time: '14:32:08.430', label: 'MCP / search_documents', detail: 'Research Agent queried 24 indexed sources', kind: 'tool' },
  { time: '14:32:09.102', label: 'A2A / compliance-review', detail: 'Remote task accepted by Compliance Agent', kind: 'protocol' },
  { time: '14:32:10.822', label: 'Shared state', detail: '6.4 KB merged into workflow context', kind: 'system' },
  { time: '14:32:11.234', label: 'LoopAgent', detail: 'Iteration 2 started - quality 0.79', kind: 'agent' },
];

function StatusDot({ status }: { status: Agent['status'] }) {
  return <span className={`status-dot ${status}`} aria-label={status} />;
}

export default function Home() {
  const [agents, setAgents] = useState(initialAgents);
  const [events, setEvents] = useState(demoEvents);
  const [task, setTask] = useState('Analyze the competitive landscape of enterprise AI agent platforms and recommend a strategic position.');
  const [running, setRunning] = useState(false);
  const [activeView, setActiveView] = useState('Overview');
  const [runId, setRunId] = useState('run_8f2a91');

  const totals = useMemo(() => ({
    tokens: agents.reduce((sum, agent) => sum + (agent.tokens ?? 0), 0),
    cost: agents.reduce((sum, agent) => sum + (agent.cost ?? 0), 0),
    complete: agents.filter((agent) => agent.status === 'complete').length,
  }), [agents]);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      setAgents((current) => {
        const next = [...current];
        const waiting = next.findIndex((agent) => agent.status === 'waiting');
        if (waiting >= 0) {
          next[waiting] = { ...next[waiting], status: 'running' };
          const event: EventRecord = { time: new Date().toISOString().slice(11, 23), label: next[waiting].name, detail: 'Execution span started', kind: 'agent' };
          setEvents((items) => [event, ...items].slice(0, 8));
        } else {
          const active = next.findIndex((agent) => agent.status === 'running');
          if (active >= 0) next[active] = { ...next[active], status: 'complete', tokens: 1000 + Math.floor(Math.random() * 1800), cost: 0.009 + Math.random() * 0.014 };
          else setRunning(false);
        }
        return next;
      });
    }, 850);
    return () => window.clearInterval(timer);
  }, [running]);

  async function handleRun() {
    setRunning(true);
    setAgents(initialAgents.map((agent, index) => ({ ...agent, status: index === 0 ? 'running' : 'waiting' })));
    try {
      const result = await startRun(task);
      setRunId(result.runId);
      streamRun(result.runId, (event) => setEvents((items) => [event, ...items].slice(0, 8)), () => setRunning(false));
    } catch {
      setEvents((items) => [{ time: new Date().toISOString().slice(11, 23), label: 'Backend unavailable', detail: 'Running local observability demo', kind: 'system' }, ...items]);
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={18} /></div><div><strong>AgentOps</strong><span>Command Center</span></div></div>
        <div className="workspace-switcher"><span className="workspace-icon">A</span><div><b>Acme Intelligence</b><small>Production workspace</small></div><ChevronRight size={15} /></div>
        <nav><p className="nav-label">Workspace</p>{['Overview', 'Runs', 'Agents', 'Monitoring'].map((item) => <button key={item} className={activeView === item ? 'nav-item active' : 'nav-item'} onClick={() => setActiveView(item)}><span>{item === 'Overview' ? <Layers3 size={17} /> : item === 'Runs' ? <RefreshCw size={17} /> : item === 'Agents' ? <Bot size={17} /> : <Activity size={17} />}</span>{item}{item === 'Monitoring' && <i>Live</i>}</button>)}<p className="nav-label integrations-label">Infrastructure</p><button className="nav-item"><Database size={17} /> MCP Services <span className="nav-check"><Check size={12} /></span></button><button className="nav-item"><Radio size={17} /> A2A Network <span className="nav-check"><Check size={12} /></span></button></nav>
        <div className="sidebar-bottom"><div className="system-health"><StatusDot status="complete" /><div><b>All systems operational</b><small>Last checked just now</small></div></div><div className="user-row"><div className="avatar">MS</div><div><b>Michiel Simsek</b><small>Administrator</small></div><ChevronRight size={15} /></div></div>
      </aside>

      <section className="content">
        <header className="topbar"><div><span className="eyebrow"><CircleDot size={12} /> LIVE WORKFLOW</span><h1>{activeView}</h1></div><div className="top-actions"><span className="environment"><StatusDot status="complete" /> Production</span><button className="icon-button" aria-label="Search"><Search size={18} /></button><div className="avatar small">MS</div></div></header>
        <div className="page-grid">
          <section className="main-column">
            <div className="command-panel"><div className="panel-heading"><div><span className="section-kicker">NEW INTELLIGENCE RUN</span><h2>What should the agents investigate?</h2></div><span className="shortcut">⌘ ↵</span></div><textarea value={task} onChange={(event) => setTask(event.target.value)} aria-label="Research task" /><div className="command-footer"><div className="run-options"><span><Zap size={14} /> Azure GPT-4o</span><span><GitBranch size={14} /> Sequential + parallel</span><span><Clock3 size={14} /> Max 3 iterations</span></div><button className="run-button" onClick={handleRun} disabled={running}><Play size={15} fill="currentColor" /> {running ? 'Orchestration active' : 'Run intelligence'}<ArrowUpRight size={15} /></button></div></div>
            <div className="section-header"><div><span className="section-kicker">WORKFLOW GRAPH</span><h2>Execution topology</h2></div><div className="trace-chip"><span>TRACE</span> {runId} <CopyIcon /></div></div>
            <div className="workflow-card"><div className="flow-line" /><div className="stage-label first">SEQUENTIAL</div><div className="agent-row sequential-row">{agents.slice(0, 3).map((agent) => <AgentCard key={agent.id} agent={agent} />)}</div><div className="stage-label parallel-label">PARALLEL <span>3 concurrent spans</span></div><div className="agent-row parallel-row">{agents.slice(3, 6).map((agent) => <AgentCard key={agent.id} agent={agent} />)}</div><div className="stage-label loop-label">QUALITY LOOP <span>iteration {agents[7].iteration} / 3</span></div><div className="agent-row final-row">{agents.slice(6).map((agent) => <AgentCard key={agent.id} agent={agent} />)}</div></div>
            <div className="section-header events-heading"><div><span className="section-kicker">ACTIVITY STREAM</span><h2>Live telemetry</h2></div><span className="live-indicator"><span /> streaming</span></div>
            <div className="events-card">{events.map((event, index) => <div className="event-row" key={`${event.time}-${index}`}><span className="event-time">{event.time}</span><span className={`event-icon ${event.kind}`}>{event.kind === 'tool' ? <Search size={14} /> : event.kind === 'protocol' ? <Radio size={14} /> : event.kind === 'system' ? <Database size={14} /> : <Cpu size={14} />}</span><div><b>{event.label}</b><span>{event.detail}</span></div><ChevronRight size={14} className="event-arrow" /></div>)}</div>
          </section>
          <aside className="metrics-column"><div className="run-status-card"><div className="status-header"><span className="section-kicker">CURRENT RUN</span><span className="run-live"><StatusDot status={running ? 'running' : 'complete'} /> {running ? 'Running' : 'Complete'}</span></div><div className="run-id">{runId}</div><div className="metric-large">{running ? '00:12.84' : '00:18.42'} <small>duration</small></div><div className="progress-track"><span style={{ width: `${Math.max(42, (totals.complete / agents.length) * 100)}%` }} /></div><div className="progress-meta"><span>{totals.complete} of {agents.length} agents complete</span><span>quality 0.79</span></div></div><div className="metrics-card"><div className="card-title"><span>Run economics</span><span className="estimate">ESTIMATES</span></div><Metric icon={<Cpu size={16} />} label="Total tokens" value={totals.tokens.toLocaleString()} trend="+12.4%" /><Metric icon={<Zap size={16} />} label="LLM cost" value={`$${totals.cost.toFixed(3)}`} trend="Azure GPT-4o" /><Metric icon={<Clock3 size={16} />} label="Avg. latency" value="2.84s" trend="p95 4.12s" /></div><div className="quality-card"><div className="quality-top"><span className="section-kicker">QUALITY LOOP</span><span className="iteration-badge">2 / 3</span></div><div className="quality-score">0.79 <span>quality score</span></div><div className="quality-bar"><span /></div><div className="quality-foot"><span>4 issues found</span><span>threshold 0.85</span></div></div><div className="integration-card"><div className="card-title"><span>Connected services</span><ArrowUpRight size={15} /></div><Integration icon={<Database size={17} />} name="MCP Knowledge Server" detail="4 tools available" status="Connected" /><Integration icon={<Radio size={17} />} name="A2A Compliance Agent" detail="Remote - Azure Container Apps" status="Healthy" /></div></aside>
        </div>
      </section>
    </main>
  );
}

function AgentCard({ agent }: { agent: Agent }) { return <div className={`agent-card ${agent.status}`}><div className="agent-card-top"><span className={`agent-type ${agent.type}`}>{agent.type === 'remote' ? 'A2A' : agent.type}</span><StatusDot status={agent.status} /></div><div className="agent-name">{agent.name}</div><div className="agent-role">{agent.role}</div><div className="agent-meta"><span>{agent.status === 'waiting' ? 'Queued' : agent.duration ? `${(agent.duration / 1000).toFixed(2)}s` : 'Running'}</span>{agent.tokens ? <span>{agent.tokens.toLocaleString()} tok</span> : null}</div></div> }
function Metric({ icon, label, value, trend }: { icon: React.ReactNode; label: string; value: string; trend: string }) { return <div className="metric-row"><span className="metric-icon">{icon}</span><div><small>{label}</small><b>{value}</b></div><span className="metric-trend">{trend}</span></div> }
function Integration({ icon, name, detail, status }: { icon: React.ReactNode; name: string; detail: string; status: string }) { return <div className="integration-row"><span className="integration-icon">{icon}</span><div><b>{name}</b><small>{detail}</small></div><span className="connected"><span /> {status}</span></div> }
function CopyIcon() { return <span className="copy-icon">⧉</span> }
