import unittest
from application import server
from application.server import app, publish_json_to_queue, remove_username_password
from application.server import republish_latest_version, republish_by_title_and_application_reference
from application.server import republish_all_versions_of_title, NoRowFoundException
import os
import mock
from sqlalchemy.exc import IntegrityError
import time
from python_logging.logging_utils import log_dir

CORRECT_TEST_TITLE = '{"sig":"some_signed_data","data":{"title_number": "DN1"}}'
INCORRECT_TEST_TITLE = '{"missing closing speech marks :"some_signed_data","data":{"title_number": "DN1"}}'

class TestException(Exception):
    pass

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
        self.assertEqual(response.data.decode("utf-8"), 'Integrity error. Check that title number and application reference are unique. ')

    @add_mocks
    @mock.patch('application.server.remove_username_password')
    def test_raise_exception(self, mock_add, mock_commit, mock_flush, mock_rollback, mock_publish_json_to_queue, mock_remove_username_password):
        mock_remove_username_password.side_effect = self.create_exception
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = CORRECT_TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '500 INTERNAL SERVER ERROR')
        self.assertEqual(response.data.decode("utf-8"), 'Service failed to insert to the database. ')

    def pretend_violate_constraint(self):
        app.logger.info('pretend_violate_constraint called')
        raise IntegrityError('boom!','','')

    def create_exception(self, *args):
        raise TestException('bang!')

    def do_nothing(self, *args):
        pass


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


    def test_remove_username_password(self):
        self.assertEqual(remove_username_password('aprotocol://ausername:apassword@localhost:9876/'), 'aprotocol://localhost:9876/')
        self.assertEqual(remove_username_password(None), 'unknown endpoint')


    @mock.patch('application.server.republish_all_versions_of_title')
    def test_republish_route_for_all_versions_of_a_title(self, mock_get_all):
        REPUBLISH_TITLE_ALL_VERSIONS = '{"titles": [{"title_number":"DN1", "all_versions":true}]}'
        mock_get_all.side_effect = self.do_nothing
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/republish', data = REPUBLISH_TITLE_ALL_VERSIONS, headers = headers)
        self.assertEqual(response.status, '200 OK')
        self.assertEquals('No errors.  Number of titles in JSON: 1', response.data.decode("utf-8"))


    @mock.patch('application.server.republish_all_versions_of_title')
    def test_republish_route_for_all_versions_of_a_title_with_error(self, mock_get_all):
        REPUBLISH_TITLE_ALL_VERSIONS = '{"titles": [{"title_number":"DN1", "all_versions":true}, {"title_number":"DN2", "all_versions":true}]}'
        mock_get_all.side_effect = self.create_exception
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/republish', data = REPUBLISH_TITLE_ALL_VERSIONS, headers = headers)
        self.assertEqual(response.status, '202 ACCEPTED')
        self.assertEquals('Completed republish.  2 titles in JSON. Number of errors: 2', response.data.decode("utf-8"))


    @mock.patch('application.server.republish_by_title_and_application_reference')
    def test_republish_route_by_title_application(self, mock_title_app):
        REPUBLISH_SPECIFIC_TITLE_VERSION = '{"titles": [{"title_number":"DN1", "application_reference": "ABR123"}]}'
        mock_title_app.side_effect = self.do_nothing
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/republish', data=REPUBLISH_SPECIFIC_TITLE_VERSION, headers=headers)
        self.assertEqual(response.status, '200 OK')
        self.assertEquals('No errors.  Number of titles in JSON: 1', response.data.decode("utf-8"))


    @mock.patch('application.server.republish_by_title_and_application_reference')
    def test_republish_route_by_title_application_with_error(self, mock_title_app):
        REPUBLISH_SPECIFIC_TITLE_VERSION = '{"titles": [{"title_number":"DN1", "application_reference": "ABR123"}]}'
        mock_title_app.side_effect = self.create_exception
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/republish', data=REPUBLISH_SPECIFIC_TITLE_VERSION, headers=headers)
        self.assertEqual(response.status, '202 ACCEPTED')
        self.assertEquals('Completed republish.  1 titles in JSON. Number of errors: 1', response.data.decode("utf-8"))


    @mock.patch('application.server.republish_latest_version')
    def test_republish_route_for_latest_version(self, mock_latest_version):
        REPUBLISH_LATEST_VERSION = '{"titles": [{"title_number":"DN1"}, {"title_number":"DN2"}, {"title_number":"DN3"}]}'
        mock_latest_version.side_effect = self.do_nothing
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/republish', data = REPUBLISH_LATEST_VERSION, headers = headers)
        self.assertEqual(response.status, '200 OK')
        self.assertEquals('No errors.  Number of titles in JSON: 3', response.data.decode("utf-8"))


    @mock.patch('application.server.republish_latest_version')
    def test_republish_route_for_latest_version_with_error(self, mock_latest_version):
        REPUBLISH_LATEST_VERSION = '{"titles": [{"title_number":"DN1"}]}'
        mock_latest_version.side_effect = self.create_exception
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/republish', data = REPUBLISH_LATEST_VERSION, headers = headers)
        self.assertEqual(response.status, '202 ACCEPTED')
        self.assertEquals('Completed republish.  1 titles in JSON. Number of errors: 1', response.data.decode("utf-8"))


    @mock.patch('application.server.republish_all_versions_of_title')
    @mock.patch('application.server.republish_by_title_and_application_reference')
    @mock.patch('application.server.republish_latest_version')
    def test_republish_route_with_mixed_requests(self, mock_latest, mock_app, mock_all):
        REPUBLISH_MIXED = '{"titles": [{"title_number":"DN1", "application_reference": "ABR123"}, {"title_number":"DN1"}, {"title_number":"DN1", "all_versions":true}]}'
        mock_latest.side_effect = self.do_nothing
        mock_app.side_effect = self.do_nothing
        mock_all.side_effect = self.do_nothing
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/republish', data = REPUBLISH_MIXED, headers = headers)
        self.assertEqual(response.status, '200 OK')
        self.assertEquals('No errors.  Number of titles in JSON: 3', response.data.decode("utf-8"))


    # row response functions are used as a mock database results.
    def one_row_response(self, *args):
        return [({'sig': 'some_signed_data', 'data': {'title_number': 'DN1'}},)]

    def zero_row_response(self, *args):
        return []


    @mock.patch('application.server.publish_json_to_queue')
    @mock.patch('application.server.execute_query')
    def test_republish_latest_version(self, mock_execute_query, mock_publish):
        mock_publish.side_effect = self.do_nothing
        mock_execute_query.side_effect = self.one_row_response
        self.assertEquals('republish_latest_version successful', republish_latest_version({'title_number': 'DN1'}))


    @mock.patch('application.server.publish_json_to_queue')
    @mock.patch('application.server.execute_query')
    def test_republish_by_title_and_application_reference(self, mock_execute_query, mock_publish):
        mock_publish.side_effect = self.do_nothing
        mock_execute_query.side_effect = self.one_row_response
        self.assertEquals('republish_by_title_and_application_reference successful',
                          republish_by_title_and_application_reference({'title_number': 'DN1', 'application_reference': 'ABR456'}, True))


    @mock.patch('application.server.publish_json_to_queue')
    @mock.patch('application.server.execute_query')
    def test_republish_all_versions_of_title(self, mock_execute_query, mock_publish):
        mock_publish.side_effect = self.do_nothing
        mock_execute_query.side_effect = self.one_row_response
        self.assertEquals('republish_all_versions_of_title successful',
                          republish_all_versions_of_title({'title_number': 'DN1'}))


    @mock.patch('application.server.publish_json_to_queue')
    @mock.patch('application.server.execute_query')
    def test_republish_latest_version_error(self, mock_execute_query, mock_publish):
        mock_publish.side_effect = self.create_exception
        mock_execute_query.side_effect = self.one_row_response
        self.assertRaises(TestException, republish_latest_version, {'title_number': 'DN1'} )


    @mock.patch('application.server.publish_json_to_queue')
    @mock.patch('application.server.execute_query')
    def test_republish_by_title_and_application_reference_error(self, mock_execute_query, mock_publish):
        mock_publish.side_effect = self.create_exception
        mock_execute_query.side_effect = self.one_row_response
        self.assertRaises(TestException, republish_by_title_and_application_reference, {'title_number': 'DN1', 'application_reference': 'ABR456'}, True)


    @mock.patch('application.server.publish_json_to_queue')
    @mock.patch('application.server.execute_query')
    def test_republish_all_versions_of_title_error(self, mock_execute_query, mock_publish):
        mock_publish.side_effect = self.create_exception
        mock_execute_query.side_effect = self.one_row_response
        self.assertRaises(TestException, republish_all_versions_of_title, {'title_number': 'DN1'})


    @mock.patch('application.server.publish_json_to_queue')
    @mock.patch('application.server.execute_query')
    def test_republish_all_versions_of_title_row_not_found(self, mock_execute_query, mock_publish):
        mock_publish.side_effect = self.do_nothing
        mock_execute_query.side_effect = self.zero_row_response
        self.assertRaises(NoRowFoundException, republish_all_versions_of_title, {'title_number': 'DN1'})