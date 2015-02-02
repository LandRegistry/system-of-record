
from app import db
from sqlalchemy.dialects.postgresql import JSON


class SignedTitles(db.model):

    __tablename__ = 'sor'

    sor = db.Column(JSON)

    def __init__(self, sor):

    def __repr__(self):
        return 'hi'