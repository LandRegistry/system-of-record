from flask import Flask, request
import os
from flask.ext.sqlalchemy import SQLAlchemy
from python_logging.setup_logging import setup_logging
from .republish_all import republish_all_titles
from kombu import Connection, Producer, Exchange, Queue


setup_logging()
app = Flask(__name__)
db = SQLAlchemy(app)
app.config.from_object(os.environ.get('SETTINGS'))

#Configure the RabbitMQ connection, queue and producer.
# By default messages sent to exchanges are persistent (delivery_mode=2),
# and queues and exchanges are durable.
# 'confirm_publish' means that the publish() call will wait for an acknowledgement.
# # Producers are used to publish messages.
exchange = Exchange()
connection = Connection(hostname=app.config['RABBIT_ENDPOINT'], transport_options={'confirm_publish': True})
queue = Queue(app.config['RABBIT_QUEUE'],
              exchange,
              routing_key=app.config['RABBIT_ROUTING_KEY'])(connection)
queue.declare()

# Producers are used to publish messages.
producer = Producer(connection)


# republish_all_titles(app, db)