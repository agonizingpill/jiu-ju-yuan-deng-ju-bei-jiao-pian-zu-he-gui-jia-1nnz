from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from domain import nmf_baselines_service as service
from domain.nmf_baselines_schemas import (
    ActivateBaseline, BuildBaseline, ConvertProfile, SaveBaseline, SettleConversion)

router = APIRouter()


@router.get('/nmf_baselines')
def list_baselines(user=Depends(actor)):
    with transaction() as conn:
        return service.list_baselines(conn)


@router.get('/nmf_baselines/conversions')
def conversion_status(user=Depends(actor)):
    with transaction() as conn:
        return service.conversion_status(conn)


@router.post('/nmf_baselines/build-baseline')
def build_baseline(data: BuildBaseline, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.build_baseline(conn, user, data)
        record(conn, user, 'nmf_baselines.build_baseline')
        return output


@router.post('/nmf_baselines/save-baseline')
def save_baseline(data: SaveBaseline, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.save_baseline(conn, user, data)
        record(conn, user, 'nmf_baselines.save_baseline')
        return output


@router.post('/nmf_baselines/convert-profile')
def convert_profile(data: ConvertProfile, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.convert_profile(conn, user, data)
        record(conn, user, 'nmf_baselines.convert_profile')
        return output


@router.post('/nmf_baselines/settle-conversion')
def settle_conversion(data: SettleConversion, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.settle_conversion(conn, user, data)
        record(conn, user, 'nmf_baselines.settle_conversion')
        return output


@router.post('/nmf_baselines/activate-baseline')
def activate_baseline(data: ActivateBaseline, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.activate_baseline(conn, user, data)
        record(conn, user, 'nmf_baselines.activate_baseline')
        return output
