from fastapi import HTTPException
from sqlalchemy import select

from core.queueing import broker, submit, view
from core.records import get, insert, need, scan, update
from domain.gel_curves_model import gel_curves
from domain.color_profiles_model import color_profiles
from domain.filter_boxes_model import filter_boxes
from domain.learning import project_curve
from domain.nmf_baselines_model import nmf_baselines, profile_conversions


def _update_conversion(conn, row_id, **values):
    conn.execute(profile_conversions.update().where(
        profile_conversions.c.id == row_id).values(**values))
    return dict(conn.execute(select(profile_conversions).where(
        profile_conversions.c.id == row_id)).mappings().first())


def _rechecked_history(conn):
    return [row['bands'] for row in scan(conn, gel_curves) if row['rechecked']]


def active_baseline(conn, lock=False):
    query = select(nmf_baselines).where(nmf_baselines.c.status == 'active')
    if lock:
        query = query.with_for_update()
    row = conn.execute(query).mappings().first()
    if row is None:
        raise HTTPException(409, detail='尚无在用基准，请先由复核员建立统一基准')
    return dict(row)


def staged_baseline(conn, lock=False):
    query = select(nmf_baselines).where(nmf_baselines.c.status == 'staged')
    if lock:
        query = query.with_for_update()
    row = conn.execute(query.order_by(nmf_baselines.c.code)).mappings().first()
    return dict(row) if row is not None else None


def _stored_baseline(conn, code):
    return get(conn, nmf_baselines, code)


def list_baselines(conn):
    return scan(conn, nmf_baselines)


def build_baseline(conn, user, data):
    """复核员用复测曲线拟合新基准；建立期间不影响在用基准，归盒与调出照常。"""
    history = _rechecked_history(conn)
    need(len(history) >= 12, '复测曲线不足，无法建立统一基准')
    need(staged_baseline(conn) is None, '已有待切换基准，请先完成切换或处理换算')
    output = submit(user, {'kind': 'fit_baseline', 'history': history})
    return {'token': output['token'], 'status': output['status']}


def save_baseline(conn, user, data):
    run = _ready_result(user, data.token)
    metrics = run['result']
    # 再次确认没有并发建立的待切换基准。
    need(staged_baseline(conn) is None, '已有待切换基准，请先完成切换或处理换算')
    return insert(conn, nmf_baselines, code=data.code, components=metrics['components'],
                  references=metrics['references'], status='staged', token=data.token,
                  mean_error=metrics['mean_error'])


def _ready_result(user, token):
    record = view(user, token)
    if record['status'] != 'ready':
        raise HTTPException(409, detail='等待计算完成后再提交')
    return record


def _conversion_row(conn, baseline_code, profile_code, lock=False):
    query = select(profile_conversions).where(
        profile_conversions.c.baseline == baseline_code,
        profile_conversions.c.profile == profile_code)
    if lock:
        query = query.with_for_update()
    return conn.execute(query).mappings().first()


def _projection_payload(conn, user, baseline_code, profile):
    baseline = _stored_baseline(conn, baseline_code)
    curve = get(conn, gel_curves, profile['curve'])
    output = submit(user, {'kind': 'project', 'components': baseline['components'],
                           'target': {'code': curve['code'], 'bands': curve['bands']}})
    return output


def _credential_alive(token):
    # 计算凭据在 Redis 中有 24 小时 TTL，键不存在即视为过期。
    return bool(token) and bool(broker.exists(f'compute:{token}'))


def convert_profile(conn, user, data):
    """把在盒签条换算到待切换基准。

    排队中且凭据仍有效时不重复启用；换算失败或旧凭据过期后，用原曲线重新换算。
    """
    baseline = get(conn, nmf_baselines, data.baseline, lock=True)
    need(baseline['status'] == 'staged', '只有待切换基准可执行换算')
    profile = get(conn, color_profiles, data.profile, lock=True)
    existing = _conversion_row(conn, data.baseline, data.profile, lock=True)
    if existing is not None:
        existing = dict(existing)
        if existing['state'] == 'ready':
            return {'code': data.profile, 'baseline': data.baseline,
                    'state': 'ready', 'token': existing['token'], 'reused': True}
        if existing['state'] == 'pending' and _credential_alive(existing['token']):
            # 排队中且凭据有效：重试不重复启用，直接回传当前状态。
            return {'code': data.profile, 'baseline': data.baseline,
                    'state': 'pending', 'token': existing['token'], 'reused': True}
        # state=failed，或 pending 但凭据已过期：用原曲线重新换算。
        output = _projection_payload(conn, user, data.baseline, profile)
        _update_conversion(conn, existing['id'], weights=None, dominant=None,
                           error_value=None, token=output['token'],
                           state='pending', detail=None)
        return {'code': data.profile, 'baseline': data.baseline,
                'state': 'pending', 'token': output['token'], 'reused': False}
    output = _projection_payload(conn, user, data.baseline, profile)
    insert(conn, profile_conversions, baseline=data.baseline, profile=data.profile,
           weights=None, dominant=None, error_value=None, token=output['token'],
           state='pending', detail=None)
    return {'code': data.profile, 'baseline': data.baseline,
            'state': 'pending', 'token': output['token'], 'reused': False}


def settle_conversion(conn, user, data):
    """复核员根据换算计算结果落账：成功写新权重，失败保留旧基准找片路径。"""
    row = _conversion_row(conn, data.baseline, data.profile, lock=True)
    need(row is not None, '尚无换算任务，请先发起换算')
    row = dict(row)
    need(row['state'] == 'pending', '该签条换算已结算，无需重复处理')
    need(row['token'] == data.token, '凭据已更新，请用最新换算凭据结算')
    record = view(user, data.token)
    if record['status'] == 'rejected':
        _update_conversion(conn, row['id'], state='failed',
                           detail=record.get('detail', '换算被拒绝'))
        return {'code': data.profile, 'baseline': data.baseline, 'state': 'failed'}
    if record['status'] != 'ready':
        raise HTTPException(409, detail='等待换算计算完成后再结算')
    metrics = record['result']
    _update_conversion(conn, row['id'], weights=metrics['coefficients'],
                       dominant=metrics['dominant'], error_value=metrics['mean_error'],
                       token=data.token, state='ready', detail=None)
    return {'code': data.profile, 'baseline': data.baseline, 'state': 'ready',
            'weights': metrics['coefficients']}


def _box_profile_codes(conn):
    codes = []
    for box in scan(conn, filter_boxes):
        codes.extend(box['contents'])
    return codes


def conversion_status(conn):
    """汇总待切换基准与当时在盒签条的对账情况，供一次性切换判断。"""
    staged = staged_baseline(conn)
    if staged is None:
        return {'staged': None, 'in_box': [], 'pending': [], 'failed': [], 'ready': [],
                'matched': False}
    in_box = _box_profile_codes(conn)
    rows = [dict(x) for x in conn.execute(select(profile_conversions).where(
        profile_conversions.c.baseline == staged['code'])).mappings()]
    by_profile = {x['profile']: x for x in rows}
    pending, failed, ready = [], [], []
    for code in in_box:
        state = by_profile.get(code, {}).get('state')
        if state == 'ready':
            ready.append(code)
        elif state == 'failed':
            failed.append(code)
        else:
            pending.append(code)
    return {'staged': staged['code'], 'in_box': in_box, 'pending': pending,
            'failed': failed, 'ready': ready, 'matched': not pending and not failed and bool(in_box)}


def activate_baseline(conn, user, data):
    """待切换基准与当时在盒签条全部对上后，一次性切换为在用基准。"""
    staged = staged_baseline(conn, lock=True)
    need(staged is not None, '没有待切换基准')
    if data.baseline is not None:
        need(staged['code'] == data.baseline, '指定基准与当前待切换基准不一致')
    status = conversion_status(conn)
    need(status['matched'], '新谱与在盒签条尚未全部换算成功，不能切换')
    current = active_baseline(conn, lock=True)
    # 旧基准退役，在盒签条权重整体改写为新基准换算结果。
    update(conn, nmf_baselines, current['code'], status='retired')
    for code in status['ready']:
        row = dict(_conversion_row(conn, staged['code'], code, lock=True))
        update(conn, color_profiles, code, weights=row['weights'], dominant=row['dominant'],
               error_value=row['error_value'], baseline=staged['code'])
    update(conn, nmf_baselines, staged['code'], status='active')
    return get(conn, nmf_baselines, staged['code'])


def weights_on_active(conn, profile):
    """返回签条在在用基准下的权重；晚到签条按在用基准换算，凭据过期则用原曲线重算。"""
    baseline = active_baseline(conn)
    if profile.get('baseline') == baseline['code']:
        return profile['weights'], baseline
    # 晚到的旧计算签条：没有在用基准权重，用原曲线即时投影，不写库、不改原凭据。
    curve = get(conn, gel_curves, profile['curve'])
    metrics = project_curve({'components': baseline['components'], 'bands': curve['bands']})
    return metrics['coefficients'], baseline
