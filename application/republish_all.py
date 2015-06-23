#!/usr/bin/python

import threading
import time
import os
import os.path
import json

PATH = './republish_progress.json'

TEMP_PATH = './republish_progress_tmp.json'


def check_for_republish_all_titles(app):
    process_thread = threading.Thread(target=check_for_republish_all_titles_file, args=(app,))
    process_thread.setDaemon(True)
    process_thread.start()


def check_for_republish_all_titles_file(app):
    republish_all_titles_file_exists = os.path.isfile(PATH)
    if republish_all_titles_file_exists:
        # app.logger.info(time)
        process_republish_all_titles_file(app)
        check_for_republish_all_titles_file(app)
    else:
        time.sleep(1)
        check_for_republish_all_titles_file(app)


def process_republish_all_titles_file(app):
    with open(PATH, "r") as read_progress_file:
        progess_data = json.load(read_progress_file)
        read_progress_file.close()

    current_id = progess_data['current_id']
    last_id = progess_data['last_id']

    while current_id <= last_id:
        #do the republish for that id.  Then increment.
        app.logger.info('do repub here: ' + str(current_id))

        current_id += 1
        progess_data['current_id'] = current_id

        # Write progress to a temporary file 0
        write_progress_file = open(TEMP_PATH, "w")
        json.dump(progess_data, write_progress_file, ensure_ascii=False)
        write_progress_file.flush()  # Flush Python buffers
        os.fsync(write_progress_file.fileno())  # Flush OS buffers
        write_progress_file.close()

        # Upon success, rename to proper filename.  Rename is an atomic action.
        os.rename(TEMP_PATH, PATH)
