import os

class Config(object):
    DEBUG = False
    LOGGING_PATH = os.getenv('LOGGING_PATH', 'python_logging/logging.yaml')

class DevelopmentConfig(Config):
    # format is dialect+driver://username:password@host:port/database
    SQLALCHEMY_DATABASE_URI = 'postgresql://systemofrecord:systemofrecord@localhost/systemofrecord'
    RABBIT_ENDPOINT = 'amqp://mqpublisher:mqpublisherpassword@localhost:5672//'
    RABBIT_QUEUE = 'system_of_record'
    RABBIT_ROUTING_KEY = 'system_of_record'
    REPUBLISH_EVERYTHING_ENDPOINT = ('amqp://mqpublisher:mqpublisherpassword@localhost:5672/')
    REPUBLISH_EVERYTHING_ROUTING_KEY = 'republish_everything'
    REPUBLISH_EVERYTHING_QUEUE = 'republish_everything'
    DEBUG = True

class UnitTestConfig(Config):
    #Class needed so no messages not actually published by tests.
    SQLALCHEMY_DATABASE_URI = ''
    RABBIT_ENDPOINT = ''
    RABBIT_QUEUE = ''
    RABBIT_ROUTING_KEY = ''
    REPUBLISH_EVERYTHING_ENDPOINT = os.getenv('')
    REPUBLISH_EVERYTHING_ROUTING_KEY = ''
    REPUBLISH_EVERYTHING_QUEUE = ''
    DEBUG = True

class PreviewConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://systemofrecord:systemofrecord@localhost/systemofrecord')
    RABBIT_ENDPOINT = os.getenv('RABBIT_ENDPOINT', 'amqp://mqpublisher:mqpublisherpassword@localhost:5672/')
    RABBIT_QUEUE = os.getenv('RABBIT_QUEUE', 'system_of_record')
    RABBIT_ROUTING_KEY = os.getenv('RABBIT_ROUTING_KEY', 'system_of_record')
    REPUBLISH_EVERYTHING_ENDPOINT = os.getenv('REPUBLISH_EVERYTHING_ENDPOINT', 'amqp://mqpublisher:mqpublisherpassword@localhost:5672/')
    REPUBLISH_EVERYTHING_ROUTING_KEY = 'republish_everything'
    REPUBLISH_EVERYTHING_QUEUE = 'republish_everything'
    LOGGING_PATH = 'python_logging/logging.yaml'
    DEBUG = True

class ReleaseConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://systemofrecord:systemofrecord@localhost/systemofrecord')
    RABBIT_ENDPOINT = os.getenv('RABBIT_ENDPOINT', 'amqp://mqpublisher:mqpublisherpassword@localhost:5672/')
    RABBIT_QUEUE = os.getenv('RABBIT_QUEUE', 'system_of_record')
    RABBIT_ROUTING_KEY = os.getenv('RABBIT_ROUTING_KEY', 'system_of_record')
    REPUBLISH_EVERYTHING_ENDPOINT = os.getenv('REPUBLISH_EVERYTHING_ENDPOINT', 'amqp://mqpublisher:mqpublisherpassword@localhost:5672/')
    REPUBLISH_EVERYTHING_ROUTING_KEY = os.getenv('REPUBLISH_EVERYTHING_ROUTING_KEY', 'republish_everything')
    REPUBLISH_EVERYTHING_QUEUE = os.getenv('REPUBLISH_EVERYTHING_QUEUE', 'republish_everything')
    LOGGING_PATH = 'python_logging/logging.yaml'
    DEBUG = True

class PreproductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', '')
    RABBIT_ENDPOINT = os.getenv('RABBIT_ENDPOINT', '')
    RABBIT_QUEUE = os.getenv('RABBIT_QUEUE', '')
    RABBIT_ROUTING_KEY = os.getenv('RABBIT_ROUTING_KEY', '')
    REPUBLISH_EVERYTHING_ENDPOINT = os.getenv('REPUBLISH_EVERYTHING_ENDPOINT', '')
    REPUBLISH_EVERYTHING_ROUTING_KEY = os.getenv('REPUBLISH_EVERYTHING_ROUTING_KEY', '')
    REPUBLISH_EVERYTHING_QUEUE = os.getenv('REPUBLISH_EVERYTHING_QUEUE', '')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', '')
    RABBIT_ENDPOINT = os.getenv('RABBIT_ENDPOINT', '')
    RABBIT_QUEUE = os.getenv('RABBIT_QUEUE', '')
    RABBIT_ROUTING_KEY = os.getenv('RABBIT_ROUTING_KEY', '')
    REPUBLISH_EVERYTHING_ENDPOINT = os.getenv('REPUBLISH_EVERYTHING_ENDPOINT', '')
    REPUBLISH_EVERYTHING_ROUTING_KEY = os.getenv('REPUBLISH_EVERYTHING_ROUTING_KEY', '')
    REPUBLISH_EVERYTHING_QUEUE = os.getenv('REPUBLISH_EVERYTHING_QUEUE', '')
