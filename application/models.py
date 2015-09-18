import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSON
from application import db


class SignedTitles(db.Model):

    __tablename__ = 'records'

    id = Column(Integer, primary_key=True)
    record = db.Column(JSON)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, record):
        self.record = record

    def __repr__(self):
        return self.record
