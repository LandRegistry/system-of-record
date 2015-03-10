import os

class Config(object):
    DEBUG = False

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/systemofrecord'
    RABBIT_ENDPOINT = 'amqp://guest:guest@localhost:5672//'
    RABBIT_QUEUE = 'system_of_record'
    RABBIT_ROUTING_KEY = 'system_of_record'
    DEBUG = True

class UnitTestConfig(Config):
    #Class needed so no messages not actually published by tests.
    SQLALCHEMY_DATABASE_URI = ''
    RABBIT_ENDPOINT = ''
    RABBIT_QUEUE = ''
    RABBIT_ROUTING_KEY = ''
    DEBUG = True

class PreviewConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/systemofrecord'
    RABBIT_ENDPOINT = 'amqp://guest:guest@localhost:5672//'
    RABBIT_QUEUE = 'system_of_record'
    RABBIT_ROUTING_KEY = 'system_of_record'
    DEBUG = True

class PreproductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')
