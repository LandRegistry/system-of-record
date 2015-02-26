import os

class Config(object):
    DEBUG = False

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/systemofrecord'
    DEBUG = True

class PreviewConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/systemofrecord'
    DEBUG = True

class PreproductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')
