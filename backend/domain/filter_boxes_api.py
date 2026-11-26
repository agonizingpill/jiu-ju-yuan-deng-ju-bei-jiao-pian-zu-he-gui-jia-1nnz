from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import filter_boxes_service as service
from domain.filter_boxes_model import filter_boxes
from domain.filter_boxes_schemas import StoreProfile, PullProfile

router = APIRouter()

@router.get('/filter_boxes')
def list_filter_boxes(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, filter_boxes)


@router.post('/filter_boxes/store-profile')
def store_profile(data: StoreProfile, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.store_profile(conn, user, data)
        record(conn, user, 'filter_boxes.store_profile')
        return output


@router.post('/filter_boxes/pull-profile')
def pull_profile(data: PullProfile, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.pull_profile(conn, user, data)
        record(conn, user, 'filter_boxes.pull_profile')
        return output
