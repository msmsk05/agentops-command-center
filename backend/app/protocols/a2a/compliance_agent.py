from __future__ import annotations

import uuid

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, Message, Part, Role


class ComplianceAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        text = ' '.join(part.text for part in context.message.parts if part.text)
        result = f'Compliance review completed for request: {text[:500]}. Review governance, evidence provenance, human escalation, and auditability.'
        await event_queue.enqueue_event(Message(message_id=str(uuid.uuid4()), context_id=context.context_id, task_id=context.task_id, role=Role.ROLE_AGENT, parts=[Part(text=result)]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        return None


def compliance_agent_card(url: str) -> AgentCard:
    return AgentCard(name='AgentOps Compliance Agent', description='Remote compliance and policy analysis specialist', version='1.0.0', supported_interfaces=[AgentInterface(url=url, protocol_binding='JSONRPC', protocol_version='1.0')], capabilities=AgentCapabilities(streaming=False), default_input_modes=['text/plain'], default_output_modes=['text/plain'], skills=[AgentSkill(id='compliance-review', name='Compliance review', description='Reviews governance and policy risks', tags=['compliance', 'risk'], examples=['Review these agent risks'])])
