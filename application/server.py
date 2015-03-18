from application.models import SignedTitles
from application import app
from application import db
from flask import request
from kombu import Connection, Producer, Exchange, Queue
import traceback
from sqlalchemy.exc import IntegrityError
from application.logging_utils import linux_user, client_ip, log_dir


@app.route("/")
def check_status():
    return "Everything is OK"


@app.route("/insert", methods=["POST"])
def insert():
    signed_title_json = request.get_json()
    signed_title_json_object = SignedTitles(signed_title_json)

    # Write to database
    try:
        #Start database transaction with 'add'.  Commit if all well.
        db.session.add(signed_title_json_object)
        #Log that the record was published
        title_number = signed_title_json['data']['titleno']
        db.session.commit()
        app.logger.info(
            'Record successfully inserted to database at %s' % (app.config['SQLALCHEMY_DATABASE_URI']))
        app.logger.info('client ip is: ' + client_ip(request))
        app.logger.info('Signed on user is: ' + linux_user())
        app.logger.info('title number is: ' + title_number)
        app.logger.info('logged at: ' + str(log_dir('info')))
        app.logger.info('within the insert operation')

        publish_json_to_queue(request.get_json())
        app.logger.info(
            'Record successfully published to %s queue at %s' % (app.config['RABBIT_QUEUE'], app.config['RABBIT_ENDPOINT']))
        app.logger.info('client ip is: ' + client_ip(request))
        app.logger.info('Signed on user is: ' + linux_user())
        app.logger.info('title number is: ' + title_number)
        app.logger.info('logged at: ' + str(log_dir('info')))
        app.logger.info('within the insert operation')

    except IntegrityError:
        db.session.rollback;
        app.logger.error(traceback.format_exc()) #logs the call stack
        return 'Integrity error. Check that signature is unique', 500

    except Exception:
        db.session.rollback;
        app.logger.error(traceback.format_exc()) #logs the call stack
        return 'Service failed to insert', 500

    return "row inserted", 201


def publish_json_to_queue(json_string):
    # Next write to queue for consumption by register publisher
    # By default messages sent to exchanges are persistent (delivery_mode=2),
    # and queues and exchanges are durable.
    exchange = Exchange()
    connection = Connection(app.config['RABBIT_ENDPOINT'])

    # Create a queue bound to the connection.
    # queue = Queue('system_of_record', exchange, routing_key='system_of_record')(connection)
    queue = Queue(app.config['RABBIT_QUEUE'],
                  exchange,
                  routing_key=app.config['RABBIT_ROUTING_KEY'])(connection)
    queue.declare()

    # Producers are used to publish messages.
    producer = Producer(connection)
    producer.publish(json_string, exchange=exchange, routing_key=queue.routing_key,  serializer='json')

