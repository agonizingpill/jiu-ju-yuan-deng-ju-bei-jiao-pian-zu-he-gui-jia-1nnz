from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.gel_reels_model import gel_reels
from domain.gel_curves_model import gel_curves
from domain.color_profiles_model import color_profiles
from domain.filter_boxes_model import filter_boxes


def scan_gel(conn, user, data):
    reel=get(conn,gel_reels,data.reel)
    need(reel['eligible'],'暂不可上光台')
    need(isinstance(data.bands,list) and len(data.bands)==4 and all(type(x) in (int,float) and 0<=x<=1 for x in data.bands),
         '需四个在 0 到 1 内的有限透过率')
    return insert(conn,gel_curves,**data.model_dump(),rechecked=False)


def recheck_curve(conn, user, data):
    x=get(conn,gel_curves,data.curve,lock=True)
    need(get(conn,gel_reels,x['reel'])['eligible'],'胶片状态不允许签认')
    return update(conn,gel_curves,data.curve,rechecked=True)
