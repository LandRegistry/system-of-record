import os

class Config(object):
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    RABBIT_ENDPOINT = os.getenv('RABBIT_ENDPOINT')
    RABBIT_QUEUE = os.getenv('RABBIT_QUEUE')
    RABBIT_ROUTING_KEY = os.getenv('RABBIT_ROUTING_KEY')
    REPUBLISH_EVERYTHING_ENDPOINT = os.getenv('REPUBLISH_EVERYTHING_ENDPOINT')
    REPUBLISH_EVERYTHING_ROUTING_KEY = os.getenv('REPUBLISH_EVERYTHING_ROUTING_KEY')
    REPUBLISH_EVERYTHING_QUEUE = os.getenv('REPUBLISH_EVERYTHING_QUEUE')
    LOGGING_PATH = os.getenv('LOGGING_PATH', 'python_logging/logging.yaml')
    DEBUG = False

class DevelopmentConfig(Config):
    # format is dialect+driver://username:password@host:port/database
    DEBUG = True

class UnitTestConfig(Config):
    #Class needed so no messages not actually published by tests.
    SQLALCHEMY_DATABASE_URI = ''
    RABBIT_ENDPOINT = ''
    RABBIT_QUEUE = ''
    RABBIT_ROUTING_KEY = ''
    REPUBLISH_EVERYTHING_ENDPOINT = ''
    REPUBLISH_EVERYTHING_ROUTING_KEY = ''
    REPUBLISH_EVERYTHING_QUEUE = ''
    DEBUG = True

class PreviewConfig(Config):
    LOGGING_PATH = 'python_logging/logging.yaml'
    DEBUG = True

class ReleaseConfig(Config):
    LOGGING_PATH = 'python_logging/logging.yaml'
    DEBUG = True

class PreproductionConfig(Config):
    DEBUG = False

class ProductionConfig(Config):
    DEBUG = False