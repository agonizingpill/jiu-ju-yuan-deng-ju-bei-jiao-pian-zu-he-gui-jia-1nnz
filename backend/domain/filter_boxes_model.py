from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


filter_boxes = Table('filter_boxes', metadata,
    Column('code', String(64), primary_key=True),
    Column('kind', String(160), nullable=False),
    Column('aged', Boolean, nullable=False),
    Column('space', Integer, nullable=False),
    Column('contents', JSON, nullable=False),
    CheckConstraint('space >= 0'),
)
