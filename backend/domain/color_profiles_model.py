from sqlalchemy import Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


color_profiles = Table('color_profiles', metadata,
    Column('code', String(64), primary_key=True),
    Column('curve', String(160), ForeignKey('gel_curves.code'), nullable=False),
    Column('weights', JSON, nullable=False),
    Column('dominant', Integer, nullable=False),
    Column('error_value', Float, nullable=False),
    Column('token', String(64), nullable=False, unique=True),
    # 签条权重所依据的统一基准；种子等历史签条可能为空，按在用基准补换算。
    Column('baseline', String(64), ForeignKey('nmf_baselines.code'), nullable=True),
)
