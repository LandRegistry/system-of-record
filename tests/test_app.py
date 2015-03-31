import unittest
from application import server
from application.server import app, publish_json_to_queue, make_log_msg
import os
import mock
from sqlalchemy.exc import IntegrityError
import time
from python_logging.logging_utils import log_dir

CORRECT_TEST_TITLE = '{"sig":"some_signed_data","data":{"title_number": "DN1"}}'
INCORRECT_TEST_TITLE = '{"missing closing speech marks :"some_signed_data","data":{"title_number": "DN1"}}'

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        app.config.from_object(os.environ.get('SETTINGS'))
        self.app = server.app.test_client()

    def add_mocks(function):
        @mock.patch('application.server.db.session.add')
        @mock.patch('application.server.db.session.commit')
        @mock.patch('application.server.db.session.flush')
        @mock.patch('application.server.db.session.rollback')
        @mock.patch('application.server.publish_json_to_queue')
        def wrapped(self, mock_add, mock_commit, mock_flush, mock_rollback, mock_publish_json_to_queue):
            return function(self, mock_add, mock_commit, mock_flush, mock_rollback, mock_publish_json_to_queue)
        return wrapped

    def test_config_variables_blank(self):
        self.assertEqual(app.config['RABBIT_ENDPOINT'], '')
        self.assertEqual(app.config['RABBIT_QUEUE'], '')
        self.assertEqual(app.config['RABBIT_ROUTING_KEY'], '')


    def test_server_code(self):
        self.assertEqual((self.app.get('/')).status, '200 OK')


    def test_server_message(self):
        self.assertEqual((self.app.get('/')).data.decode("utf-8"), "Everything is OK")


    @add_mocks
    def test_insert_route_correctly(self, mock_add, mock_commit, mock_flush, mock_rollback, mock_publish_json_to_queue):
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = CORRECT_TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '201 CREATED')
        self.assertTrue('Record successfully inserted to database at' in response.data.decode("utf-8"))


    @add_mocks
    def test_insert_route_incorrectly(self, mock_add, mock_commit, mock_flush, mock_rollback, mock_publish_json_to_queue):
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = INCORRECT_TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '400 BAD REQUEST')

    @add_mocks
    def test_record_unique_constraint(self, mock_add, mock_commit, mock_flush, mock_rollback, mock_publish_json_to_queue):
        mock_flush.side_effect = self.pretend_violate_constraint

        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = CORRECT_TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '409 CONFLICT')
        self.assertEqual(response.data.decode("utf-8"), 'Integrity error. Check that signature is unique. ')

    @add_mocks
    def test_raise_exception(self, mock_add, mock_commit, mock_flush, mock_rollback, mock_publish_json_to_queue):
        mock_publish_json_to_queue.side_effect = self.create_exception

        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = CORRECT_TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '500 INTERNAL SERVER ERROR')
        self.assertEqual(response.data.decode("utf-8"), 'Service failed to insert to the database. ')

    def pretend_violate_constraint(self):
        app.logger.info('pretend_violate_constraint called')
        raise IntegrityError('boom!','','')

    def create_exception(self, json_string):
        raise Exception('bang!')

    def test_logging_writes_to_debug_log(self):
        test_timestamp = time.time()
        app.logger.debug(test_timestamp)
        log_directory = log_dir('debug')
        f = open(log_directory, 'r')
        file_content = f.read()
        self.assertTrue(str(test_timestamp) in file_content)


    def test_logging_writes_to_error_log(self):
        test_timestamp = time.time()
        app.logger.error(test_timestamp)
        log_directory = log_dir('error')
        f = open(log_directory, 'r')
        file_content = f.read()
        self.assertTrue(str(test_timestamp) in file_content)


    def test_logging_writes_audits(self):
        test_timestamp = time.time()
        app.logger.audit(test_timestamp)
        log_directory = log_dir('error')
        f = open(log_directory, 'r')
        file_content = f.read()
        self.assertTrue(str(test_timestamp) in file_content)


    def test_info_logging_writes_to_debug_log(self):
        test_timestamp = time.time()
        app.logger.info(test_timestamp)
        log_directory = log_dir('debug')
        f = open(log_directory, 'r')
        file_content = f.read()
        self.assertTrue(str(test_timestamp) in file_content)


