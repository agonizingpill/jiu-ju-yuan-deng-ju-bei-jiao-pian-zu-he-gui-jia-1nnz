from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.gel_reels_model import gel_reels
from domain.gel_curves_model import gel_curves
from domain.color_profiles_model import color_profiles
from domain.filter_boxes_model import filter_boxes


def store_profile(conn, user, data):
    signed=get(conn,color_profiles,data.profile,lock=True)
    curve=get(conn,gel_curves,signed['curve'])
    reel=get(conn,gel_reels,curve['reel'])
    box=get(conn,filter_boxes,data.box,lock=True)
    need(box['kind']==reel['family'] and box['aged']==reel['aged'],'新批与老化胶片或不同介质不得混归')
    need(box['space']>0,'收纳盒无空位')
    need(not any(data.profile in row['contents'] for row in scan(conn,filter_boxes)),'此签条已经归盒')
    return update(conn,filter_boxes,data.box,space=box['space']-1,contents=box['contents']+[data.profile])


def pull_profile(conn, user, data):
    get(conn,color_profiles,data.profile,lock=True)
    box=get(conn,filter_boxes,data.box,lock=True)
    need(data.profile in box['contents'],'指定片盒未收录此签条')
    return update(conn,filter_boxes,data.box,space=box['space']+1,
      contents=[item for item in box['contents'] if item!=data.profile])
