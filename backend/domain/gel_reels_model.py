from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


gel_reels = Table('gel_reels', metadata,
    Column('code', String(64), primary_key=True),
    Column('family', String(160), nullable=False),
    Column('aged', Boolean, nullable=False),
    Column('eligible', Boolean, nullable=False),
)
