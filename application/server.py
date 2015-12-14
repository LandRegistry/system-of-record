from application.models import SignedTitles
from application import app
from application import db
from application import republish_title_instance
from flask import request, g
# from kombu import Connection, Producer, Exchange, Queue
import traceback
from sqlalchemy.exc import IntegrityError
from python_logging.logging_utils import linux_user, client_ip, log_dir
import re
import os
import os.path
import json


PATH='./republish_progress.json'

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
        app.logger.audit(
            make_log_msg(
                'Record successfully published to %s queue at %s. ' % (app.config['RABBIT_QUEUE'], rabbit_endpoint()),
                    request, 'debug', title_number))

        db.session.commit()

    except IntegrityError as err:
        db.session.rollback()
        error_message = 'Integrity error. Check that title number and application reference are unique. '
        app.logger.error(make_log_msg(error_message, request, 'error', title_number))
        app.logger.error(error_message + err.args[0])  # Show limited exception message without reg data.
        return error_message, 409

    except Exception as err:
        db.session.rollback()
        error_message = 'Service failed to insert to the database. '
        app.logger.error(make_log_msg(error_message, request, 'error', title_number))
        app.logger.error(error_message + err.args[0])  # Show limited exception message without reg data.
        return error_message, 500

    postgres_endpoint = remove_username_password(app.config['SQLALCHEMY_DATABASE_URI'])
    success_message = 'Record successfully inserted to database at %s. ' % postgres_endpoint
    app.logger.audit(
        make_log_msg(success_message,
                 request, 'debug', title_number))
    return success_message, 201



def publish_json_to_queue(request_json, title_number):
    # Next write to queue for consumption by register publisher
    from application import producer, exchange, system_of_record_queue, connection

    def errback(exc, interval):
        app.logger.error('Error publishing to queue: %r', exc, exc_info=1)
        app.logger.info('Retry publishing in %s seconds.', interval)

    # connection.ensure will re-establish the connection and retry, if the connection is lost.
    publish_to_sor = connection.ensure(producer, producer.publish, errback=errback, max_retries=10)
    publish_to_sor(request_json, exchange=exchange, routing_key=system_of_record_queue.routing_key, serializer='json',
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

        # get all versions of the register for a title number.  Key 'all-versions' contains a boolean.
        if 'all_versions' in a_title and a_title['all_versions']:
            try:
                republish_all_versions_of_title(a_title)
            except:
                error_count += 1

        # get the register by title_number and application_reference
        elif 'application_reference' in a_title:
            try:
                republish_by_title_and_application_reference(a_title, True)
            except:
                error_count += 1

        #get the latest version of the register for a title number
        else:
            try:
                republish_latest_version(a_title)
            except:
                error_count += 1

        total_count += 1

    if error_count != 0:
        return 'Completed republish.  %i titles in JSON. Number of errors: %i' % (total_count, error_count), 202
    else:
        return 'No errors.  Number of titles in JSON: %i' % total_count, 200


def republish_latest_version(republish_json):
    try:
        row_count = 0 #resultproxy.rowcount unreliable in sqlalchemy

        sql = "select record from records where (record->'data'->>'title_number')::text = '%s' order by id desc limit 1;" % \
              republish_json['title_number']
        result = execute_query(sql)
        for row in result:
            row_count += 1
            publish_json_to_queue((row[0]), republish_json['title_number'])

        if row_count == 0:
            raise NoRowFoundException('title_number %s not found in database. ' % republish_json['title_number'])

        app.logger.audit(
            make_log_msg(
                'Republishing latest version of title to %s queue at %s. ' % (
                    app.config['RABBIT_QUEUE'], rabbit_endpoint()),
                    request, 'debug', republish_json['title_number']))

        return 'republish_latest_version successful'  # for testing

    except Exception as err:
        error_message = 'Error republishing latest version of %s. ' % republish_json['title_number']
        app.logger.error(make_log_msg(error_message, request, 'error', republish_json['title_number']))
        app.logger.error(error_message + err.args[0])  # Show limited exception message without reg data.
        raise # re-raise error for counting errors.


def republish_by_title_and_application_reference(republish_json, perform_audit):
    try:
        row_count = 0 #resultproxy.rowcount unreliable in sqlalchemy

        sql = "select record from records where (record->'data'->>'title_number')::text = '%s' and (record->'data'->>'application_reference')::text = '%s';" % (
            republish_json['title_number'], republish_json['application_reference'])
        result = execute_query(sql)

        for row in result:
            row_count += 1
            publish_json_to_queue((row[0]), republish_json['title_number'])

        if row_count == 0:
            raise NoRowFoundException('application %s for title number %s not found in database. ' % (
                republish_json['application_reference'], republish_json['title_number']))

        if perform_audit: # No audit is system performing a full republish.
            app.logger.audit(
                make_log_msg(
                    'Republishing application %s to  %s queue at %s. ' % (
                        republish_json['application_reference'], app.config['RABBIT_QUEUE'], rabbit_endpoint()),
                    request, 'debug', republish_json['title_number']))

        return 'republish_by_title_and_application_reference successful'  # for testing

    except Exception as err:
        error_message = 'Error republishing title %s with application reference %s. ' % (
            republish_json['title_number'], republish_json['application_reference'])
        app.logger.error(make_log_msg(error_message, request, 'error', republish_json['title_number']))
        app.logger.error(error_message + err.args[0])  # Show limited exception message without reg data.
        raise # re-raise error for counting errors.


def republish_all_versions_of_title(republish_json):
    try:
        row_count = 0 #resultproxy.rowcount unreliable in sqlalchemy

        sql = "select record from records where (record->'data'->>'title_number')::text = '%s';" % republish_json[
            'title_number']
        result = execute_query(sql)

        for row in result:
            row_count += 1
            publish_json_to_queue((row[0]), republish_json['title_number'])

        if row_count == 0:
            raise NoRowFoundException('title_number %s not found in database .' % republish_json['title_number'])

        app.logger.audit(
            make_log_msg(
                'Republishing all versions of title to %s queue at %s. ' % (app.config['RABBIT_QUEUE'], rabbit_endpoint()),
                request, 'debug', republish_json['title_number']))

        return 'republish_all_versions_of_title successful'  # for testing

    except Exception as err:
            error_message = 'Error republishing title %s. ' % (
                republish_json['title_number'])
            app.logger.error(make_log_msg(error_message, request, 'error', republish_json['title_number']))
            app.logger.error(error_message + err.args[0])  # Show limited exception message without reg data.
            raise  # re-raise error for counting errors.


@app.route("/republish/everything")
def republish_everything_without_params():
    republish_title_instance.set_republish_flag(None)
    return republish_everything(None, None)  # No date_from and date_to specified

@app.route("/republish/everything/from/<date_time_from>")
def republish_everything_with_from_param(date_time_from):
    return republish_everything(date_time_from, None)

@app.route("/republish/everything/to/<date_time_to>")
def republish_everything_with_to_param(date_time_to):
    return republish_everything(None, date_time_to)

@app.route("/republish/everything/between/<date_time_from>/<date_time_to>")
def republish_everything_with_from_and_to_params(date_time_from, date_time_to):
    return republish_everything(date_time_from, date_time_to)

def republish_everything(date_time_from, date_time_to):
    import logging
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # check that a republish job is not already underway.
    if os.path.isfile(PATH):
        if check_job_running() == 'running':
            audit_message = 'New republish job attempted.  However, one already in progress. '
            app.logger.audit(make_log_msg(audit_message, request, 'debug', 'all titles'))
            return "Republish job already in progress", 200
        elif check_job_running() == 'not running':
            audit_message = 'Existing republish everything job resumed. '
            app.logger.audit(make_log_msg(audit_message, request, 'debug', 'all titles'))
            # resume republishing events.
            republish_title_instance.republish_all_titles(app, db)
            return "Resumed republish job.", 200
        else:
            return "Unknown job status.", 200
    else:
        # Get the corresponding row ids for the date supplied.
        if date_time_from is None:
            from_id = 0
        else:
            from_id = get_first_id_for_date_time(date_time_from)
            app.logger.audit('Request to republish everything from {0} (id = {1})'.format(date_time_from, from_id))
        if date_time_to is None:
            to_id = get_last_system_of_record_id()
        else:
            to_id = get_last_id_for_date_time(date_time_to)
            app.logger.audit('Request to republish everything up to {0} (id = {1})'.format(date_time_to, to_id))

        # Create a new job file
        new_job_data = {"current_id": from_id, "last_id": to_id, "count": 0}
        with open(PATH, 'w') as f:
            json.dump(new_job_data, f, ensure_ascii=False)
        audit_message = 'New republish everything job submitted. '
        app.logger.audit(make_log_msg(audit_message, request, 'debug', 'all titles'))
        # Check for and process republishing events.
        republish_title_instance.republish_all_titles(app, db)
        return "New republish job submitted", 200


def get_first_id_for_date_time(date_time_from):
    # Date required in format of "2015-11-11T13:42:50.840623", Time separator T is removed with REGEX.
    date_time_from = re.sub('[T]', ' ', date_time_from)
    signed_titles_instance = db.session.query(SignedTitles).filter(SignedTitles.created_date >= date_time_from).order_by(SignedTitles.created_date.asc()).first()
    return signed_titles_instance.id


def get_last_id_for_date_time(date_time_to):
    # Date required in format of "2015-11-11T13:42:50.840623", Time separator T is removed with REGEX.
    date_time_to = re.sub('[T]', ' ', date_time_to)
    signed_titles_instance = db.session.query(SignedTitles).filter(
        SignedTitles.created_date <= date_time_to).order_by(SignedTitles.created_date.desc()).first()
    return signed_titles_instance.id


@app.route("/republish/everything/status")
def check_job_running():
    if republish_title_instance.republish_all_in_progress():
        return 'running'
    else:
        return 'not running'

def get_last_system_of_record_id():
    signed_titles_instance = db.session.query(SignedTitles).order_by(SignedTitles.id.desc()).first()
    return signed_titles_instance.id


def execute_query(sql):
    return db.engine.execute(sql)


class NoRowFoundException(Exception):
    pass

@app.route("/republish/pause")
def pause_republish():
    republish_title_instance.set_republish_flag('pause')
    app.logger.audit(
        make_log_msg(
            'Republishing has been paused. ',
            request, 'debug', 'n/a'))
    return 'paused republishing from System of Record and will re-start on the resume command'

@app.route("/republish/abort")
def abort_republish():
    republish_title_instance.set_republish_flag('abort')
    app.logger.audit(
        make_log_msg(
            'Republishing has been aborted. ',
            request, 'debug', 'n/a'))
    return 'aborted republishing from System of Record'

@app.route("/republish/resume")
def resume_republish():
    if os.path.isfile(PATH):
        republish_title_instance.set_republish_flag(None)
        republish_everything_without_params()
        app.logger.audit(
            make_log_msg(
                'Republishing has been resumed. ',
                request, 'debug', 'n/a'))
        return 'republishing has been resumed'
    else:
        app.logger.audit(
            make_log_msg(
                'Republishing is not in progress, unable to resume. ',
                request, 'debug', 'n/a'))
        return 'Republishing cannot resume as no job in progress'

@app.route("/republish/progress")
def republish_progress():
    progress = progress_republish()
    return progress

def progress_republish():
    app.logger.audit(make_log_msg('Republish progress requested', request, 'debug', 'n/a'))
    republish_counts = republish_title_instance.get_republish_instance_variable(db)
    if os.path.exists(PATH):
        republish_counts['republish_started'] = True
    else:
        republish_counts['republish_started'] = False
    return json.dumps(republish_counts)