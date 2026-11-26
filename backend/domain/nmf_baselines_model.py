from sqlalchemy import CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


# 统一 NMF 基准：同一时刻至多一条 status='active'，其余为待切换的 staged。
nmf_baselines = Table('nmf_baselines', metadata,
    Column('code', String(64), primary_key=True),
    Column('components', JSON, nullable=False),          # 共享成分矩阵（n_components x 波段数）
    Column('references', Integer, nullable=False),       # 参与拟合的复测曲线数
    Column('status', String(16), nullable=False),        # active / staged / retired
    Column('token', String(64), nullable=False, unique=True),
    Column('mean_error', Float, nullable=False),         # 基准对历史数据的重构均误
    CheckConstraint("status in ('active','staged','retired')"),
)


# 新基准对在盒签条的换算记录：保证同一签条对同一新基准只换算一次（重试不重复启用）。
profile_conversions = Table('profile_conversions', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('baseline', String(64), ForeignKey('nmf_baselines.code'), nullable=False),
    Column('profile', String(64), ForeignKey('color_profiles.code'), nullable=False),
    Column('weights', JSON, nullable=True),              # 换算成功后的新权重，失败时为空
    Column('dominant', Integer, nullable=True),
    Column('error_value', Float, nullable=True),
    Column('token', String(64), nullable=True),          # 换算计算凭据，过期可清空重算
    Column('state', String(16), nullable=False),         # pending / ready / failed
    Column('detail', String(255), nullable=True),
    CheckConstraint("state in ('pending','ready','failed')"),
)
