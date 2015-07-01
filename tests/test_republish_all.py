import unittest
import os
import mock
from application import app, db
from application.republish_all import *
import json


class TestException(Exception):
    pass

class TestSequenceFunctions(unittest.TestCase):

    PATH = './republish_progress.json'

    def setUp(self):
        app.config.from_object(os.environ.get('SETTINGS'))
        self.app = app.test_client()

    def test_config_variables_blank(self):
        self.assertEqual(app.config['SQLALCHEMY_DATABASE_URI'], '')
        self.assertEqual(app.config['RABBIT_ENDPOINT'], '')
        self.assertEqual(app.config['RABBIT_QUEUE'], '')
        self.assertEqual(app.config['RABBIT_ROUTING_KEY'], '')
        self.assertEqual(app.config['REPUBLISH_EVERYTHING_ENDPOINT'], '')
        self.assertEqual(app.config['REPUBLISH_EVERYTHING_ROUTING_KEY'], '')
        self.assertEqual(app.config['REPUBLISH_EVERYTHING_QUEUE'], '')

    def test_log_republish_error(self):
        self.assertTrue('test Signed in as:' in log_republish_error('test', app))

    @mock.patch('application.republish_all.check_for_republish_all_titles_file')
    @mock.patch('application.republish_all.check_republish_everything_queue')
    def test_republish_all_titles(self, mock_queue_func, mock_file_func):
        mock_queue_func.side_effect = self.do_nothing
        mock_file_func.side_effect = self.do_nothing
        try:
            republish_all_titles(app, db)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

    # mantra: "Mock an item where it is used, not where it came from."
    @mock.patch('application.republish_all.process_republish_all_titles_file')
    @mock.patch('time.sleep')
    def test_check_for_republish_all_titles_file(self, mock_sleep, mock_repub):
        # Write a file.  Mock Process it. Mock sleep to raise an exception to exit the recursive loop.
        self.write_file()
        mock_sleep.side_effect = self.create_exception
        mock_repub.side_effect = self.do_nothing
        self.assertRaises(TestException, check_for_republish_all_titles_file, app, db)

    def test_remove_republish_all_titles_file(self):
        self.write_file() # creates the test file.
        remove_republish_all_titles_file(app)
        self.assertFalse(os.path.isfile(PATH))

    # def test_process_republish_all_titles_file(self):
    #     try:
    #         self.write_file()
    #         process_republish_all_titles_file(app, db)
    #     except Exception as err:
    #         app.logger.error(str(err))
    #         self.fail("myFunc() raised ExceptionType unexpectedly!")


    def do_nothing(*args):
        pass

    def create_exception(self, *args):
        raise TestException('bang!')

    def write_file(self):
        new_job_data = {"current_id": 0, "last_id": 1, "count": 0}
        with open(PATH, 'w') as f:
            json.dump(new_job_data, f, ensure_ascii=False)


