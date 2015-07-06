import unittest
import os
import mock
from application import app, db
from application.republish_all import *
import json
from testfixtures import LogCapture

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
        with LogCapture() as l:
            self.write_file()
            mock_sleep.side_effect = self.create_exception
            mock_repub.side_effect = self.do_nothing
            self.assertRaises(TestException, check_for_republish_all_titles_file, app, db)
        l.check(
            ('application', 'AUDIT', 'Republish everything: processing a request to republish all titles. '),
            ('application', 'AUDIT', 'Republish everything: Row IDs up to 1 checked. 0 titles sent for republishing.')
        )


#'Republish everything: Row IDs up to %s checked. %s titles sent for republishing.'

    @mock.patch('application.app.logger.audit')
    def test_remove_republish_all_titles_file(self, mock_audit):
        self.write_file()  # creates the test file.
        remove_republish_all_titles_file(app)
        mock_audit.assert_called_once_with(
            'Republish everything: Row IDs up to 1 checked. 0 titles sent for republishing.')
        self.assertFalse(os.path.isfile(PATH))

    @mock.patch('kombu.Exchange')
    @mock.patch('kombu.Connection')
    @mock.patch('kombu.Queue')
    @mock.patch('kombu.Producer')
    @mock.patch('application.republish_all.get_title_detail')
    def test_process_republish_all_titles_file(self, mock_db, mock_producer, mock_queue, mock_connection, mock_exchange):

        def fake_sor_data(self, *args):
            return {"sig": "some_signed_data", "data": {"title_number": "DN1", "application_reference": 23}}

        mock_db.side_effect = fake_sor_data
        try:
            self.write_file()
            process_republish_all_titles_file(app, db)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

    @mock.patch('application.models.SignedTitles')
    @mock.patch('application.db.session.query')
    def test_get_title_detail(self, mock_query, mock_model):
        try:
            get_title_detail(db, 1)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

    @mock.patch('kombu.message.Message')
    @mock.patch('application.server.republish_by_title_and_application_reference')
    @mock.patch('application.app.logger.audit')
    def test_process_message(self, mock_audit, mock_republish, mock_msg):
        mock_msg.ack.side_effect = self.do_nothing
        try:
            test_dict = {"title_number": "all done", "application_reference": "noon"}
            process_message(test_dict, mock_msg)
            mock_audit.assert_called_once_with('Republish everything: job completed at noon')
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

        try:
            test_dict = {"title_number": "DN1", "application_reference": "ABR1"}
            process_message(test_dict, mock_msg)
            mock_republish.assert_called_once_with(test_dict, False)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

    @mock.patch('kombu.Exchange')
    @mock.patch('kombu.Connection')
    @mock.patch('kombu.Queue')
    @mock.patch('kombu.Consumer')
    @mock.patch('kombu.Connection.channel')
    @mock.patch('application.republish_all.running_as_service')
    def test_check_republish_everything_queue(self, mock_loop_bool, mock_channel, mock_consumer, mock_queue,
                                              mock_connection, mock_exchange):
        # Everything is mocked in this test.   But its a large function - so coverage needs to be considered.
        def make_false():
            return False
        mock_loop_bool.side_effect = make_false
        try:
            check_republish_everything_queue(app)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

    def do_nothing(*args):
                pass

    def create_exception(self, *args):
        raise TestException('bang!')

    def write_file(self):
        new_job_data = {"current_id": 0, "last_id": 1, "count": 0}
        with open(PATH, 'w') as f:
            json.dump(new_job_data, f, ensure_ascii=False)




