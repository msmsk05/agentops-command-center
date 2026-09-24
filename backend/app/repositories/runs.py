from app.telemetry.events import telemetry


class RunRepository:
    def get(self, run_id: str) -> dict | None:
        return telemetry.runs.get(run_id)

    def events(self, run_id: str) -> list[dict]:
        return list(telemetry.events.get(run_id, []))


run_repository = RunRepository()
