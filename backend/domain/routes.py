from domain.gel_reels_api import router as gel_reels
from domain.gel_curves_api import router as gel_curves
from domain.color_profiles_api import router as color_profiles
from domain.filter_boxes_api import router as filter_boxes

routers = (gel_reels, gel_curves, color_profiles, filter_boxes,)
