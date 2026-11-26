import numpy as np
from sklearn.decomposition import NMF


def _round_coefficients(values):
    return np.asarray(values, dtype=float).round(4).tolist()


def fit_baseline(data):
    """用全部复测曲线拟合一套共享 NMF 基准，返回成分矩阵与基准重构均误。"""
    history = np.asarray(data['history'], dtype=float)
    model = NMF(n_components=2, init='nndsvda', max_iter=1000, random_state=24)
    coefficients = model.fit_transform(history)
    reconstruction = coefficients @ model.components_
    mean_error = round(float(np.mean(np.abs(reconstruction - history))), 5)
    return {
        'components': model.components_.round(6).tolist(),
        'references': int(len(history)),
        'mean_error': mean_error,
    }


def project_curve(data):
    """把单条曲线投影到一套既有基准的成分上，不再各自拟合新模型。"""
    components = np.asarray(data['components'], dtype=float)
    observation = np.asarray(data['bands'], dtype=float).reshape(1, -1)
    if observation.shape[1] != components.shape[1]:
        raise ValueError('曲线波段数与基准成分不一致，无法换算')
    # 非负最小二乘投影：固定基准，只解系数，保证权重非负且各签条可比。
    coefficients, residual = _nnls(components.T, observation[0])
    approximate = coefficients @ components
    return {
        'coefficients': _round_coefficients(coefficients),
        'dominant': int(coefficients.argmax()) + 1,
        'mean_error': round(float(np.mean(np.abs(approximate - observation))), 5),
    }


def _nnls(matrix, target):
    """轻量非负最小二乘（投影梯度），避免对 scipy 的额外依赖。"""
    n_features = matrix.shape[1]
    weights = np.zeros(n_features)
    step = 1.0 / (np.linalg.norm(matrix.T @ matrix) + 1e-12)
    for _ in range(2000):
        gradient = matrix.T @ (matrix @ weights - target)
        updated = np.maximum(0.0, weights - step * gradient)
        if np.all(np.abs(updated - weights) < 1e-10):
            weights = updated
            break
        weights = updated
    residual = target - matrix @ weights
    return weights, float(residual @ residual)


def calculate(data):
    """worker 入口，按任务类型分发，保持与队列协议兼容。"""
    kind = data.get('kind', 'decompose')
    if kind == 'fit_baseline':
        return fit_baseline(data)
    if kind in ('project', 'decompose'):
        return project_curve({'components': data['components'], 'bands': data['target']['bands']})
    raise ValueError(f'未知计算类型 {kind}')
