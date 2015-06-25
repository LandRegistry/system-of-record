#!/usr/bin/python

import threading
import time
import os
import os.path
import json

PATH = './republish_progress.json'

TEMP_PATH = './republish_progress_tmp.json'


def republish_all_titles(app, db):
    # Thread to check the file for job progress and act accordingly.
    process_thread = threading.Thread(target=check_for_republish_all_titles_file, args=(app, db, ))
    process_thread.setDaemon(True)
    process_thread.start()

    # Thread to query the REPUBLISH_EVERYTHING_QUEUE and process any jobs found.
    process_thread = threading.Thread(target=check_republish_everything_queue, args=(app, ))
    process_thread.setDaemon(True)
    process_thread.start()


def check_for_republish_all_titles_file(app, db):
    republish_all_titles_file_exists = os.path.isfile(PATH)
    if republish_all_titles_file_exists:
        process_republish_all_titles_file(app, db)
        remove_republish_all_titles_file(app)
        app.logger.audit("republish everything job completed.")
        check_for_republish_all_titles_file(app, db)
    else:
        time.sleep(5)
        check_for_republish_all_titles_file(app, db)


def process_republish_all_titles_file(app, db):
    with open(PATH, "r") as read_progress_file:
        progess_data = json.load(read_progress_file)
        read_progress_file.close()

    current_id = progess_data['current_id']
    last_id = progess_data['last_id']

    while current_id <= last_id:
        #Set up the queue and connection here, and tidy up in the finally statement.
        from kombu import Connection, Producer, Exchange, Queue
        exchange = Exchange()
        connection = Connection(hostname=app.config['RABBIT_ENDPOINT'], transport_options={'confirm_publish': True})
        queue = Queue(app.config['REPUBLISH_EVERYTHING_QUEUE'],
                      exchange,
                      routing_key=app.config['REPUBLISH_EVERYTHING_ROUTING_KEY'])(connection)
        queue.declare()
        producer = Producer(connection)
        try:
            #get the title_number and application_reference for the id
            title_dict = get_title_detail(db, current_id)
            if title_dict:
                try:
                    title_number = title_dict['data']['title_number']
                    application_reference = title_dict['data']['application_reference']
                    queue_json = {"title_number": title_number, "application_reference": application_reference}
                    producer.publish(queue_json, exchange=exchange, routing_key=queue.routing_key, serializer='json')
                except Exception as err:
                    log_republish_error('Could not parse JSON to republish for row id %s. ' % current_id, app)

            current_id += 1
            progess_data['current_id'] = current_id

            # Write progress to a temporary file 0
            write_progress_file = open(TEMP_PATH, "w")
            json.dump(progess_data, write_progress_file, ensure_ascii=False)
            write_progress_file.flush()  # Flush Python buffers
            os.fsync(write_progress_file.fileno())  # Flush OS buffers
            write_progress_file.close()

            # Upon success, rename to proper filename.  Rename is an atomic action.
            max_tries = 100
            for i in range(max_tries):
                try:
                    os.rename(TEMP_PATH, PATH)
                    break
                except:
                    time.sleep(.1)
            else:
                log_republish_error('Can not rename temp file after processing id: %s' % current_id, app)

        finally:
            producer.close()
            connection.close()

def get_title_detail(db, the_id):
    from application.models import SignedTitles
    a_dict = None
    signed_titles_instance = db.session.query(SignedTitles).get(the_id)
    if signed_titles_instance:
        a_dict = signed_titles_instance.record
    return a_dict


def remove_republish_all_titles_file(app):
    max_tries = 100
    for i in range(max_tries):
        try:
            os.remove(PATH)
            break
        except:
            time.sleep(.1)
    else:
        log_republish_error('Can not remove job file after republishing', app)


def process_message(body, message):
    from application.server import republish_by_title_and_application_reference
    republish_by_title_and_application_reference(body)
    message.ack()


def check_republish_everything_queue(app):
    # Set up the queue and connection here, and tidy up in the finally statement.
    from kombu import Consumer, Exchange, Connection, Queue
    connection = Connection(hostname=app.config['RABBIT_ENDPOINT'])
    channel = connection.channel()
    exchange = Exchange()
    queue = Queue(app.config['REPUBLISH_EVERYTHING_QUEUE'],
                  exchange,
                  routing_key=app.config['REPUBLISH_EVERYTHING_ROUTING_KEY'])(connection)
    queue.declare()
    consumer = Consumer(channel, queues=queue, callbacks=[process_message], accept=['json'])
    consumer.consume()
    # Loop "forever", as a service.
    # N.B.: if there is a serious network failure or the like then this will keep logging errors!
    while True:
        try:
            consumer.connection.drain_events()
        except Exception as e:
            log_republish_error("Exception trying to query REPUBLISH_EVERYTHING_QUEUE: %s" % e.args[0], app)
            # If we ignore the problem, perhaps it will go away ...
            time.sleep(10)


def log_republish_error(message, app):
    from python_logging.logging_utils import linux_user
    message = message + 'Signed in as: %s. ' % linux_user()
    app.logger.error(message)