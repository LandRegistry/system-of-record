export SQLALCHEMY_DATABASE_URI="postgresql://systemofrecord:systemofrecord@localhost/systemofrecord"
export RABBIT_ENDPOINT="amqp://mqpublisher:mqpublisherpassword@localhost:5672//"
export RABBIT_QUEUE="system_of_record"
export RABBIT_ROUTING_KEY="system_of_record"
export REPUBLISH_EVERYTHING_ENDPOINT="amqp://mqpublisher:mqpublisherpassword@localhost:5672//"
export REPUBLISH_EVERYTHING_ROUTING_KEY="republish_everything"
export REPUBLISH_EVERYTHING_QUEUE="republish_everything"

export SETTINGS="config.DevelopmentConfig"
export LOGGING_PATH="python_logging/logging.yaml"
