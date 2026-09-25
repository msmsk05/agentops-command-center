from app.telemetry.events import telemetry


class RunRepository:
    """Persistence-honesty note: backed by an in-process TelemetryStore (dict/deque), not a database.

    Acceptable for the current single-replica Azure Container Apps deployment, but run/telemetry
    history does NOT survive a process restart or scale beyond one replica. If/when that changes,
    swap the internals of this class for a real store (e.g. Postgres/Redis) — callers only depend
    on this repository interface, not on TelemetryStore directly.
    """

    def get(self, run_id: str) -> dict | None:
        return telemetry.runs.get(run_id)

    def events(self, run_id: str) -> list[dict]:
        return list(telemetry.events.get(run_id, []))

    def list_runs(self) -> list[dict]:
        return list(telemetry.runs.values())


run_repository = RunRepository()
