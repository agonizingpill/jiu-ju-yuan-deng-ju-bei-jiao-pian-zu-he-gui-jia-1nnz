from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import gel_reels_service as service
from domain.gel_reels_model import gel_reels
from domain.gel_reels_schemas import OpenLightTable

router = APIRouter()

@router.get('/gel_reels')
def list_gel_reels(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, gel_reels)


@router.post('/gel_reels/open-light-table')
def open_light_table(data: OpenLightTable, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.open_light_table(conn, user, data)
        record(conn, user, 'gel_reels.open_light_table')
        return output
