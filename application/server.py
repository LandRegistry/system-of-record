from application.models import SignedTitles
from application import app
from application import db
from flask import request
from kombu import Connection, Producer, Exchange, Queue
import traceback
from sqlalchemy.exc import IntegrityError
from python_logging.logging_utils import linux_user, client_ip, log_dir
import re



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
        publish_json_to_queue(request.get_json(), get_title_number(request))
        rabbit_endpoint = remove_username_password(app.config['RABBIT_ENDPOINT'])
        app.logger.audit(
            make_log_msg(
                'Record successfully published to %s queue at %s. ' % (app.config['RABBIT_QUEUE'], rabbit_endpoint),
                    request, 'debug', title_number))

        db.session.commit()

    except IntegrityError as err:
        db.session.rollback()
        error_message = 'Integrity error. Check that title number and application reference are unique. '
        app.logger.exception(make_log_msg(error_message, request, 'error', title_number))
        return error_message, 409

    except Exception as err:
        db.session.rollback()
        error_message = 'Service failed to insert to the database. '
        app.logger.exception(make_log_msg(error_message, request, 'error', title_number))
        return error_message, 500

    postgres_endpoint = remove_username_password(app.config['SQLALCHEMY_DATABASE_URI'])
    success_message = 'Record successfully inserted to database at %s. ' % postgres_endpoint
    app.logger.audit(
        make_log_msg(success_message,
                 request, 'debug', title_number))
    return success_message, 201



def publish_json_to_queue(json_string, title_number):
    # Next write to queue for consumption by register publisher
    # By default messages sent to exchanges are persistent (delivery_mode=2),
    # and queues and exchanges are durable.
    # 'confirm_publish' means that the publish() call will wait for an acknowledgement.
    exchange = Exchange()
    connection = Connection(hostname=app.config['RABBIT_ENDPOINT'], transport_options={'confirm_publish': True})

    # Create a queue bound to the connection.
    # queue = Queue('system_of_record', exchange, routing_key='system_of_record')(connection)
    queue = Queue(app.config['RABBIT_QUEUE'],
                  exchange,
                  routing_key=app.config['RABBIT_ROUTING_KEY'])(connection)
    queue.declare()

    # Producers are used to publish messages.
    producer = Producer(connection)
    producer.publish(json_string, exchange=exchange, routing_key=queue.routing_key, serializer='json',
                     headers={'title_number': title_number})


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


def remove_username_password(endpoint_string):
    try:
        return re.sub('://[^:]+:[^@]+@', '://', endpoint_string)
    except:
        return "unknown endpoint"


@app.route("/republish", methods=["POST"])
def republish():
    #Consider Indexes on Expressions to make selects more efficient.
    republish_json = request.get_json()
    # Now loop through the json elements
    for a_title in republish_json['titles']:

        # get all versions of the register for a title number.  Key 'all-versions' contains a boolean.
        if 'all-versions' in a_title and a_title['all-versions']:
            app.logger.info('get all versions of %s' % a_title['title_number'])
            sql = "select record from records where (record->'data'->>'title_number')::text = '%s';" % a_title[
                'title_number']
            result = db.engine.execute(sql)
            for row in result:
                app.logger.info(row[0])
                publish_json_to_queue((row[0]), a_title['title_number'])

        # get the register by title_number and application_reference
        elif 'application_reference' in a_title:
            app.logger.info('get %s with reference %s ' % (a_title['title_number'], a_title['application_reference']))
            sql = "select record from records where (record->'data'->>'title_number')::text = '%s' and (record->'data'->>'application_reference')::text = '%s';" % (
                a_title['title_number'], a_title['application_reference'])
            result = db.engine.execute(sql)

            for row in result:
                app.logger.info(row[0])
                publish_json_to_queue((row[0]), a_title['title_number'])

        #get the latest version of the register for a title number
        else:
            app.logger.info('get latest version of %s' % a_title['title_number'])
            sql = "select record from records where (record->'data'->>'title_number')::text = '%s' order by id desc limit 1;" % \
                  a_title['title_number']
            result = db.engine.execute(sql)
            for row in result:
                app.logger.info(row[0])
                publish_json_to_queue((row[0]), a_title['title_number'])

    return 'ok', 200