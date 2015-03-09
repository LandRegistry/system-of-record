import os

class Config(object):
    DEBUG = False

class DevelopmentConfig(Config):
    # format is dialect+driver://username:password@host:port/database
    SQLALCHEMY_DATABASE_URI = 'postgresql://systemofrecord:systemofrecord@localhost/systemofrecord'
    RABBIT_ENDPOINT = 'amqp://guest:guest@localhost:5672//'
    RABBIT_QUEUE = 'system_of_record'
    RABBIT_ROUTING_KEY = 'system_of_record'
    DEBUG = True

class PreviewConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://systemofrecord:systemofrecord@localhost/systemofrecord'
    RABBIT_ENDPOINT = 'amqp://guest:guest@localhost:5672//'
    RABBIT_QUEUE = 'system_of_record'
    RABBIT_ROUTING_KEY = 'system_of_record'
    DEBUG = True

class PreproductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')
