from sqlalchemy import Column, Integer
from application.server import db
from sqlalchemy.dialects.postgresql import JSON


class SignedTitles(db.Model):

    __tablename__ = 'sor'

    id = Column(Integer, primary_key=True)
    sor = db.Column(JSON)

