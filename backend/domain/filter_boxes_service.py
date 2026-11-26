import numpy as np

from core.records import get, need, scan, update
from domain.gel_reels_model import gel_reels
from domain.gel_curves_model import gel_curves
from domain.color_profiles_model import color_profiles
from domain.filter_boxes_model import filter_boxes
from domain.learning import project_curve
from domain.nmf_baselines_service import active_baseline, weights_on_active


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


def _cosine_similarity(left, right):
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return round(float(np.dot(a, b) / denominator), 4)


def find_similar(conn, user, data):
    """待找色片与在盒签条使用同一套在用基准换算后，比较权重相似度。"""
    target_curve = get(conn, gel_curves, data.curve)
    baseline = active_baseline(conn)
    target_weights = project_curve(
        {'components': baseline['components'], 'bands': target_curve['bands']})['coefficients']

    profiles = {row['code']: row for row in scan(conn, color_profiles)}
    matches = []
    for box in scan(conn, filter_boxes):
        for profile_code in box['contents']:
            profile = profiles.get(profile_code)
            if profile is None:
                continue
            # 晚到的旧计算签条按在用基准即时换算；旧凭据过期则用原曲线重算。
            weights, _ = weights_on_active(conn, profile)
            matches.append({
                'box': box['code'],
                'profile': profile_code,
                'curve': profile['curve'],
                'similarity': _cosine_similarity(target_weights, weights),
                'weights': weights,
            })
    matches.sort(key=lambda item: item['similarity'], reverse=True)
    return {'baseline': baseline['code'], 'curve': data.curve,
            'weights': target_weights, 'matches': matches}
