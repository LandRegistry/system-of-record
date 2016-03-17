import unittest
from unittest.mock import patch, Mock, PropertyMock, call
from application import server
from application.server import app,db, publish_json_to_queue, remove_username_password, make_log_msg
import os
import mock
from sqlalchemy.exc import IntegrityError
import time
import json
from testfixtures import LogCapture
import pytest
import logging
import os.path
import pwd

CORRECT_TEST_TITLE = '{"sig":"some_signed_data","data":{"title_number": "DN1"}}'
INCORRECT_TEST_TITLE = '{"missing closing speech marks :"some_signed_data","data":{"title_number": "DN1"}}'

# Set up root logger
logging.basicConfig(format='%(levelname)s %(asctime)s [SystemOfRecord] Message: %(message)s', level=logging.INFO, datefmt='%d.%m.%y %I:%M:%S %p')

class TestException(Exception):
    pass

class FakeSignedTitles():
    def __init__(self, set_id, record):
        self.id = set_id
        self.record = record

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
        self.assertEqual(response.data.decode("utf-8"), 'Integrity error. Check that title number, application reference and geometry application reference are unique. ')

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

    @mock.patch('application.server.linux_user')
    def test_make_log_message_with_title(self, mock_return):
        mock_return.return_value = 'user'
        self.assertEqual(make_log_msg('test message', 'DN1'), 'test message, Raised by: user, Title Number: DN1')

    @mock.patch('application.server.linux_user')
    def test_make_log_message_without_title(self, mock_return):
        mock_return.return_value = 'user'
        self.assertEqual(make_log_msg('test message', ''), 'test message, Raised by: user')

    @patch('application.server.pwd.getpwuid')
    def test_make_log_message_with_user_exception(self, mock_return):
        mock_return.side_effect = [ Exception('test') ]
        self.assertEqual(make_log_msg('test message', ''), 'test message, Raised by: failed to get user: test')

    def test_remove_username_password(self):
        self.assertEqual(remove_username_password('aprotocol://ausername:apassword@localhost:9876/'), 'aprotocol://localhost:9876/')
        self.assertEqual(remove_username_password(None), 'unknown endpoint')
    
    @patch('application.server.socket.socket')            
    def test_republish_connection_running(self, mock_socket):
        assert server.republish_connection() == mock_socket.return_value
        mock_socket.return_value.connect.assert_called_with("\0republish-socket")

    @patch('application.server.socket.socket')
    @patch('application.server.multiprocessing.Process')           
    def test_republish_connection_not_running_retry(self, mock_process, mock_socket):
        mock_socket.return_value.connect.side_effect = [ ConnectionRefusedError(), ConnectionRefusedError(), Mock() ]
        assert server.republish_connection() == mock_socket.return_value
        mock_socket.return_value.connect.assert_called_with("\0republish-socket")
        
    @patch('application.server.republish_connection')
    def test_republish_command(self, mock_connection):
        mock_connection.return_value.recv.return_value = b'{"result": "by your command"}'
        assert server.republish_command({'command': 'me'}) == "by your command"
        mock_connection.return_value.close.assert_called_with()        

    @patch('application.server.republish_command')
    def test_start_republish_nosync_ok(self, mock_republish_command):
        mock_republish_command.return_value = "Republish started"
        assert server.start_republish({'a':'thing'}, False) == "New republish job submitted"
        mock_republish_command.assert_called_with({'target': 'start', 'kwargs': {'a':'thing'}})
        
    @patch('application.server.republish_command')
    def test_start_republish_nosync_nook(self, mock_republish_command):
        mock_republish_command.return_value = "Something else happened"
        assert server.start_republish({'a':'thing'}, False) == "Something else happened"
        mock_republish_command.assert_called_with({'target': 'start', 'kwargs': {'a':'thing'}})
        
    @patch('application.server.republish_command')
    def test_start_republish_sync_ok(self, mock_republish_command):
        mock_republish_command.return_value = "Republish complete"
        assert server.start_republish({'a':'thing'}, True) == "Republish complete"
        mock_republish_command.assert_called_with({'target': 'sync_start', 'kwargs': {'a':'thing'}})
        
    @patch('application.server.republish_command')
    def test_start_republish_sync_nook(self, mock_republish_command):
        mock_republish_command.return_value = "Something else happened"
        with pytest.raises(Exception) as exc:
            assert server.start_republish({'a':'thing'}, True) == "Something else happened"
        mock_republish_command.assert_called_with({'target': 'sync_start', 'kwargs': {'a':'thing'}})

    @patch('application.server.republish_command')
    def test_republish_progress_true(self, mock_republish_command):
        mock_republish_command.return_value = {'is_running': True, 'other': 'stuff' }
        resp = self.app.get('/republish/progress')
        assert json.loads(resp.get_data().decode("UTF8")) == {"is_running": True, "republish_started": "true", "other": "stuff"}
        mock_republish_command.assert_called_with({'target': 'progress'})
    
    @patch('application.server.republish_command')
    def test_republish_progress_false(self, mock_republish_command):
        mock_republish_command.return_value = {'is_running': False, 'other': 'stuff' }
        resp = self.app.get('/republish/progress')
        assert json.loads(resp.get_data().decode("UTF8")) == {"is_running": False, "republish_started": "false", "other": "stuff"}
        mock_republish_command.assert_called_with({'target': 'progress'})

    @patch('application.server.republish_command')
    def test_resume_republish_started(self, mock_republish_command):
        mock_republish_command.return_value = "Started"
        resp = self.app.get('/republish/resume')
        assert resp.get_data() == b'republishing has been resumed'
        mock_republish_command.assert_called_with({'target': 'resume'})

    @patch('application.server.republish_command')
    def test_resume_republish_nothing(self, mock_republish_command):
        mock_republish_command.return_value = "Nothing to resume"
        resp = self.app.get('/republish/resume')
        assert resp.get_data() == b'Republishing cannot resume as no job in progress'
        mock_republish_command.assert_called_with({'target': 'resume'})

    @patch('application.server.republish_command')
    def test_resume_republish_other(self, mock_republish_command):
        mock_republish_command.return_value = "Rhubarb"
        resp = self.app.get('/republish/resume')
        assert resp.get_data() == b'Rhubarb'
        mock_republish_command.assert_called_with({'target': 'resume'})

    @patch('application.server.republish_command')
    def test_abort_republish_ok(self, mock_republish_command):
        mock_republish_command.return_value = "Reset"
        resp = self.app.get('/republish/abort')
        assert resp.get_data() == b'aborted republishing from System of Record'
        mock_republish_command.assert_called_with({'target': 'reset'})

    @patch('application.server.republish_command')
    def test_abort_republish_other(self, mock_republish_command):
        mock_republish_command.return_value = "Custard"
        resp = self.app.get('/republish/abort')
        assert resp.get_data() == b'Custard'
        mock_republish_command.assert_called_with({'target': 'reset'})

    @patch('application.server.republish_command')
    def test_pause_republish_ok(self, mock_republish_command):
        mock_republish_command.return_value = "Republish stopped"
        resp = self.app.get('/republish/pause')
        assert resp.get_data() == b'paused republishing from System of Record and will re-start on the resume command'
        mock_republish_command.assert_called_with({'target': 'stop'})

    @patch('application.server.republish_command')
    def test_pause_republish_other(self, mock_republish_command):
        mock_republish_command.return_value = "Rumplestiltskin"
        resp = self.app.get('/republish/pause')
        assert resp.get_data() == b'Rumplestiltskin'
        mock_republish_command.assert_called_with({'target': 'stop'})

    @patch('application.server.republish_command')
    def test_pause_republish_running(self, mock_republish_command):
        mock_republish_command.return_value = True
        resp = self.app.get('/republish/everything/status')
        assert resp.get_data() == b'running'
        mock_republish_command.assert_called_with({'target': 'running'})
        
    @patch('application.server.republish_command')
    def test_pause_republish_notrunning(self, mock_republish_command):
        mock_republish_command.return_value = False
        resp = self.app.get('/republish/everything/status')
        assert resp.get_data() == b'not running'
        mock_republish_command.assert_called_with({'target': 'running'})
        
    @patch('application.server.start_republish')
    def test_republish_everything_with_from_and_to_params(self, mock_start_republish):
        mock_start_republish.return_value = "New republish job submitted"
        resp = self.app.get('/republish/everything/2015-11-11T13:42:50.840623/2016-11-11T13:42:50.840623')
        assert resp.get_data() == b'New republish job submitted'
        mock_start_republish.assert_called_with({'start_date': '2015-11-11 13:42:50.840623', 'end_date': '2016-11-11 13:42:50.840623'})
        
    @patch('application.server.start_republish')
    def test_republish_everything_with_from_param(self, mock_start_republish):
        mock_start_republish.return_value = "New republish job submitted"
        resp = self.app.get('/republish/everything/2015-11-11T13:42:50.840623')
        assert resp.get_data() == b'New republish job submitted'
        mock_start_republish.assert_called_with({'start_date': '2015-11-11 13:42:50.840623'})
        
    @patch('application.server.start_republish')
    def test_republish_everything_without_params(self, mock_start_republish):
        mock_start_republish.return_value = "New republish job submitted"
        resp = self.app.get('/republish/everything')
        assert resp.get_data() == b'New republish job submitted'
        mock_start_republish.assert_called_with()
        
    @patch('application.server.start_republish')
    def test_republish_multiok(self, mock_start_republish):
        json = '{"titles": [ '
        json += '{"title_number":"A_TITLE1", "all_versions": true}, '
        json += '{"title_number":"A_TITLE2", "application_reference": "A_ABR2"}, '
        json += '{"title_number":"A_TITLE3", "application_reference": "A_ABR3", "geometry_application_reference": "A_GEO_ABR3"}, '
        json += '{"title_number":"A_TITLE4"}'
        json += ' ] }'
        resp = self.app.post('/republish', data=json, headers={'content-Type': 'application/json'})
        assert resp.get_data() == b'No errors.  Number of titles in JSON: 4'
        calls = []
        calls.append(call({'title_number': 'A_TITLE1'}, True))
        calls.append(call({'title_number': 'A_TITLE2', 'application_reference': 'A_ABR2'}, True))
        calls.append(call({'title_number': 'A_TITLE3', 'geometry_application_reference': 'A_GEO_ABR3', 'application_reference': 'A_ABR3'}, True))
        calls.append(call({'title_number': 'A_TITLE4', 'newest_only': True}, True))
        mock_start_republish.assert_has_calls(calls)
        
    @patch('application.server.start_republish')
    def test_republish_multi_except(self, mock_start_republish):
        mock_start_republish.side_effect = [ '', '', Exception("Something went wrong"), '']
        json = '{"titles": [ '
        json += '{"title_number":"A_TITLE1", "all_versions": true}, '
        json += '{"title_number":"A_TITLE2", "application_reference": "A_ABR2"}, '
        json += '{"title_number":"A_TITLE3", "application_reference": "A_ABR3", "geometry_application_reference": "A_GEO_ABR3"}, '
        json += '{"title_number":"A_TITLE4"}'
        json += ' ] }'
        resp = self.app.post('/republish', data=json, headers={'content-Type': 'application/json'})
        assert resp.get_data() == b'Completed republish.  4 titles in JSON. Number of errors: 1'
        calls = []
        calls.append(call({'title_number': 'A_TITLE1'}, True))
        calls.append(call({'title_number': 'A_TITLE2', 'application_reference': 'A_ABR2'}, True))
        calls.append(call({'title_number': 'A_TITLE3', 'geometry_application_reference': 'A_GEO_ABR3', 'application_reference': 'A_ABR3'}, True))
        calls.append(call({'title_number': 'A_TITLE4', 'newest_only': True}, True))
        mock_start_republish.assert_has_calls(calls)
