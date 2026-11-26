from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import color_profiles_service as service
from domain.color_profiles_model import color_profiles
from domain.color_profiles_schemas import DecomposeGel, SaveComponents

router = APIRouter()

@router.get('/color_profiles')
def list_color_profiles(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, color_profiles)


@router.post('/color_profiles/decompose-gel')
def decompose_gel(data: DecomposeGel, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.decompose_gel(conn, user, data)
        record(conn, user, 'color_profiles.decompose_gel')
        return output


@router.post('/color_profiles/save-components')
def save_components(data: SaveComponents, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.save_components(conn, user, data)
        record(conn, user, 'color_profiles.save_components')
        return output
