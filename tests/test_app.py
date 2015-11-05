import unittest
from application import server
from application.server import app,db, publish_json_to_queue, remove_username_password
from application.server import republish_latest_version, republish_by_title_and_application_reference
from application.server import republish_all_versions_of_title, NoRowFoundException
import os
import mock
from sqlalchemy.exc import IntegrityError
import time
from python_logging.logging_utils import log_dir
import json
from application import republish_title_instance
from testfixtures import LogCapture

CORRECT_TEST_TITLE = '{"sig":"some_signed_data","data":{"title_number": "DN1"}}'
INCORRECT_TEST_TITLE = '{"missing closing speech marks :"some_signed_data","data":{"title_number": "DN1"}}'

class TestException(Exception):
    pass

class TestSequenceFunctions(unittest.TestCase):

    PATH = './republish_progress.json'

    def setUp(self):
        app.config.from_object(os.environ.get('SETTINGS'))
        self.app = server.app.test_client()

    def tearDown(self):
        republish_title_instance.remove_republish_all_titles_file(app)

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

    @mock.patch('application.server.get_last_system_of_record_id')
    @mock.patch('application.server.republish_title_instance.republish_all_titles')
    def test_republish_everything_route(self, mock_republish, mock_id):
        #erase a job file if it exists
        republish_title_instance.remove_republish_all_titles_file(app)

        def fake_id():
            return 1
        mock_id.side_effect = fake_id
        mock_republish.side_effect = self.do_nothing
        # start new job
        response = self.app.get('/republish/everything')
        self.assertEqual(response.status, '200 OK')
        self.assertEquals("New republish job submitted", response.data.decode("utf-8"))

        # check I can't start another
        response = self.app.get('/republish/everything')
        self.assertEqual(response.status, '200 OK')
        self.assertEquals("Resumed republish job.", response.data.decode("utf-8"))

        republish_title_instance.remove_republish_all_titles_file(app)

    @mock.patch('application.server.get_last_system_of_record_id')
    @mock.patch('application.server.check_job_running')
    @mock.patch('application.server.republish_title_instance.republish_all_titles')
    def test_republish_route_with_running_job(self, mock_republish, mock_running, mock_id):

        def fake_id():
            return 1

        def fake_running():
            return 'running'
        def clear_progress_file():
            #erase a job file if it exists
            try:
                os.remove(self.PATH)
            except:
                pass

        clear_progress_file()
        mock_running.side_effect = fake_running
        mock_id.side_effect = fake_id
        mock_republish.side_effect = self.do_nothing
        # start new job
        response = self.app.get('/republish/everything')
        self.assertEqual(response.status, '200 OK')
        self.assertEquals("New republish job submitted", response.data.decode("utf-8"))

        # check I can't start another
        response = self.app.get('/republish/everything')
        self.assertEqual(response.status, '200 OK')
        self.assertEquals("Republish job already in progress", response.data.decode("utf-8"))

    def test_log_republish_error(self):
        self.assertTrue('test Signed in as:' in republish_title_instance.log_republish_error('test', app))

    @mock.patch('application.server.republish_title_instance.check_for_republish_all_titles_file')
    def test_republish_all_titles(self, mock_file_func):
        mock_file_func.side_effect = self.do_nothing
        try:
            republish_title_instance.republish_all_titles(app, db)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

    # mantra: "Mock an item where it is used, not where it came from."
    @mock.patch('application.server.republish_title_instance.process_republish_all_titles_file')
    def test_check_for_republish_all_titles_file(self, mock_repub):
        with LogCapture() as l:
            self.write_file()
            mock_repub.side_effect = self.do_nothing
            republish_title_instance.check_for_republish_all_titles_file(app, db)
        l.check(
            ('application', 'AUDIT', 'Republish everything: processing a request to republish all titles. '),
            ('application', 'AUDIT', 'Republish everything: Row IDs up to 1 checked. 0 titles sent for republishing.')
        )

    @mock.patch('application.app.logger.audit')
    def test_remove_republish_all_titles_file(self, mock_audit):
        self.write_file()  # creates the test file.
        republish_title_instance.remove_republish_all_titles_file(app)
        mock_audit.assert_called_once_with(
            'Republish everything: Row IDs up to 1 checked. 0 titles sent for republishing.')
        self.assertFalse(os.path.isfile(self.PATH))

    @mock.patch('application.models.SignedTitles')
    @mock.patch('application.db.session.query')
    def test_get_title_detail(self, mock_query, mock_model):
        try:
            republish_title_instance.get_title_detail(db, 1)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")

    @mock.patch('application.server.republish_by_title_and_application_reference')
    @mock.patch('application.server.republish_title_instance.get_title_detail')
    def test_process_republish_all_titles_file(self, mock_get_detail, mock_republish):

        def fake_sor_data(self, *args):
            return {"sig": "some_signed_data", "data": {"title_number": "DN1", "application_reference": 23}}

        mock_get_detail.side_effect = fake_sor_data
        mock_republish.side_effect = self.do_nothing
        try:
            self.write_file()
            republish_title_instance.process_republish_all_titles_file(app, db)
        except Exception as err:
            app.logger.error(str(err))
            self.fail("myFunc() raised ExceptionType unexpectedly!")


    def write_file(self):
        new_job_data = {"current_id": 0, "last_id": 1, "count": 0}
        with open(self.PATH, 'w') as f:
            json.dump(new_job_data, f, ensure_ascii=False)




