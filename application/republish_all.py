#!/usr/bin/python

import threading
import time
import os
import os.path
import json

PATH = './republish_progress.json'

TEMP_PATH = './republish_progress_tmp.json'


def republish_all_titles(app, db):
    process_thread = threading.Thread(target=check_for_republish_all_titles_file, args=(app, db, ))
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
        #get the title_number and application_reference for the id
        title_dict = get_title_detail(db, current_id)
        if title_dict:
            try:
                title_number = title_dict['data']['title_number']
                application_reference = title_dict['data']['application_reference']
                queue_json = {"titles": [{"title_number":title_number, "application_reference": application_reference}]}
                publish_json_to_republish_everything_queue(queue_json, app)
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


def publish_json_to_republish_everything_queue(queue_json, app):

    from kombu import Connection, Producer, Exchange, Queue

    # Next write to queue for consumption by register publisher
    # By default messages sent to exchanges are persistent (delivery_mode=2),
    # and queues and exchanges are durable.
    # 'confirm_publish' means that the publish() call will wait for an acknowledgement.
    exchange = Exchange()
    connection = Connection(hostname=app.config['RABBIT_ENDPOINT'], transport_options={'confirm_publish': True})

    # Create a queue bound to the connection.
    # queue = Queue('system_of_record', exchange, routing_key='system_of_record')(connection)
    queue = Queue(app.config['REPUBLISH_EVERYTHING_QUEUE'],
                  exchange,
                  routing_key=app.config['REPUBLISH_EVERYTHING_ROUTING_KEY'])(connection)
    queue.declare()

    # Producers are used to publish messages.
    producer = Producer(connection)
    producer.publish(queue_json, exchange=exchange, routing_key=queue.routing_key, serializer='json')


def log_republish_error(message, app):
    from python_logging.logging_utils import linux_user
    message = message + 'Signed in as: %s. ' % linux_user()
    app.logger.error(message)