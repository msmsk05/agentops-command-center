from fastapi import APIRouter, HTTPException

from app.repositories.runs import run_repository

router = APIRouter(prefix='/api/monitoring', tags=['monitoring'])


@router.get('/runs/{run_id}/trace')
async def trace(run_id: str) -> dict:
    run = run_repository.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='Run not found')
    return {'trace_id': run['trace_id'], 'session_id': run['session_id'], 'events': run_repository.events(run_id)}
