#!/usr/bin/python

import threading
import time
import os
import os.path
import json
import socket

PATH = './republish_progress.json'

TEMP_PATH = './republish_progress_tmp.json'

JOB_COMPLETE_FLAG = 'all done'


class RepublishTitles:

    def __init__(self):
        self.republish_thread = None
        self.republish_flag = None
        self.republish_current_id = 0
        self.republish_last_id = 0
        self.republish_count = 0

    def set_republish_instance_variables(self, republish_current_id, republish_last_id, republish_count):
        self.republish_current_id = republish_current_id
        self.republish_last_id = republish_last_id
        self.republish_count = republish_count

    def get_republish_instance_variable(self):
        return {"republish_current_id": self.republish_current_id, "republish_max_id": self.republish_last_id, "total_records_published": self.republish_count}

    def set_republish_flag(self,value):
        self.republish_flag = value

    def republish_all_in_progress(self):
        socket_check = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            socket_check.bind("\0republish-socket")
            socket_check.close
            return False
        except socket.error:
            return True


    def republish_all_titles(self, app, db):
        # Thread to check the file for job progress and act accordingly.
        self.republish_thread = threading.Thread(name='monitor-republish_file', target=self.check_for_republish_all_titles_file, args=(app, db, ))
        self.republish_thread.setDaemon(True)
        self.republish_thread.start()


    def check_for_republish_all_titles_file(self, app, db):
        republish_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        republish_socket.bind("\0republish-socket")
        republish_all_titles_file_exists = os.path.isfile(PATH)
        if republish_all_titles_file_exists:
            self.process_republish_all_titles_file(app, db)
            self.remove_republish_all_titles_file(app)
        republish_socket.close


    def query_sor_100_at_a_time(self, db, progress_data):
        from application.models import SignedTitles
        return db.session.query(SignedTitles).filter(SignedTitles.id >= progress_data['current_id']).order_by(SignedTitles.id).yield_per(100)


    def process_republish_all_titles_file(self, app, db):
        from .server import publish_json_to_queue
        with open(PATH, "r") as read_progress_file:
            progress_data = json.load(read_progress_file)
            read_progress_file.close()

        app.logger.audit('Republish everything: processing a request to republish all titles from row ids %s to %s.'
                         % (progress_data['current_id'], progress_data['last_id']))

        # 100 rows returned at a time. Start iterating from the row id that is current_id.
        for row in self.query_sor_100_at_a_time(db, progress_data):
            if row:
                try:
                    progress_data['current_id'] = row.id
                    current_id = progress_data['current_id']
                    if row.id > progress_data['last_id'] or self.republish_flag is not None:
                        break

                    publish_json_to_queue(row.record, row.record['data']['title_number'])
                    progress_data['count'] += 1
                    self.set_republish_instance_variables(progress_data['current_id'], progress_data['last_id'],
                                                          progress_data['count'])


                except Exception as err:
                    self.log_republish_error(
                        'Could not republish for row id %s owing to following error %s. ' % (
                            progress_data['current_id'], str(err)), app)
                    # Update the progress file upon error
                    self.update_progress(app, progress_data)

            # Update progress in the file for every 10000 processed rows
            if progress_data['current_id'] % 10000 == 0:
                self.update_progress(app, progress_data)


        # Update the progress file upon completion
        self.update_progress(app, progress_data)


    def update_progress(self, app, progress_data):
        write_progress_file = open(TEMP_PATH, "w")
        json.dump(progress_data, write_progress_file, ensure_ascii=False)
        write_progress_file.flush()  # Flush Python buffers
        os.fsync(write_progress_file.fileno())  # Flush OS buffers
        write_progress_file.close()

        # Upon success, rename to proper filename.  Rename is an atomic action.  May fail if the flask app is querying
        # the progress file, to determine job progress.
        max_tries = app.config['MAX_RENAME_RETRIES']
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
            self.log_republish_error('Can not rename temp file after processing id: %s.  Aborting job.  Error: %s' % (progress_data['current_id'], str(loop_error)), app)

    def remove_republish_all_titles_file(self, app):
        republish_all_titles_file_exists = os.path.isfile(PATH)
        if republish_all_titles_file_exists:
            max_tries = 10
            for i in range(max_tries):
                try:
                    with open(PATH, "r") as read_progress_file:
                        progess_data = json.load(read_progress_file)
                        read_progress_file.close()
                    if self.republish_flag == 'pause':
                        app.logger.audit('Republish everything: Row IDs up to %s checked. %s titles sent for republishing. Currently paused.' % (
                            progess_data['last_id'], progess_data['count']))
                    else:
                         if self.republish_flag is None:
                             app.logger.audit('Republish everything: Row IDs up to %s checked. %s titles sent for republishing.' % (
                                 progess_data['last_id'], progess_data['count']))
                         else:
                             app.logger.audit('Republish everything: Job Aborted. %s titles sent for republishing.' % (
                                 progess_data['count']))
                             self.set_republish_instance_variables(0,0,0)
                             self.set_republish_flag(None)
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