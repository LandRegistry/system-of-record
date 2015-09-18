import os

class Config(object):
    # format is dialect+driver://username:password@host:port/database
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://systemofrecord:systemofrecord@localhost/systemofrecord')
    RABBIT_ENDPOINT = os.getenv('RABBIT_ENDPOINT', 'amqp://mqpublisher:mqpublisherpassword@localhost:5672//')
    RABBIT_QUEUE = os.getenv('RABBIT_QUEUE', 'system_of_record')
    RABBIT_ROUTING_KEY = os.getenv('RABBIT_ROUTING_KEY', 'system_of_record')
    LOGGING_PATH = os.getenv('LOGGING_PATH', 'python_logging/logging.yaml')
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True

class UnitTestConfig(Config):
    #Class needed so no messages not actually published by tests.
    SQLALCHEMY_DATABASE_URI = ''
    RABBIT_ENDPOINT = ''
    RABBIT_QUEUE = ''
    RABBIT_ROUTING_KEY = ''
    DEBUG = True

class PreviewConfig(Config):
    LOGGING_PATH = 'python_logging/logging.yaml'
    DEBUG = True

class ReleaseConfig(Config):
    LOGGING_PATH = 'python_logging/logging.yaml'
    DEBUG = True

class PreproductionConfig(Config):
    DEBUG = False

class OatConfig(Config):
    DEBUG = False

class ProductionConfig(Config):
    DEBUG = False