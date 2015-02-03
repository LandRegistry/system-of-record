from sqlalchemy import Column, Integer
from sqlalchemy.dialects.postgresql import JSON
from application import db


class SignedTitles(db.Model):

    __tablename__ = 'sor'

    id = Column(Integer, primary_key=True)
    sor = db.Column(JSON)

    def __init__(self, sor):
        self.sor = sor

    def __repr__(self):
        return self.sor
