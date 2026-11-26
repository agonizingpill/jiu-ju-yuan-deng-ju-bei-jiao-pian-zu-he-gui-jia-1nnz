from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.gel_reels_model import gel_reels
from domain.gel_curves_model import gel_curves
from domain.color_profiles_model import color_profiles
from domain.filter_boxes_model import filter_boxes


def decompose_gel(conn, user, data):
    target=get(conn,gel_curves,data.curve)
    history=[x['bands'] for x in scan(conn,gel_curves) if x['rechecked'] and x['code']!=data.curve]
    need(target['rechecked'] and len(history)>=12,'目标或历史复测不足')
    return submit(user,{'target':target,'history':history})


def save_components(conn, user, data):
    run=result(user,data.token); metrics=run['result']
    return insert(conn,color_profiles,code=data.code,curve=run['input']['target']['code'],
       weights=metrics['coefficients'],dominant=metrics['dominant'],error_value=metrics['mean_error'],token=data.token)
