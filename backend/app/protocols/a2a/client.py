from __future__ import annotations

import time
import uuid

from a2a.client import ClientFactory
from a2a.types import Message, Part, Role, SendMessageRequest

from app.telemetry.events import telemetry


class A2AClient:
    def __init__(self, agent_url: str, run_id: str | None = None) -> None:
        self.agent_url = agent_url
        self.run_id = run_id

    async def assess_compliance(self, request: str) -> str:
        started = time.perf_counter()
        status = 'error'
        try:
            client = await ClientFactory().create_from_url(self.agent_url)
            message = Message(message_id=str(uuid.uuid4()), role=Role.ROLE_USER, parts=[Part(text=request)])
            request_message = SendMessageRequest(message=message)
            response_text = ''
            async for response in client.send_message(request_message):
                if response.HasField('message'):
                    response_text = ' '.join(part.text for part in response.message.parts if part.text)
                elif response.HasField('artifact_update'):
                    response_text = ' '.join(part.text for part in response.artifact_update.artifact.parts if part.text)
            status = 'complete'
            return response_text
        finally:
            await client.close() if 'client' in locals() else None
            if self.run_id:
                await telemetry.emit(self.run_id, 'A2A / compliance-review', f'A2A task {status}', 'protocol', protocol='A2A', status=status, duration_ms=round((time.perf_counter() - started) * 1000, 2), remote_agent=self.agent_url)
