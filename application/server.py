from application.models import SignedTitles
from application import app
from application import db
from flask import request
from kombu import Connection, Producer, Exchange, Queue
import traceback
from sqlalchemy.exc import IntegrityError
from python_logging.logging_utils import linux_user, client_ip, log_dir


@app.route("/")
def check_status():
    return "Everything is OK"


@app.route("/insert", methods=["POST"])
def insert():
    signed_title_json = request.get_json()
    signed_title_json_object = SignedTitles(signed_title_json)

    title_number = get_title_number(request)
    try:
        db.session.add(signed_title_json_object)
        #flush the database session to send the insert to the database
        #to check unique constraint before commit
        db.session.flush()

        # Publish to queue upon successful insertion
        publish_json_to_queue(request.get_json())
        app.logger.audit(
            make_log_msg('Record successfully published to %s queue at %s' % (
                app.config['RABBIT_QUEUE'], app.config['RABBIT_ENDPOINT']), request, 'info', title_number))

        db.session.commit()

        app.logger.audit(
            make_log_msg('Record successfully inserted to database at %s. ' % app.config['SQLALCHEMY_DATABASE_URI'],
                         request, 'info', title_number))

    except IntegrityError:
        db.session.rollback()
        error_message = 'Integrity error. Check that signature is unique. '
        app.logger.exception(make_log_msg(error_message, request, 'error', title_number))
        return error_message, 409

    except Exception:
        db.session.rollback()
        error_message = 'Service failed to insert to the database. '
        app.logger.exception(make_log_msg(error_message, request, 'error', title_number))
        return error_message, 500

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


def make_log_msg(message, request, log_level, title_number):
    #Constructs the message to submit to audit.
    msg = message + 'Client ip address is: %s. ' % client_ip(request)
    msg = msg + 'Signed in as: %s. ' % linux_user()
    msg = msg + 'Title number is: %s. ' % title_number
    msg = msg + 'Logged at: system-of-record/%s. ' % log_dir(log_level)
    return msg


def get_title_number(request):
    #gets the title number from minted json
    try:
        return request.get_json()['data']['title_number']
    except Exception as err:
        error_message = "title number not found. Check JSON format: "
        app.logger.error(make_log_msg(error_message, request, 'error', request.get_json()))
        return error_message + str(err)
