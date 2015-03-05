import os

class Config(object):
    DEBUG = False

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/systemofrecord'
    RABBIT_ENDPOINT = 'amqp://guest:guest@localhost:5672//'
    RABBIT_QUEUE = 'system_of_record'
    RABBIT_ROUTING_KEY = 'system_of_record'
    DEBUG = True
    REGISTER_PUBLISHER_QUEUE_DETAILS = 'OUTGOING_QUEUE'

class PreviewConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/systemofrecord'
    RABBIT_ENDPOINT = 'amqp://guest:guest@localhost:5672//'
    RABBIT_QUEUE = 'system_of_record'
    RABBIT_ROUTING_KEY = 'system_of_record'
    DEBUG = True
    REGISTER_PUBLISHER_QUEUE_DETAILS = 'OUTGOING_QUEUE'

class PreproductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','')
