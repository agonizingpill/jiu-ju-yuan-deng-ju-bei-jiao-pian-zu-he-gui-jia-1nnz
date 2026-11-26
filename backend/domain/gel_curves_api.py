from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import gel_curves_service as service
from domain.gel_curves_model import gel_curves
from domain.gel_curves_schemas import ScanGel, RecheckCurve

router = APIRouter()

@router.get('/gel_curves')
def list_gel_curves(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, gel_curves)


@router.post('/gel_curves/scan-gel')
def scan_gel(data: ScanGel, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.scan_gel(conn, user, data)
        record(conn, user, 'gel_curves.scan_gel')
        return output


@router.post('/gel_curves/recheck-curve')
def recheck_curve(data: RecheckCurve, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.recheck_curve(conn, user, data)
        record(conn, user, 'gel_curves.recheck_curve')
        return output
