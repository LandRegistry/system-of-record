from flask import Flask, request, g
import os
from flask.ext.sqlalchemy import SQLAlchemy
from python_logging.setup_logging import setup_logging
from .republish_all import RepublishTitles
from kombu import Connection, Producer, Exchange, Queue, Consumer


setup_logging()
app = Flask(__name__)
db = SQLAlchemy(app)
app.config.from_object(os.environ.get('SETTINGS'))
republish_title_instance = RepublishTitles()

if os.environ.get('SETTINGS') != "config.UnitTestConfig":
    #Configure the RabbitMQ connection, queue and producer for the flask app.
    # By default messages sent to exchanges are persistent (delivery_mode=2),
    # and queues and exchanges are durable.
    exchange = Exchange()
    connection = Connection(hostname=app.config['RABBIT_ENDPOINT'], transport_options={'confirm_publish': True})
    system_of_record_queue = Queue(app.config['RABBIT_QUEUE'],
                  exchange,
                  routing_key=app.config['RABBIT_ROUTING_KEY'])(connection)
    system_of_record_queue.declare()
    channel = connection.channel()
    producer = Producer(connection)