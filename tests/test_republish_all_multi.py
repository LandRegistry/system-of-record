import pytest
import unittest
from unittest.mock import patch, Mock, PropertyMock, call
from application.republish_all_multi import Republisher
from kombu import Queue

class RepublisherTest(unittest.TestCase):
    
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, "output_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    @patch.object(Republisher, "output_routing_key", create=True, new_callable=PropertyMock, return_value="A_ROUTING_KEY")
    @patch.object(Republisher, 'db_session', create=True)
    def test_query_sor_publish_ok(self, mock_db_session, mock_output_routing_key, mock_output_queue, mock_stop_event, mock_amqp_pool):
        mock_stop_event.is_set.side_effect = [ False, False ]
        mock_db_session.execute.return_value = [ { 'record': 'SOME_JSON', 'title': 'A_TITLE' }, { 'record': 'SOME_JSON2', 'title': 'A_TITLE2' }  ]
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        Republisher().query_sor_publish(10, 20)
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")
        calls = [ call("SOME_JSON", routing_key="A_ROUTING_KEY", content_type="application/json", headers={ 'title_number': "A_TITLE" }), 
                  call("SOME_JSON2", routing_key="A_ROUTING_KEY", content_type="application/json", headers={ 'title_number': "A_TITLE2" })]
        mock_queue.put.assert_has_calls(calls)
        mock_queue.close.assert_called_with()
        mock_conn.release.assert_called_with()
    
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, "output_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    @patch.object(Republisher, "output_routing_key", create=True, new_callable=PropertyMock, return_value="A_ROUTING_KEY")
    @patch.object(Republisher, 'db_session', create=True)
    def test_query_sor_publish_stopped(self, mock_db_session, mock_output_routing_key, mock_output_queue, mock_stop_event, mock_amqp_pool):
        mock_stop_event.is_set.side_effect = [ False, True ]
        mock_db_session.execute.return_value = [ { 'record': 'SOME_JSON', 'title': 'A_TITLE' }, { 'record': 'SOME_JSON2', 'title': 'A_TITLE2' }  ]
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        Republisher().query_sor_publish(10, 20)
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")
        calls = [ call("SOME_JSON", routing_key="A_ROUTING_KEY", content_type="application/json", headers={ 'title_number': "A_TITLE" })]
        mock_queue.put.assert_has_calls(calls)
        mock_queue.close.assert_called_with()
        mock_conn.release.assert_called_with()
    
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    @patch.object(Republisher, "process_message")
    @patch.object(Republisher, 'stop_event', create=True)
    def test_read_messages_stop(self, mock_stop_event, mock_process_message, mock_republish_queue, mock_amqp_pool):
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_messages = [ Mock(), Mock(), Mock() ]
        mock_queue.get.side_effect = mock_messages
        mock_stop_event.is_set.side_effect = [ False, False, True ]
        mock_queue.Empty = EOFError
        Republisher().read_messages()
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")
        mock_process_message.assert_has_calls([ call(mock_messages[0]), call(mock_messages[1]), call(mock_messages[2]) ])
        mock_messages[0].ack.assert_called_once_with()
        mock_messages[1].ack.assert_called_once_with()
        mock_messages[2].ack.assert_not_called()
        mock_queue.close.assert_called_with()
        mock_conn.release.assert_called_with()
    
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    @patch.object(Republisher, "process_message")
    @patch.object(Republisher, 'stop_event', create=True)
    def test_read_messages_empty(self, mock_stop_event, mock_process_message, mock_republish_queue, mock_amqp_pool):
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_messages = [ Mock(), Mock(), EOFError() ]
        mock_queue.get.side_effect = mock_messages
        mock_stop_event.is_set.return_value = False
        mock_queue.Empty = EOFError
        Republisher().read_messages()
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")
        mock_process_message.assert_has_calls([ call(mock_messages[0]), call(mock_messages[1]) ])
        mock_messages[0].ack.assert_called_once_with()
        mock_messages[1].ack.assert_called_once_with()
        mock_queue.close.assert_called_with()
        mock_conn.release.assert_called_with()
    
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    def test_send_messages_except(self, mock_republish_queue, mock_amqp_pool):
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_queue.put.side_effect = Exception("AN_EXCEPTION")
        with pytest.raises(Exception) as exc:
            Republisher().send_messages(10, 29, 10, {'arg1': "A_ARG"})
        mock_conn.release.assert_called_with()
        mock_queue.close.assert_called_with()
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")
        
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    def test_send_messages_even(self, mock_republish_queue, mock_amqp_pool):
        Republisher().send_messages(10, 29, 10, {'arg1': "A_ARG"})
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_conn.release.assert_called_with()
        mock_queue.close.assert_called_with()
        calls = [call({'id_end': 19, 'id_start': 10}, headers={'batch_size': 10, 'id_end': 29, 'id_start': 10, 'kwargs': {'arg1': 'A_ARG'}}, serializer='json'),
                 call({'id_end': 29, 'id_start': 20}, headers={'batch_size': 10, 'id_end': 29, 'id_start': 10, 'kwargs': {'arg1': 'A_ARG'}}, serializer='json')]
        mock_queue.put.assert_has_calls(calls)
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")
                
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    def test_send_messages_odd(self, mock_republish_queue, mock_amqp_pool):
        Republisher().send_messages(10, 30, 10, {'arg1': "A_ARG"})
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_conn.release.assert_called_with()
        mock_queue.close.assert_called_with()
        calls = [call({'id_end': 19, 'id_start': 10}, headers={'batch_size': 10, 'id_end': 30, 'id_start': 10, 'kwargs': {'arg1': 'A_ARG'}}, serializer='json'),
                 call({'id_end': 29, 'id_start': 20}, headers={'batch_size': 10, 'id_end': 30, 'id_start': 10, 'kwargs': {'arg1': 'A_ARG'}}, serializer='json'),
                 call({'id_end': 30, 'id_start': 30}, headers={'batch_size': 10, 'id_end': 30, 'id_start': 10, 'kwargs': {'arg1': 'A_ARG'}}, serializer='json')]
        mock_queue.put.assert_has_calls(calls)
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")

    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    def test_send_messages_one(self, mock_republish_queue, mock_amqp_pool):
        Republisher().send_messages(32, 32, 10, {'arg1': "A_ARG"})
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_conn.release.assert_called_with()
        mock_queue.close.assert_called_with()
        calls = [call({'id_end': 32, 'id_start': 32}, headers={'batch_size': 10, 'id_end': 32, 'id_start': 32, 'kwargs': {'arg1': 'A_ARG'}}, serializer='json')]
        mock_queue.put.assert_has_calls(calls)
        mock_conn.SimpleQueue.assert_called_with("A_QUEUE")
        
    @patch.object(Republisher, 'db_session', create=True)
    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, 'send_messages')
    def test_populate_queue_ids_title(self, mock_send_messages, mock_stop_event, mock_db_session):
        mock_db_session.execute.return_value.__iter__ = Mock(return_value=iter([{ 'id_start': 14, 'id_end': 14 }, { 'id_start': 10, 'id_end': 10 }]))
        mock_res = mock_db_session.execute.return_value.rowcount = 1
        Republisher().populate_queue_ids('A_TITLE', 'A_REFERENCE', 'A_GEO_REFERENCE', 'A_START_DATE', 'A_END_DATE', True, 100)
        mock_db_session.execute.assert_called_with("SELECT id as id_start, id as id_end FROM records WHERE 1=1 AND (record->'data'->>'title_number')::text = :title_number AND (record->'data'->>'application_reference')::text = :application_reference AND (record->'data'->>'geometry_application_reference')::text = :geometry_application_reference AND created_date >= :start_date AND created_date <= :end_date ORDER BY id DESC LIMIT 1 ",
                                                   {'start_date': 'A_START_DATE', 'application_reference': 'A_REFERENCE', 'end_date': 'A_END_DATE',
                                                    'geometry_application_reference': 'A_GEO_REFERENCE', 'title_number': 'A_TITLE'})
        mock_db_session.remove.assert_called_with()
        mock_send_messages.assert_has_calls([ call(14, 14, 100, {'application_reference': 'A_REFERENCE', 'start_date': 'A_START_DATE',
                                                                 'geometry_application_reference': 'A_GEO_REFERENCE', 'title_number': 'A_TITLE', 'newest_only': True,
                                                                 'end_date': 'A_END_DATE'}),
                                            call(10, 10, 100, {'application_reference': 'A_REFERENCE', 'start_date': 'A_START_DATE',
                                                               'geometry_application_reference': 'A_GEO_REFERENCE', 'title_number': 'A_TITLE', 'newest_only': True,
                                                               'end_date': 'A_END_DATE'})])
        
    @patch.object(Republisher, 'db_session', create=True)
    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, 'send_messages')
    def test_populate_queue_ids_range(self, mock_send_messages, mock_stop_event, mock_db_session):
        mock_db_session.execute.return_value.__iter__ = Mock(return_value=iter([{ 'id_start': 14, 'id_end': 200 }]))
        mock_res = mock_db_session.execute.return_value.rowcount = 1
        Republisher().populate_queue_ids(None, None, None, 'A_START_DATE', 'A_END_DATE', False, 123)
        mock_db_session.execute.assert_called_with('SELECT min(id) as id_start, max(id) as id_end FROM records WHERE 1=1 AND created_date >= :start_date AND created_date <= :end_date ',
                                                   {'start_date': 'A_START_DATE', 'end_date': 'A_END_DATE'})
        mock_db_session.remove.assert_called_with()
        mock_send_messages.assert_has_calls([ call(14, 200, 123, {'application_reference': None, 'start_date': 'A_START_DATE',
                                                                 'geometry_application_reference': None, 'title_number': None, 'newest_only': False,
                                                                 'end_date': 'A_END_DATE'}) ])   
             
    @patch.object(Republisher, 'db_session', create=True)
    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, 'send_messages')
    def test_populate_queue_ids_noids(self, mock_send_messages, mock_stop_event, mock_db_session):
        mock_db_session.execute.return_value.__iter__ = Mock(return_value=iter([{ 'id_start': None, 'id_end': None }]))
        mock_res = mock_db_session.execute.return_value.rowcount = 1
        with pytest.raises(Exception) as exc:
            Republisher().populate_queue_ids(None, None, None, 'A_START_DATE', 'A_END_DATE', False, 123)
        mock_db_session.execute.assert_called_with('SELECT min(id) as id_start, max(id) as id_end FROM records WHERE 1=1 AND created_date >= :start_date AND created_date <= :end_date ',
                                                   {'start_date': 'A_START_DATE', 'end_date': 'A_END_DATE'})
        mock_db_session.remove.assert_called_with()
 
    @patch.object(Republisher, 'db_session', create=True)
    @patch.object(Republisher, 'stop_event', create=True)
    def test_populate_queue_ids_none(self, mock_stop_event, mock_db_session):
        mock_db_session.execute.return_value.__iter__ = Mock(return_value=iter([]))
        mock_res = mock_db_session.execute.return_value.rowcount = 0
        with pytest.raises(Exception) as exc:
            Republisher().populate_queue_ids(None, None, None, 'A_START_DATE', 'A_END_DATE', False, 123)
        mock_db_session.execute.assert_called_with('SELECT min(id) as id_start, max(id) as id_end FROM records WHERE 1=1 AND created_date >= :start_date AND created_date <= :end_date ',
                                                   {'start_date': 'A_START_DATE', 'end_date': 'A_END_DATE'})
        mock_db_session.remove.assert_called_with()
        
    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, "is_running", return_value=False)
    @patch.object(Republisher, "threads", create=True, new_callable=PropertyMock, return_value=5)
    @patch.object(Republisher, "queue_count", return_value=1)
    @patch.object(Republisher, "read_messages")
    @patch("application.republish_all_multi.threading.Thread")
    def test_start_consumers_running(self, mock_thread, mock_read_messages, mock_queue_count, mock_threads, mock_is_running, mock_stop_event):
        assert Republisher().start_consumers() == "Started"
        calls = [ call(target=mock_read_messages) for x in range(5) ]
        calls += [ call().start() for x in range(5) ]
        mock_thread.assert_has_calls(calls, True)
        mock_stop_event.clear.assert_called_with()
    
    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, "is_running", return_value=True)
    def test_start_consumers_notrunning(self, mock_is_running, mock_stop_event):
        assert Republisher().start_consumers() == "Already running"
        mock_stop_event.clear.assert_called_with()

    @patch.object(Republisher, 'stop_event', create=True)
    @patch.object(Republisher, "is_running", return_value=False)
    @patch.object(Republisher, "queue_count", return_value=0)    
    def test_start_consumers_nothing(self, mock_queue_count, mock_is_running, mock_stop_event):
        assert Republisher().start_consumers() == "Nothing to resume"
        mock_stop_event.clear.assert_called_with()
    
    @patch.object(Republisher, "is_running", return_value=False)
    @patch.object(Republisher, "queue_count", return_value=0)
    @patch.object(Republisher, "set_progress")
    @patch.object(Republisher, "populate_queue_ids")
    @patch.object(Republisher, "start_consumers")    
    def test_start_republish_ok(self, mock_start_consumers, mock_populate_queue_ids, mock_set_progress, mock_queue_count, mock_is_running):
        assert Republisher().start_republish("A_TITLE", "A_REFERENCE", "A_GEO_REFERENCE", "A_START_DATE", "A_END_DATE", True, 99) == "Republish started"
        mock_set_progress.assert_called_with()
        mock_populate_queue_ids.assert_called_with("A_TITLE", "A_REFERENCE", "A_GEO_REFERENCE", "A_START_DATE", "A_END_DATE", True, 99)
        mock_start_consumers.assert_called_with()
        
    @patch.object(Republisher, "is_running", return_value=True)
    def test_start_republish_running(self, mock_is_running):
        assert Republisher().start_republish() == "Already running"
    
    @patch.object(Republisher, "is_running", return_value=False)
    @patch.object(Republisher, "queue_count", return_value=1)
    def test_start_republish_notcomplete(self, mock_queue_count, mock_is_running):
        assert Republisher().start_republish() == "Not running but republish not complete - resume to continue"
    
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="A_QUEUE")
    @patch.object(Republisher, "stop_republish")
    @patch.object(Republisher, "amqp_pool", create=True)   
    @patch.object(Republisher, 'consumer_threads', create=True)
    def test_reset_republish_ok(self, mock_consumer_threads, mock_amqp_pool, mock_stop_republish, mock_queue_name):
        thread = Mock()
        mock_consumer_threads.__iter__ = Mock(return_value=iter([thread, thread]))
        assert Republisher().reset_republish() == "reset"
        mock_stop_republish.assert_called_with()
        connection = mock_amqp_pool.acquire.return_value
        connection.SimpleQueue.assert_called_with("A_QUEUE")
        queue = connection.SimpleQueue.return_value
        queue.clear.assert_called_with()
        queue.close.assert_called_with()
        thread.join.assert_has_calls([call(), call()])
    
    @patch.object(Republisher, "start_republish", return_value="START_RESULT")
    def test_handle_connection_start(self, mock_method):
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "start", "kwargs": { "arg1": "value1", "arg2": "value2" } }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "START_RESULT"}')
        
    @patch.object(Republisher, "start_republish", return_value="Republish started")
    @patch.object(Republisher, "consumer_threads", create=True)   
    def test_handle_connection_sync_start(self, mock_consumer_threads, mock_method):
        thread = Mock()
        mock_consumer_threads.__iter__ = Mock(return_value=iter([thread, thread]))
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "sync_start", "kwargs": { "arg1": "value1", "arg2": "value2" } }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "Republish complete"}')
        thread.join.assert_has_calls([call(), call()])
        
    @patch.object(Republisher, "stop_republish", return_value="STOP_RESULT")
    def test_handle_connection_stop(self, mock_method):
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "stop" }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "STOP_RESULT"}')
    
    @patch.object(Republisher, "is_running", return_value="RUNNING_RESULT")
    def test_handle_connection_running(self, mock_method):
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "running" }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "RUNNING_RESULT"}')
    
    @patch.object(Republisher, "reset_republish", return_value="RESET_RESULT")
    def test_handle_connection_reset(self, mock_method):
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "reset" }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "RESET_RESULT"}')
    
    @patch.object(Republisher, "start_consumers", return_value="RESUME_RESULT")
    def test_handle_connection_resume(self, mock_method):
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "resume" }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "RESUME_RESULT"}')
    
    @patch.object(Republisher, "republish_progress", return_value="PROGRESS_RESULT")
    def test_handle_connection_progress(self, mock_method):
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "progress" }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "PROGRESS_RESULT"}')
 
    def test_handle_connection_unknown(self):
        mock_conn = Mock()
        mock_conn.recv.return_value =  b'{ "target": "wibble" }'
        Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "unknown command"}')
    
    def test_handle_connection_exception(self):
        mock_conn = Mock()
        mock_conn.recv.side_effect = Exception("AN_EXCEPTION")
        with pytest.raises(Exception) as exc:
            Republisher().handle_connection(mock_conn, Mock())
        mock_conn.sendall.assert_called_with(b'{"result": "failed to process request: Exception - AN_EXCEPTION"}')

    @patch("application.republish_all_multi.socket.socket")
    @patch("application.republish_all_multi.create_engine")
    @patch("application.republish_all_multi.sessionmaker")
    @patch("application.republish_all_multi.scoped_session")
    @patch("application.republish_all_multi.threading.Thread")
    @patch("application.republish_all_multi.Connection")
    @patch.object(Republisher, "handle_connection")
    @patch.object(Republisher, "stop_event", create=True, new_callable=PropertyMock)
    def test_republish_process(self, mock_stop_event, mock_handle_conn, mock_conn, mock_thread, mock_session, mock_session_maker, mock_engine, mock_socket):
        mock_thread_instance = mock_thread.return_value
        mock_thread_instance.join.side_effect = SystemExit()
        Republisher().republish_process("DB_URI", "AMQP_URI", "REPUBLISH_QUEUE", "OUTPUT_QUEUE", "OUTPUT_ROUTING_KEY", 21)
        mock_socket.return_value.close.assert_called_with()
        mock_thread.assert_called_with(target=mock_handle_conn, args=mock_socket.return_value.accept())
        mock_stop_event.return_value.set.assert_called_with()
    
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="a_queue")
    def test_queue_count_ok(self, mock_republish_queue, mock_amqp_pool):
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_queue.qsize.return_value = 10
        assert Republisher().queue_count() == 10
        mock_conn.SimpleQueue.assert_called_with("a_queue")
        mock_queue.close.assert_called_with()
        mock_conn.release.assert_called_with()
        
    @patch.object(Republisher, "amqp_pool", create=True)
    @patch.object(Republisher, "republish_queue", create=True, new_callable=PropertyMock, return_value="a_queue")
    def test_queue_count_except(self, mock_republish_queue, mock_amqp_pool):
        mock_conn = mock_amqp_pool.acquire.return_value
        mock_queue = mock_conn.SimpleQueue.return_value
        mock_queue.qsize.side_effect = Exception("Some error")
        with pytest.raises(Exception) as exc:
            Republisher().queue_count()
        mock_conn.SimpleQueue.assert_called_with("a_queue")
        mock_queue.close.assert_called_with()
        mock_conn.release.assert_called_with()
                
    @patch.object(Republisher, "queue_count", return_value=20)
    @patch.object(Republisher, "progress_end", create=True, new_callable=PropertyMock, return_value=4000)
    @patch.object(Republisher, "progress_start", create=True, new_callable=PropertyMock, return_value=1)
    @patch.object(Republisher, "progress_batch", create=True, new_callable=PropertyMock, return_value=100)
    @patch.object(Republisher, "is_running", return_value=True)
    def test_republish_progress_ok(self, mock_is_running, mock_progress_batch, mock_progress_start, mock_progress_end, mock_queue_count):
        assert Republisher().republish_progress() == { 'batch_size': 100, 'id_end': 4000, 'id_start': 1, 'is_running': True, 'messages_remaining': 20, 
                                                      'percent_complete': 50.0 }

    @patch.object(Republisher, "queue_count", return_value=20)
    @patch.object(Republisher, "progress_end", create=True, new_callable=PropertyMock, return_value=4000)
    @patch.object(Republisher, "progress_start", create=True, new_callable=PropertyMock, return_value=1)
    @patch.object(Republisher, "progress_batch", create=True, new_callable=PropertyMock, return_value=0)
    @patch.object(Republisher, "is_running", return_value=False)
    def test_republish_progress_calc_fail(self, mock_is_running, mock_progress_batch, mock_progress_start, mock_progress_end, mock_queue_count):
        assert Republisher().republish_progress() == { 'batch_size': 0, 'id_end': 4000, 'id_start': 1, 'is_running': False, 'messages_remaining': 20, 
                                                      'percent_complete': -1 }            
    
    @patch.object(Republisher, 'consumer_threads', create=True)
    def test_is_running_running(self, mock_consumer_threads):
        thread = Mock()
        thread.is_alive.side_effect = [ False, True ]
        mock_consumer_threads.__iter__ = Mock(return_value=iter([thread, thread]))
        assert Republisher().is_running() == True
        
    @patch.object(Republisher, 'consumer_threads', create=True)
    def test_is_running_not_running(self, mock_consumer_threads):
        thread = Mock()
        thread.is_alive.side_effect = [ False, False ]
        mock_consumer_threads.__iter__ = Mock(return_value=iter([thread, thread]))
        assert Republisher().is_running() == False
        
    @patch.object(Republisher, 'query_sor_publish')
    @patch.object(Republisher, 'set_progress')
    def test_process_message(self, mock_set_progress, mock_query_sor_publish):
        mock_message = Mock(payload={ 'id_start': 12, 'id_end': 29 }, headers={ 'id_start': 12, 'id_end': 29, 'batch_size': 123, 'kwargs': 'BLAH' })
        Republisher().process_message(mock_message)
        mock_query_sor_publish.assert_called_with(12, 29)
        mock_set_progress.assert_called_with(12, 29, 123, 'BLAH')

    @patch.object(Republisher, 'is_running', return_value=True)
    @patch.object(Republisher, 'stop_event', create=True)
    def test_stop_republish_running(self, mock_stop_event, mock_is_running):
        assert Republisher().stop_republish() == "Republish stopped"
        mock_stop_event.set.assert_called_with()
        
    @patch.object(Republisher, 'is_running', return_value=False)
    @patch.object(Republisher, 'stop_event', create=True)
    def test_stop_republish_not_running(self, mock_stop_event, mock_is_running):
        assert Republisher().stop_republish() == "Republish stopped"
        mock_stop_event.set.assert_not_called()
