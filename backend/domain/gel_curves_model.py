from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


gel_curves = Table('gel_curves', metadata,
    Column('code', String(64), primary_key=True),
    Column('reel', String(160), ForeignKey('gel_reels.code'), nullable=False),
    Column('bands', JSON, nullable=False),
    Column('rechecked', Boolean, nullable=False),
)
