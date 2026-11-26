from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.gel_reels_model import gel_reels
from domain.gel_curves_model import gel_curves
from domain.color_profiles_model import color_profiles
from domain.filter_boxes_model import filter_boxes


def open_light_table(conn, user, data):
    get(conn,gel_reels,data.reel,lock=True)
    return update(conn,gel_reels,data.reel,eligible=data.eligible)
