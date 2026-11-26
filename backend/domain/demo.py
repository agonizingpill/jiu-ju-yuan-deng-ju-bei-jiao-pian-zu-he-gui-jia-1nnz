from domain.gel_reels_model import gel_reels
from domain.gel_curves_model import gel_curves
from domain.nmf_baselines_model import nmf_baselines
from domain.color_profiles_model import color_profiles
from domain.filter_boxes_model import filter_boxes
from domain.learning import fit_baseline, project_curve

_reel_rows = [{'code': 'REEL-H', 'family': '耐热树脂', 'aged': True, 'eligible': True},
 {'code': 'REEL-F', 'family': '耐热树脂', 'aged': False, 'eligible': True},
 {'code': 'REEL-J', 'family': '覆膜', 'aged': False, 'eligible': False}]

_curve_rows = [{'code': 'SP-00',
  'reel': 'REEL-H',
  'bands': [0.08, 0.27, 0.68, 0.78],
  'rechecked': True},
 {'code': 'SP-01',
  'reel': 'REEL-F',
  'bands': [0.817, 0.497, 0.247, 0.137],
  'rechecked': True},
 {'code': 'SP-02',
  'reel': 'REEL-H',
  'bands': [0.834, 0.514, 0.264, 0.154],
  'rechecked': True},
 {'code': 'SP-03',
  'reel': 'REEL-F',
  'bands': [0.131, 0.321, 0.731, 0.831],
  'rechecked': True},
 {'code': 'SP-04',
  'reel': 'REEL-H',
  'bands': [0.868, 0.548, 0.298, 0.188],
  'rechecked': True},
 {'code': 'SP-05', 'reel': 'REEL-F', 'bands': [0.8, 0.48, 0.23, 0.12], 'rechecked': True},
 {'code': 'SP-06',
  'reel': 'REEL-H',
  'bands': [0.097, 0.287, 0.697, 0.797],
  'rechecked': True},
 {'code': 'SP-07',
  'reel': 'REEL-F',
  'bands': [0.834, 0.514, 0.264, 0.154],
  'rechecked': True},
 {'code': 'SP-08',
  'reel': 'REEL-H',
  'bands': [0.851, 0.531, 0.281, 0.171],
  'rechecked': True},
 {'code': 'SP-09',
  'reel': 'REEL-F',
  'bands': [0.148, 0.338, 0.748, 0.848],
  'rechecked': True},
 {'code': 'SP-10', 'reel': 'REEL-H', 'bands': [0.8, 0.48, 0.23, 0.12], 'rechecked': True},
 {'code': 'SP-11',
  'reel': 'REEL-F',
  'bands': [0.817, 0.497, 0.247, 0.137],
  'rechecked': True},
 {'code': 'SP-12',
  'reel': 'REEL-H',
  'bands': [0.114, 0.304, 0.714, 0.814],
  'rechecked': True},
 {'code': 'SP-13',
  'reel': 'REEL-F',
  'bands': [0.851, 0.531, 0.281, 0.171],
  'rechecked': True},
 {'code': 'SP-14',
  'reel': 'REEL-H',
  'bands': [0.868, 0.548, 0.298, 0.188],
  'rechecked': True},
 {'code': 'SP-15',
  'reel': 'REEL-F',
  'bands': [0.08, 0.27, 0.68, 0.78],
  'rechecked': True},
 {'code': 'SP-16',
  'reel': 'REEL-H',
  'bands': [0.817, 0.497, 0.247, 0.137],
  'rechecked': True},
 {'code': 'SP-17',
  'reel': 'REEL-F',
  'bands': [0.834, 0.514, 0.264, 0.154],
  'rechecked': True},
 {'code': 'SP-18',
  'reel': 'REEL-H',
  'bands': [0.131, 0.321, 0.731, 0.831],
  'rechecked': True},
 {'code': 'SP-19',
  'reel': 'REEL-F',
  'bands': [0.868, 0.548, 0.298, 0.188],
  'rechecked': True},
 {'code': 'SP-20', 'reel': 'REEL-H', 'bands': [0.8, 0.48, 0.23, 0.12], 'rechecked': True},
 {'code': 'SP-21',
  'reel': 'REEL-F',
  'bands': [0.097, 0.287, 0.697, 0.797],
  'rechecked': True},
 {'code': 'SP-22',
  'reel': 'REEL-H',
  'bands': [0.834, 0.514, 0.264, 0.154],
  'rechecked': True},
 {'code': 'SP-23',
  'reel': 'REEL-F',
  'bands': [0.851, 0.531, 0.281, 0.171],
  'rechecked': True}]


def _seed_baseline():
    """用全部复测曲线拟合初始在用基准，使所有签条与找片共用同一套基准。"""
    fit = fit_baseline({'history': [row['bands'] for row in _curve_rows]})
    return {'code': 'NMF-BASE-01', 'components': fit['components'],
            'references': fit['references'], 'status': 'active',
            'token': 'fixture-baseline', 'mean_error': fit['mean_error']}


_baseline_rows = [_seed_baseline()]


def _seed_profile():
    # 让历史签条 NMF-0 的权重与在用基准自洽：把来源曲线 SP-03 投影到该基准。
    baseline = _baseline_rows[0]
    bands = next(row['bands'] for row in _curve_rows if row['code'] == 'SP-03')
    metrics = project_curve({'components': baseline['components'], 'bands': bands})
    return {'code': 'NMF-0', 'curve': 'SP-03', 'weights': metrics['coefficients'],
            'dominant': metrics['dominant'], 'error_value': metrics['mean_error'],
            'token': 'fixture', 'baseline': baseline['code']}


_profile_rows = [_seed_profile()]

_box_rows = [{'code': 'BOX-F', 'kind': '耐热树脂', 'aged': False, 'space': 4, 'contents': ['NMF-0']},
 {'code': 'BOX-H', 'kind': '耐热树脂', 'aged': True, 'space': 2, 'contents': []}]

FIXTURES = [
    (gel_reels, _reel_rows),
    (gel_curves, _curve_rows),
    (nmf_baselines, _baseline_rows),
    (color_profiles, _profile_rows),
    (filter_boxes, _box_rows),
]
