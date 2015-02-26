import os

class Config(object):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    RABBIT_ENDPOINT = os.environ['RABBIT_ENDPOINT']
    RABBIT_QUEUE = os.environ['RABBIT_QUEUE']
    RABBIT_ROUTING_KEY = os.environ['RABBIT_ROUTING_KEY']

class DevelopmentConfig(Config):
    DEBUG = True

class TestConfig(Config):
    DEBUG = True
