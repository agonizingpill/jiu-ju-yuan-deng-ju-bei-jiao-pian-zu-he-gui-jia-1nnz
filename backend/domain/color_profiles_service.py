from core.queueing import submit, result
from core.records import get, insert, need
from domain.gel_curves_model import gel_curves
from domain.color_profiles_model import color_profiles
from domain.nmf_baselines_service import active_baseline


def decompose_gel(conn, user, data):
    target = get(conn, gel_curves, data.curve)
    need(target['rechecked'], '目标曲线尚未复测，无法分解')
    # 全部签条投影到同一套在用基准，权重才可比、才能据此找相近备片。
    baseline = active_baseline(conn)
    return submit(user, {'kind': 'project', 'components': baseline['components'],
                         'target': {'code': target['code'], 'bands': target['bands']}})


def save_components(conn, user, data):
    run = result(user, data.token)
    metrics = run['result']
    # 记录签条所依据的在用基准，便于后续基准换版时识别晚到的旧计算签条。
    baseline = active_baseline(conn)
    return insert(conn, color_profiles, code=data.code, curve=run['input']['target']['code'],
                  weights=metrics['coefficients'], dominant=metrics['dominant'],
                  error_value=metrics['mean_error'], token=data.token, baseline=baseline['code'])
