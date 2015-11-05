#!/usr/bin/python

import threading
import time
import os
import os.path
import json

PATH = './republish_progress.json'

TEMP_PATH = './republish_progress_tmp.json'

JOB_COMPLETE_FLAG = 'all done'

class RepublishTitles:

    def __init__(self):
        self.republish_thread = None


    def republish_all_in_progress(self):
        if self.republish_thread is not None:
            return self.republish_thread.isAlive()
        else:
            return False


    def republish_all_titles(self, app, db):
        # Thread to check the file for job progress and act accordingly.
        self.republish_thread = threading.Thread(name='monitor-republish_file', target=self.check_for_republish_all_titles_file, args=(app, db, ))
        self.republish_thread.setDaemon(True)
        self.republish_thread.start()


    def check_for_republish_all_titles_file(self, app, db):
        republish_all_titles_file_exists = os.path.isfile(PATH)
        if republish_all_titles_file_exists:
            app.logger.audit('Republish everything: processing a request to republish all titles. ')
            self.process_republish_all_titles_file(app, db)
            self.remove_republish_all_titles_file(app)


    def process_republish_all_titles_file(self, app, db):
        from .server import republish_by_title_and_application_reference

        with open(PATH, "r") as read_progress_file:
            progess_data = json.load(read_progress_file)
            read_progress_file.close()

        current_id = progess_data['current_id']
        last_id = progess_data['last_id']

        while current_id <= last_id:
            #get the title_number and application_reference for the id
            title_dict = self.get_title_detail(db, current_id)
            if title_dict:
                try:
                    title_number = title_dict['data']['title_number']
                    application_reference = title_dict['data']['application_reference']
                    republish_json = {"title_number": title_number, "application_reference": application_reference}

                    republish_by_title_and_application_reference(republish_json, False)

                    progress_count = progess_data['count']
                    progress_count += 1
                    progess_data['count'] = progress_count

                except Exception as err:
                    self.log_republish_error(
                        'Could not parse JSON to republish for row id %s owing to following error %s. ' % (
                        current_id, str(err)), app)

            current_id += 1

            # Update progress in the file every 10000 rows
            if current_id % 10000 == 0 or current_id == last_id:
                progess_data['current_id'] = current_id
                write_progress_file = open(TEMP_PATH, "w")
                json.dump(progess_data, write_progress_file, ensure_ascii=False)
                write_progress_file.flush()  # Flush Python buffers
                os.fsync(write_progress_file.fileno())  # Flush OS buffers
                write_progress_file.close()

                # Upon success, rename to proper filename.  Rename is an atomic action.  May fail if the flask app is querying
                # the progress file, to determine job progress.
                max_tries = 100
                loop_error = None
                for i in range(max_tries):
                    try:
                        os.rename(TEMP_PATH, PATH)
                        break
                    except Exception as err:
                        time.sleep(0.1)
                        app.logger.info("cannot rename file.  On attempt %i" % i, app)
                        loop_error = err
                else:
                    self.log_republish_error('Can not rename temp file after processing id: %s.  Aborting job.  Error: %s' % (current_id, str(loop_error)), app)
                    #Abort this job by breaking out of the loop.  Otherwise it will continuously loop on the same id.
                    break


    def get_title_detail(self, db, the_id):
        from application.models import SignedTitles
        a_dict = None
        signed_titles_instance = db.session.query(SignedTitles).get(the_id)
        if signed_titles_instance:
            a_dict = signed_titles_instance.record
        return a_dict


    def remove_republish_all_titles_file(self, app):
        republish_all_titles_file_exists = os.path.isfile(PATH)
        if republish_all_titles_file_exists:
            max_tries = 10
            for i in range(max_tries):
                try:
                    with open(PATH, "r") as read_progress_file:
                        progess_data = json.load(read_progress_file)
                        read_progress_file.close()
                    app.logger.audit('Republish everything: Row IDs up to %s checked. %s titles sent for republishing.' % (
                        progess_data['last_id'], progess_data['count']))
                    os.remove(PATH)
                    break
                except Exception as err:
                    time.sleep(1)
                    self.log_republish_error(str(err), app)
            else:
                self.log_republish_error('Can not remove job file after republishing', app)


    def log_republish_error(self, message, app):
        from python_logging.logging_utils import linux_user
        message = message + ' Signed in as: %s. ' % linux_user()
        app.logger.error(message)
        return message # return is for testing