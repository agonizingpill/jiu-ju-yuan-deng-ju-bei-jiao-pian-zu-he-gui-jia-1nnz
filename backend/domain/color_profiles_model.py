from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


color_profiles = Table('color_profiles', metadata,
    Column('code', String(64), primary_key=True),
    Column('curve', String(160), ForeignKey('gel_curves.code'), nullable=False),
    Column('weights', JSON, nullable=False),
    Column('dominant', Integer, nullable=False),
    Column('error_value', Float, nullable=False),
    Column('token', String(64), nullable=False, unique=True),
)
