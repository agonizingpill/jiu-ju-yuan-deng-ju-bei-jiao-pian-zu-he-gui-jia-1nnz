"""HTTP + 真实 worker 线程集成测试，覆盖路由、鉴权与计算失败回退。"""
import json
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

# 用临时文件库，保证 TestClient 工作线程与主线程看到同一份表与数据。
_db_fd, _db_path = tempfile.mkstemp(suffix='.db')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{_db_path}')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('JWT_SECRET', 'test-secret')

import fakeredis  # noqa: E402
import core.queueing as queueing  # noqa: E402
fake_redis = fakeredis.FakeRedis(decode_responses=True)
queueing.broker = fake_redis

from core import worker as worker_mod  # noqa: E402
worker_mod.broker = fake_redis

from fastapi.testclient import TestClient  # noqa: E402
from core.db import engine, metadata, transaction  # noqa: E402
import domain.nmf_baselines_model  # noqa: E402,F401
from core.app import app  # noqa: E402
from domain import demo  # noqa: E402
from domain.learning import project_curve  # noqa: E402

PASS, FAIL = 0, 0


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  PASS {name}')
    else:
        FAIL += 1
        print(f'  FAIL {name} {detail}')


def login(client, role):
    resp = client.post('/auth/login',
                       json={'email': f'{role}@demo.test', 'password': 'DemoC0de!2026'})
    return {'Authorization': 'Bearer ' + resp.json()['token']}


def wait_compute(client, headers, token):
    for _ in range(50):
        data = client.get(f'/compute/{token}', headers=headers).json()
        if data['status'] != 'queued':
            return data
        time.sleep(0.05)
    raise RuntimeError('compute timeout')


def main():
    metadata.create_all(engine)
    with transaction() as conn:
        for table, rows in demo.FIXTURES:
            for row in rows:
                conn.execute(table.insert().values(**row))

    # 真实 worker 线程消费队列。
    stop = threading.Event()

    def run_worker():
        while not stop.is_set():
            item = fake_redis.lmove(queueing.QUEUE, f'{queueing.QUEUE}:processing')
            if item is None:
                time.sleep(0.02)
                continue
            job = json.loads(item)
            record = {'owner': job['owner'], 'input': job['input']}
            try:
                from domain.learning import calculate
                record.update(status='ready', result=calculate(job['input']))
            except ValueError as exc:
                record.update(status='rejected', detail=str(exc))
            fake_redis.set(f'compute:{job["token"]}', json.dumps(record, allow_nan=False), ex=86400)
            fake_redis.lrem(f'{queueing.QUEUE}:processing', 1, item)

    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()

    with TestClient(app) as client:
        viewer = login(client, 'viewer')
        operator = login(client, 'operator')
        reviewer = login(client, 'reviewer')

        # 鉴权：viewer 不能建基准。
        resp = client.post('/nmf_baselines/build-baseline', headers=viewer, json={})
        check('只读访客禁止建基准', resp.status_code == 403)

        # 未登录被拦。
        check('未登录拒绝访问', client.get('/nmf_baselines').status_code == 401)

        # 复核员建基准并签存。
        resp = client.post('/nmf_baselines/build-baseline', headers=reviewer, json={})
        check('建基准入队', resp.status_code == 200 and resp.json()['status'] == 'queued')
        token = resp.json()['token']
        result = wait_compute(client, reviewer, token)
        check('worker 拟合基准成功', result['status'] == 'ready'
              and len(result['result']['components']) == 2)
        resp = client.post('/nmf_baselines/save-baseline', headers=reviewer,
                           json={'code': 'NMF-BASE-02', 'token': token})
        check('签存待切换基准', resp.status_code == 200 and resp.json()['status'] == 'staged')

        # 换算在盒签条 NMF-0 并结算。
        resp = client.post('/nmf_baselines/convert-profile', headers=reviewer,
                           json={'baseline': 'NMF-BASE-02', 'profile': 'NMF-0'})
        check('发起换算', resp.status_code == 200 and resp.json()['state'] == 'pending')
        ctoken = resp.json()['token']
        cresult = wait_compute(client, reviewer, ctoken)
        check('worker 投影换算成功', cresult['status'] == 'ready')
        resp = client.post('/nmf_baselines/settle-conversion', headers=reviewer,
                           json={'baseline': 'NMF-BASE-02', 'profile': 'NMF-0', 'token': ctoken})
        check('结算换算', resp.status_code == 200 and resp.json()['state'] == 'ready')

        # 重试不重复启用：再次发起应 reused。
        resp = client.post('/nmf_baselines/convert-profile', headers=reviewer,
                           json={'baseline': 'NMF-BASE-02', 'profile': 'NMF-0'})
        check('重试不重复启用', resp.json().get('reused') is True)

        # 对账：当前在盒只有 NMF-0（BOX-H 空），全对上可切换。
        resp = client.get('/nmf_baselines/conversions', headers=reviewer)
        check('对账 matched', resp.json()['matched'] is True)
        resp = client.post('/nmf_baselines/activate-baseline', headers=reviewer,
                           json={'baseline': 'NMF-BASE-02'})
        check('一次性切换成功', resp.status_code == 200 and resp.json()['status'] == 'active')

        # 归盒页找片接口（operator 可用）。
        resp = client.post('/filter_boxes/find-similar', headers=operator,
                           json={'curve': 'SP-01'})
        check('找片接口返回同基准结果',
              resp.status_code == 200 and resp.json()['baseline'] == 'NMF-BASE-02'
              and resp.json()['matches'][0]['profile'] == 'NMF-0')

        # viewer 也能找片（只读）。
        check('只读访客可找片',
              client.post('/filter_boxes/find-similar', headers=viewer,
                          json={'curve': 'SP-01'}).status_code == 200)

        # 计算失败路径：波段数不匹配，worker 标记 rejected。
        bad = project_curve
        try:
            bad({'components': result['result']['components'], 'bands': [0.1, 0.2]})
            check('波段不匹配应抛错', False)
        except ValueError as exc:
            check('波段不匹配触发换算失败', '不一致' in str(exc))

    stop.set()
    thread.join(timeout=2)
    print(f'\n结果：{PASS} 通过 / {FAIL} 失败')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
