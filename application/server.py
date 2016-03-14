from application.models import SignedTitles
from application import app
from application import db
from application.republish_all_multi import Republisher
from flask import request, g
import traceback
from sqlalchemy.exc import IntegrityError
import re
import os
import os.path
import json
import socket
import multiprocessing
import time
import pwd
import datetime
import sys
import logging

logging.basicConfig(format='%(levelname)s %(asctime)s [SystemOfRecord] Message: %(message)s', level=logging.INFO, datefmt='%d.%m.%y %I:%M:%S %p')

@app.route("/")
def check_status():
    logging.info("SOR status check OK")
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
        publish_json_to_queue(request.get_json(), title_number)
        logging.info( make_log_msg( 'Record successfully published to %s queue at %s. ' % (app.config['RABBIT_QUEUE'], rabbit_endpoint()), title_number ) )
        db.session.commit()

    except IntegrityError as err:
        db.session.rollback()
        error_message = 'Integrity error. Check that title number, application reference and geometry application reference are unique. '
        logging.error( make_log_msg( error_message + err.args[0], title_number ) )
        return error_message, 409

    except Exception as err:
        db.session.rollback()
        error_message = 'Service failed to insert to the database. '
        logging.error( make_log_msg( error_message + err.args[0], title_number ) )
        return error_message, 500

    postgres_endpoint = remove_username_password(app.config['SQLALCHEMY_DATABASE_URI'])
    success_message = 'Record successfully inserted to database at %s. ' % postgres_endpoint
    logging.info( make_log_msg( success_message, title_number) )
    return success_message, 201

def publish_json_to_queue(request_json, title_number):
    # Next write to queue for consumption by register publisher
    from application import producer, exchange, system_of_record_queue, connection

    def errback(exc, interval):
        logging.error( make_log_msg( 'Error publishing to queue: %r.' % exc, title_number ) )
        logging.info( make_log_msg( 'Retry publishing in %s seconds' % interval, title_number ) )

    # connection.ensure will re-establish the connection and retry, if the connection is lost.
    publish_to_sor = connection.ensure(producer, producer.publish, errback=errback, max_retries=10)
    publish_to_sor(request_json, exchange=exchange, routing_key=system_of_record_queue.routing_key, serializer='json',
                     headers={'title_number': title_number})

def get_title_number(request):
    #gets the title number from minted json
    try:
        return request.get_json()['data']['title_number']
    except Exception as err:
        error_message = "Title number not found. Check JSON format: "
        logging.error( make_log_msg( error_message + request.get_json() , title_number ) )
        return error_message + str(err)

def remove_username_password(endpoint_string):
    try:
        return re.sub('://[^:]+:[^@]+@', '://', endpoint_string)
    except:
        return "unknown endpoint"

def rabbit_endpoint():
    #We don't want to include the username and password for the endpoint in logs
    return remove_username_password(app.config['RABBIT_ENDPOINT'])

@app.route("/republish", methods=["POST"])
def republish():
    #Consider Indexes on Expressions to make selects more efficient.
    error_count = 0
    total_count = 0
    republish_json = request.get_json()
    # Now loop through the json elements
    for a_title in republish_json['titles']:

        try:
            # get all versions of the register for a title number.  Key 'all-versions' contains a boolean.
            if 'all_versions' in a_title and a_title['all_versions']:
                start_republish({'title_number': a_title['title_number']}, True)

            # get version(s) of the register by title_number and application_reference.
            # NB. Possible to have versions with same title_number and application_reference, but different geometry_application_reference
            elif 'application_reference' in a_title and 'geometry_application_reference' not in a_title:
                start_republish({'title_number': a_title['title_number'], 'application_reference': a_title['application_reference']}, True)

            # get specific version of register by title_number, application_reference and geometry_application_reference
            elif 'application_reference' in a_title and 'geometry_application_reference' in a_title:
                start_republish({'title_number': a_title['title_number'], 'application_reference': a_title['application_reference'],
                                 'geometry_application_reference': a_title['geometry_application_reference'] }, True)

            # get the latest version of the register for a title number
            else:
                start_republish({'title_number': a_title['title_number'], 'newest_only': True}, True)
        except:
            error_count += 1

        total_count += 1

    if error_count > 0:
        return 'Completed republish.  %i titles in JSON. Number of errors: %i' % (total_count, error_count), 202
    else:
        return 'No errors.  Number of titles in JSON: %i' % total_count, 200

@app.route("/republish/everything")
def republish_everything_without_params():
    logging.info( make_log_msg( 'Starting full republish..' ) )
    return start_republish()

@app.route("/republish/everything/<date_time_from>")
def republish_everything_with_from_param(date_time_from):
    date_time_from = re.sub('[T]', ' ', date_time_from)
    logging.info( make_log_msg( 'Starting republish from date %s' % date_time_from  ) )
    return start_republish({ 'start_date': date_time_from })

@app.route("/republish/everything/<date_time_from>/<date_time_to>")
def republish_everything_with_from_and_to_params(date_time_from, date_time_to):
    # Date required in format of "2015-11-11T13:42:50.840623", Time separator T is removed with REGEX.
    date_time_from = re.sub('[T]', ' ', date_time_from)
    date_time_to = re.sub('[T]', ' ', date_time_to)
    logging.info( make_log_msg( 'Starting date range republish from %s to %s' % date_time_from, date_time_to  ) )
    return start_republish({ 'start_date': date_time_from, 'end_date': date_time_to })

@app.route("/republish/everything/status")
def check_job_running():
    logging.info( make_log_msg( 'Query republish status...' ) )
    res = republish_command({'target':'running'})
    if res:
        return 'running'
    else:
        return 'not running'

@app.route("/republish/pause")
def pause_republish():
    logging.info( make_log_msg( 'Pausing republish...' ) )
    res = republish_command({'target':'stop'})
    if res == "Republish stopped":
        return 'paused republishing from System of Record and will re-start on the resume command'
    else:
        return res

@app.route("/republish/abort")
def abort_republish():
    logging.info( make_log_msg( 'Aborting republish...' ) )
    res = republish_command({'target':'reset'})
    if res == "Reset":
        return 'aborted republishing from System of Record'
    else:
        return res

@app.route("/republish/resume")
def resume_republish():
    logging.info( make_log_msg( 'Resuming republish...' ) )
    res = republish_command({'target':'resume'})
    if res == 'Started' or res == 'Already running':
        return 'republishing has been resumed'
    elif res == 'Nothing to resume':
        return 'Republishing cannot resume as no job in progress'
    else:
        return res
    
@app.route("/republish/progress")
def republish_progress():
    logging.info( make_log_msg( 'Retrieving Republish progress...' ) )
    res = republish_command({'target':'progress'})
    #TODO: Backwards compatibility (please remove me when updating front end)
    res['republish_started'] = 'true' if res['is_running'] else 'false'
    return json.dumps(res)

def start_republish(kwargs={}, sync=False):
    '''Start republish with the given criteria, wait for completion if sync = true'''
    logging.info( make_log_msg( 'Starting republishing %s...' % (json.dumps(kwargs) ) ) )
    if sync:
        command = 'sync_start'
    else:
        command = 'start'
    res = republish_command({'target': command, 'kwargs': kwargs})
    if res == "Republish started":
        return "New republish job submitted"
    elif sync:
        if res == "Republish complete":
            return res
        else:
            logging.info( make_log_msg( 'Republish failed: %s' % res ) )
            raise Exception(res)
    else:
        return res

def republish_command(command):
    '''Sends the given command to the republisher'''
    socket = republish_connection()
    try:
        socket.sendall(json.dumps(command).encode("utf-8"))
        reply = socket.recv(4096).decode("utf-8")
        res = json.loads(reply)
    finally:
        socket.close()
    return res['result']

def republish_connection():
    '''Establish republish connection and return socket, starts republisher if not running'''
    republish_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        republish_socket.connect("\0republish-socket")
        return republish_socket
    except ConnectionRefusedError:
        logging.info( make_log_msg( 'Republisher not running, starting...' ) )
        mp = multiprocessing.Process(target=Republisher().republish_process, args=[app.config['SQLALCHEMY_DATABASE_URI'],
                                                                              app.config['RABBIT_ENDPOINT'],
                                                                              app.config['REPUBLISH_QUEUE'],
                                                                              app.config['RABBIT_QUEUE'],
                                                                              app.config['RABBIT_ROUTING_KEY']])
        mp.daemon = True
        mp.start()
        for _x in range(10):
            try:
                republish_socket.connect("\0republish-socket")
                return republish_socket
            except ConnectionRefusedError:
                logging.info( make_log_msg( 'Republisher connection refused, retrying...' ) )
                time.sleep(1)
        raise
    

def make_log_msg(message, title_number=''):
    if title_number == '':
        return "{}, Raised by: {}".format( message, linux_user() )
    else:
        return "{}, Raised by: {}, Title Number: {}".format( message, linux_user(), title_number )


def linux_user():
    try:
        return pwd.getpwuid(os.geteuid()).pw_name
    except Exception as err:
        return "failed to get user: %s" % err