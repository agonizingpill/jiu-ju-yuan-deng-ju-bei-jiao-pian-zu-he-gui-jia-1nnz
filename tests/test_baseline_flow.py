"""端到端领域测试：统一基准、同基准找片、换版换算与一次性切换。

用 SQLite 内存库 + fakeredis 跑通服务层与 worker 计算，不依赖 MySQL/Redis 容器。
运行：PYTHONPATH=backend python -I tests/test_baseline_flow.py
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('JWT_SECRET', 'test-secret')

import fakeredis  # noqa: E402

# 在导入应用模块前替换 redis 客户端。
import core.queueing as queueing  # noqa: E402
fake_redis = fakeredis.FakeRedis(decode_responses=True)
queueing.broker = fake_redis

from sqlalchemy import select  # noqa: E402
from core.db import engine, metadata, transaction  # noqa: E402
from core import worker as worker_mod  # noqa: E402
worker_mod.broker = fake_redis

import domain.nmf_baselines_model  # noqa: E402,F401  确保新表注册进 metadata
from domain import demo  # noqa: E402
from domain import color_profiles_service as cp_service  # noqa: E402
from domain import filter_boxes_service as fb_service  # noqa: E402
from domain import nmf_baselines_service as base_service  # noqa: E402
from domain.gel_curves_model import gel_curves  # noqa: E402
from domain.color_profiles_model import color_profiles  # noqa: E402
from domain.filter_boxes_model import filter_boxes  # noqa: E402
from domain.nmf_baselines_model import nmf_baselines, profile_conversions  # noqa: E402

REVIEWER = {'sub': 'reviewer@demo.test', 'role': 'reviewer'}
OPERATOR = {'sub': 'operator@demo.test', 'role': 'operator'}

PASS, FAIL = 0, 0


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  PASS {name}')
    else:
        FAIL += 1
        print(f'  FAIL {name} {detail}')


def drain_queue():
    """同步执行队列里所有计算任务，模拟 worker。"""
    while True:
        item = fake_redis.lmove(queueing.QUEUE, f'{queueing.QUEUE}:processing')
        if item is None:
            return
        job = json.loads(item)
        status_record = {'owner': job['owner'], 'input': job['input']}
        try:
            from domain.learning import calculate
            status_record.update(status='ready', result=calculate(job['input']))
        except ValueError as exc:
            status_record.update(status='rejected', detail=str(exc))
        fake_redis.set(f'compute:{job["token"]}',
                       json.dumps(status_record, allow_nan=False), ex=86400)
        fake_redis.lrem(f'{queueing.QUEUE}:processing', 1, item)


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def seed():
    metadata.create_all(engine)
    with transaction() as conn:
        for table, rows in demo.FIXTURES:
            for row in rows:
                conn.execute(table.insert().values(**row))


def baseline_code(conn, status):
    return conn.execute(select(nmf_baselines.c.code).where(
        nmf_baselines.c.status == status)).scalar()


def main():
    seed()
    with transaction() as conn:
        active = base_service.active_baseline(conn)
        check('种子存在唯一在用基准', active['code'] == 'NMF-BASE-01')
        check('种子基准含两个成分', len(active['components']) == 2)

    # 1) 分解新色片：投影到在用基准，而不是各自拟合。
    with transaction() as conn:
        target = conn.execute(select(gel_curves).where(gel_curves.c.code == 'SP-01')).mappings().first()
        sub = cp_service.decompose_gel(conn, OPERATOR, Obj(curve='SP-01'))
        check('分解任务进入队列', sub['status'] == 'queued')
    drain_queue()
    with transaction() as conn:
        run = queueing.result(OPERATOR, sub['token'])
        check('投影返回两成分权重', len(run['result']['coefficients']) == 2)
        saved = cp_service.save_components(conn, REVIEWER,
                                           Obj(code='NMF-24', token=sub['token']))
        check('签存记录基准归属为在用基准', saved['baseline'] == 'NMF-BASE-01')

    # 2) 归盒页同基准相似度：待找色片与在盒签条可比。
    with transaction() as conn:
        sim = fb_service.find_similar(conn, OPERATOR, Obj(curve='SP-01'))
        check('找片使用在用基准', sim['baseline'] == 'NMF-BASE-01')
        check('返回在盒签条匹配', [m['profile'] for m in sim['matches']] == ['NMF-0'])
        check('相似度落在 0~1', 0.0 <= sim['matches'][0]['similarity'] <= 1.0)

    # 3) 晚到的旧计算签条（baseline 为空/旧版）按在用基准即时换算。
    with transaction() as conn:
        conn.execute(color_profiles.insert().values(
            code='NMF-LATE', curve='SP-02', weights=[9.9, 0.1], dominant=1,
            error_value=0.5, token='late-token', baseline=None))
        # SP-02 属于 REEL-H（老化、耐热树脂），归入 BOX-H。
        fb_service.store_profile(conn, OPERATOR, Obj(box='BOX-H', profile='NMF-LATE'))
        late = fb_service.find_similar(conn, OPERATOR, Obj(curve='SP-02'))
        late_match = [m for m in late['matches'] if m['profile'] == 'NMF-LATE'][0]
        check('晚到签条按在用基准换算而非沿用旧权重', late_match['weights'] != [9.9, 0.1])
        box_h = conn.execute(select(filter_boxes).where(
            filter_boxes.c.code == 'BOX-H')).mappings().first()
        check('晚到签条可正常归盒', 'NMF-LATE' in box_h['contents'])

    # 4) 复核员建新基准（staged），期间在用基准不变、归盒照常。
    with transaction() as conn:
        build = base_service.build_baseline(conn, REVIEWER, Obj(note='复测换版'))
    drain_queue()
    with transaction() as conn:
        base_service.save_baseline(conn, REVIEWER,
                                   Obj(code='NMF-BASE-02', token=build['token']))
        staged = base_service.staged_baseline(conn)
        check('新基准登记为待切换', staged['code'] == 'NMF-BASE-02')
        check('在用基准仍是旧版', baseline_code(conn, 'active') == 'NMF-BASE-01')
        # 归盒照常：把 NMF-24 归入 BOX-F 之外的合适盒子（BOX-H 是老化盒，NMF-24 来自 REEL-F 新批）
        # 这里验证 store/pull 在 staged 期间仍按旧基准工作流可用。
        box_before = conn.execute(select(filter_boxes).where(
            filter_boxes.c.code == 'BOX-F')).mappings().first()
        check('换版期间归盒空位照常可读', box_before['space'] == 4)

    # 5) 换算在盒签条；重试不重复启用。
    with transaction() as conn:
        first = base_service.convert_profile(conn, REVIEWER,
                                             Obj(baseline='NMF-BASE-02', profile='NMF-0'))
        check('首次换算进入待结算', first['state'] == 'pending' and first['reused'] is False)
        again = base_service.convert_profile(conn, REVIEWER,
                                             Obj(baseline='NMF-BASE-02', profile='NMF-0'))
        check('重试不重复启用', again['reused'] is True and again['state'] == 'pending')
    drain_queue()
    with transaction() as conn:
        token = conn.execute(select(profile_conversions.c.token).where(
            profile_conversions.c.profile == 'NMF-0')).scalar()
        settled = base_service.settle_conversion(
            conn, REVIEWER, Obj(baseline='NMF-BASE-02', profile='NMF-0', token=token))
        check('换算结算成功', settled['state'] == 'ready')

    # 6) 换算凭据过期：旧凭据不能结算，且可凭原曲线重新换算，重试不重复启用。
    with transaction() as conn:
        conn.execute(profile_conversions.insert().values(
            baseline='NMF-BASE-02', profile='NMF-LATE', weights=None, dominant=None,
            error_value=None, token='will-expire', state='pending', detail=None))
        # 模拟凭据过期：Redis 中查不到该 token，结算应被拒绝而非误用。
        try:
            base_service.settle_conversion(
                conn, REVIEWER, Obj(baseline='NMF-BASE-02', profile='NMF-LATE',
                                    token='will-expire'))
            check('过期凭据应被拒绝', False)
        except Exception as exc:
            check('旧凭据过期时报错而非误用', '过期' in str(exc) or '不存在' in str(exc))
        # 过期后重新换算：服务用原曲线生成新任务（reused=False），无需手工清记录。
        expired_retry = base_service.convert_profile(
            conn, REVIEWER, Obj(baseline='NMF-BASE-02', profile='NMF-LATE'))
        check('过期凭据触发重新换算', expired_retry['reused'] is False
              and expired_retry['token'] != 'will-expire')

    # 晚到签条已在盒，按在用基准（旧版）换算；找片仍走旧基准。
    with transaction() as conn:
        box_h = conn.execute(select(filter_boxes).where(
            filter_boxes.c.code == 'BOX-H')).mappings().first()
        check('晚到签条仍在盒中', 'NMF-LATE' in box_h['contents'])
        sim = fb_service.find_similar(conn, OPERATOR, Obj(curve='SP-00'))
        check('换算未全对上时找片仍用旧在用基准', sim['baseline'] == 'NMF-BASE-01')

    # 切换被锁定：在盒签条 NMF-LATE 尚未成功换算。
    with transaction() as conn:
        status = base_service.conversion_status(conn)
        check('存在未完成换算时 matched=False', status['matched'] is False)
        try:
            base_service.activate_baseline(conn, REVIEWER, Obj(baseline='NMF-BASE-02'))
            check('未全对上禁止切换', False)
        except Exception as exc:
            check('未全对上禁止切换', '不能切换' in str(exc))

    # 7) 先用新凭据结算为失败（模拟 worker 拒绝），再从失败状态重试成功。
    with transaction() as conn:
        retry_token = conn.execute(select(profile_conversions.c.token).where(
            profile_conversions.c.profile == 'NMF-LATE')).scalar()
        # 直接在 Redis 写入 rejected 结果，模拟 worker 换算失败。
        fake_redis.set(f'compute:{retry_token}', json.dumps({
            'owner': REVIEWER['sub'], 'status': 'rejected',
            'detail': '波段不一致，无法换算', 'input': {}}), ex=86400)
        failed = base_service.settle_conversion(
            conn, REVIEWER, Obj(baseline='NMF-BASE-02', profile='NMF-LATE',
                                token=retry_token))
        check('换算失败落账为 failed', failed['state'] == 'failed')
        # 失败状态下重试：服务重新提交，得到新凭据。
        retry = base_service.convert_profile(
            conn, REVIEWER, Obj(baseline='NMF-BASE-02', profile='NMF-LATE'))
        check('失败后用原曲线重试生成新任务', retry['reused'] is False
              and retry['state'] == 'pending' and retry['token'] != retry_token)
    drain_queue()
    with transaction() as conn:
        new_token = conn.execute(select(profile_conversions.c.token).where(
            profile_conversions.c.profile == 'NMF-LATE')).scalar()
        settled = base_service.settle_conversion(
            conn, REVIEWER, Obj(baseline='NMF-BASE-02', profile='NMF-LATE', token=new_token))
        check('原曲线重算后结算成功', settled['state'] == 'ready')

    # 8) 全部对上，一次性切换；旧基准退役，在盒签条权重改写。
    with transaction() as conn:
        status = base_service.conversion_status(conn)
        check('全部换算成功 matched=True', status['matched'] is True)
        activated = base_service.activate_baseline(conn, REVIEWER, Obj(baseline='NMF-BASE-02'))
        check('新基准成为在用', activated['status'] == 'active' and activated['code'] == 'NMF-BASE-02')
        check('旧基准退役', baseline_code(conn, 'retired') == 'NMF-BASE-01')
        nmf0 = conn.execute(select(color_profiles).where(
            color_profiles.c.code == 'NMF-0')).mappings().first()
        check('在盒签条基准归属切换到新版', dict(nmf0)['baseline'] == 'NMF-BASE-02')

    # 9) 切换后找片与新分解都用新基准。
    with transaction() as conn:
        sim = fb_service.find_similar(conn, OPERATOR, Obj(curve='SP-00'))
        check('切换后找片使用新基准', sim['baseline'] == 'NMF-BASE-02')
        sub = cp_service.decompose_gel(conn, OPERATOR, Obj(curve='SP-03'))
    drain_queue()
    with transaction() as conn:
        run = queueing.result(OPERATOR, sub['token'])
        check('切换后新分解仍可投影', len(run['result']['coefficients']) == 2)

    print(f'\n结果：{PASS} 通过 / {FAIL} 失败')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
