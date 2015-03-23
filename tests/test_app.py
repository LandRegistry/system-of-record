import unittest
from application import server
from application.server import app, publish_json_to_queue
import os
import mock

CORRECT_TEST_TITLE = '{"sig":"some_signed_data","data":{"titleno": "DN1"}}'
INCORRECT_TEST_TITLE = '{"missing closing speech marks :"some_signed_data","data":{"titleno": "DN1"}}'

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        app.config.from_object(os.environ.get('SETTINGS'))
        self.app = server.app.test_client()

    def test_config_variables_blank(self):
        self.assertEqual(app.config['RABBIT_ENDPOINT'], '')
        self.assertEqual(app.config['RABBIT_QUEUE'], '')
        self.assertEqual(app.config['RABBIT_ROUTING_KEY'], '')


    def test_server_code(self):
        self.assertEqual((self.app.get('/')).status, '200 OK')


    def test_server_message(self):
        self.assertEqual((self.app.get('/')).data.decode("utf-8"), "Everything is OK")


    @mock.patch('application.server.db.session.add')
    @mock.patch('application.server.db.session.commit')
    @mock.patch('application.server.db.session.flush')
    @mock.patch('application.server.publish_json_to_queue')
    def test_insert_route_correctly(self, mock_add, mock_commit, mock_flush, mock_publish_json_to_queue):
        mock_add.side_effect = self.pretend_db_session_add()
        mock_commit.side_effect = self.pretend_db_session_commit()
        mock_flush.side_effect = self.pretend_db_session_flush()
        mock_publish_json_to_queue = self.pretend_publish_json_to_queue

        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = CORRECT_TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '201 CREATED')
        self.assertEqual(response.data.decode("utf-8"), 'row inserted')


    @mock.patch('application.server.db.session.add')
    @mock.patch('application.server.db.session.commit')
    @mock.patch('application.server.db.session.flush')
    def test_insert_route_incorrectly(self, mock_add, mock_commit, mock_flush):
        mock_add.side_effect = self.pretend_db_session_add()
        mock_commit.side_effect = self.pretend_db_session_commit()
        mock_flush.side_effect = self.pretend_db_session_flush()

        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = INCORRECT_TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '400 BAD REQUEST')


    def pretend_db_session_add(self):
        app.logger.info('pretend_db_session_add called')

    def pretend_db_session_commit(self):
        app.logger.info('pretend_db_session_commit called')

    def pretend_db_session_flush(self):
        app.logger.info('pretend_db_session_flush called')

    def pretend_publish_json_to_queue(self):
        app.logger.info('pretend_publish_json_to_queue called')
