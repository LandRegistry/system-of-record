#!/usr/bin/python

import multiprocessing
import socket
import threading
import sys
import json
import time
import math
from kombu import Connection, Producer, Exchange, Queue
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import *
import pwd
import datetime
import sys
import logging
import os

logging.basicConfig(format='%(levelname)s %(asctime)s [SystemOfRecord] Message: %(message)s', level=logging.INFO, datefmt='%d.%m.%y %I:%M:%S %p')

class Republisher:
    """Republisher class for republishing from the system or record.  Designed to be run as a multiprocessing process
    calling the republish_process method"""
    
    def republish_process(self, db_uri, amqp_uri, republish_queue, output_queue, output_routing_key, threads=10):
        """Main republishing method.  Binds to socket for communications, establishes connection pooling independent of
        system of record, and accepts connections, spawning a thread to handle each connection.  Designed to be called as
        a multiprocessing process."""
        self.stop_event = threading.Event()
        self.republish_queue = republish_queue
        self.output_queue = output_queue
        self.output_routing_key = output_routing_key
        self.threads = threads
        self.consumer_threads = []
        self.set_progress()

        logging.info(self.make_log_msg( 'Creating socket...' ) )
        republish_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        logging.info(self.make_log_msg( 'Binding to socket...' ) )
        republish_socket.bind("\0republish-socket")
        logging.info(self.make_log_msg( 'Listening on socket...' ) )
        republish_socket.listen(10)
        logging.info(self.make_log_msg( 'Socket now listening' ) )
        logging.info(self.make_log_msg( 'Establishing DB pool...' ) )
        engine = create_engine(db_uri, pool_size=threads + 1)
        session_factory = sessionmaker(bind=engine)
        self.db_session = scoped_session(session_factory)
        logging.info(self.make_log_msg( 'Establishing AMQP pool...' ) )
        self.amqp_pool = Connection(amqp_uri).Pool((threads * 2) + 1)
        logging.info(self.make_log_msg( 'Pools established' ) )
        logging.info(self.make_log_msg( 'Handling connections...' ) )
        while 1:
            try:
                t = threading.Thread(target=self.handle_connection, args=republish_socket.accept())
                t.start()
                #Too much hassle to handle concurrent connections so just wait until done before accepting the next one
                t.join()
            except (KeyboardInterrupt, SystemExit):
                logging.info(self.make_log_msg( 'Stopping republisher' ) )
                self.stop_event.set()
                break
        republish_socket.close()
        
    def set_progress(self, start=-1, end=-1, batch=-1, kwargs={}):
        """Sets progress of the current republish"""
        self.progress_start = start
        self.progress_end = end
        self.progress_batch = batch
        self.progress_kwargs = kwargs
        
    def handle_connection(self, conn, addr):
        """Handles connection from socket, calling appropriate method.  Designed to be called as a threading thread"""
        logging.info(self.make_log_msg( 'Thread %s: Accepted client connection' % (threading.current_thread().ident) ) )
        try:
            data = json.loads(conn.recv(10240).decode("utf-8"))
            command = data['target']
            if command == 'start':
                conn.sendall(json.dumps({ "result": self.start_republish(**data['kwargs']) }).encode("utf-8"))
            elif command == 'sync_start':
                res = self.start_republish(**data['kwargs'])
                if res == "Republish started":
                    for thread in self.consumer_threads:
                        thread.join()
                    res = "Republish complete"
                conn.sendall(json.dumps({ "result": res }).encode("utf-8"))
            elif command == 'stop':
                conn.sendall(json.dumps({ "result": self.stop_republish() }).encode("utf-8"))
            elif command == 'running':
                conn.sendall(json.dumps({ "result": self.is_running() }).encode("utf-8"))
            elif command == 'reset':
                conn.sendall(json.dumps({ "result": self.reset_republish() }).encode("utf-8"))
            elif command == 'resume':
                conn.sendall(json.dumps({ "result": self.start_consumers() }).encode("utf-8"))
            elif command == 'progress':
                conn.sendall(json.dumps({ "result": self.republish_progress() }).encode("utf-8"))
            else:
                conn.sendall(json.dumps({ "result": "unknown command" }).encode("utf-8"))
        except:
            conn.sendall(json.dumps({ "result": "failed to process request: %s - %s" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1])) }).encode("utf-8"))
            raise
        finally:
            conn.close()
            logging.info(self.make_log_msg( 'Thread %s: Client Disconnected' % (threading.current_thread().ident) ) )
        
    def republish_progress(self):
        """Returns the current republish progress as a dictionary"""
        remain_msg = self.queue_count()
        try:
            total_msg = math.ceil((self.progress_end - self.progress_start) / self.progress_batch)
            percent = 100 * ((total_msg - remain_msg) / total_msg)
        except:
            percent = -1
        return { 'percent_complete': percent, 'id_start': self.progress_start, 'id_end': self.progress_end, 'batch_size': self.progress_batch, 
                'messages_remaining': remain_msg, 'is_running': self.is_running() }
        
        
    def reset_republish(self):
        """Stops the current republish and clears the republish input queue"""
        self.stop_republish()
        for thread in self.consumer_threads:
            thread.join()
        logging.info(self.make_log_msg( 'Thread %s: Clearing republish queue...' % (threading.current_thread().ident) ) )
        connection = self.amqp_pool.acquire(block=True, timeout=10)
        input_queue = connection.SimpleQueue(self.republish_queue)
        try:
            input_queue.clear()
            self.set_progress()
        finally:
            input_queue.close()
            connection.release()
            logging.info(self.make_log_msg( 'Thread %s: Released connection' % (threading.current_thread().ident) ) )
        return "reset"
    
    def is_running(self):
        """Returns boolean of whether a republish is in progress"""
        for thread in self.consumer_threads:
            if thread.is_alive():
                return True
        return False
        
    def start_republish(self, title_number=None, application_reference=None, geometry_application_reference=None, start_date=None, end_date=None, newest_only=False, block_size=100):
        """Starts a republish with the supplied requirements"""
        if self.is_running():
            return "Already running"
        if self.queue_count() > 0:
            return("Not running but republish not complete - resume to continue")
        else:
            self.set_progress()
            self.populate_queue_ids(title_number, application_reference, geometry_application_reference, start_date, end_date, newest_only, block_size)
            self.start_consumers()
        return "Republish started"
    
    def start_consumers(self):
        """Starts consumers in their own threads"""
        self.stop_event.clear()
        if self.is_running():
            return "Already running"
        elif self.queue_count() <= 0:
            return "Nothing to resume"
        else:
            self.consumer_threads = []
            for _x in range(self.threads):
                thread = threading.Thread(target=self.read_messages)
                thread.start()
                self.consumer_threads.append(thread)
            return "Started"
    
    def stop_republish(self):
        """Stops republishing threads via event"""
        if self.is_running():
            self.stop_event.set()
        return "Republish stopped"
    
    def queue_count(self):
        """Returns count of republishing queue"""
        logging.info(self.make_log_msg( 'Thread %s: Retrieving count from republish queue...' % (threading.current_thread().ident) ) )
        connection = self.amqp_pool.acquire(block=True, timeout=10)
        input_queue = connection.SimpleQueue(self.republish_queue)
        try:
            count = -1
            count = input_queue.qsize()
        finally:
            input_queue.close()
            connection.release()
            logging.info(self.make_log_msg( 'Thread %s: Released connection' % (threading.current_thread().ident) ) )
        return count
    
    def populate_queue_ids(self, title_number, application_reference, geometry_application_reference, start_date, end_date, newest_only, block_size):
        """Queries SOR DB for id range(s) for the supplied republish criteria""" 
        sql = "SELECT "
        params = {}
        
        if title_number or application_reference or geometry_application_reference:
            sql = sql + "id as id_start, id as id_end FROM records WHERE 1=1 "
        else:
            sql = sql + "min(id) as id_start, max(id) as id_end FROM records WHERE 1=1 " 
            
        if title_number:
            sql = sql + "AND (record->'data'->>'title_number')::text = :title_number "
            params['title_number'] = title_number
        if application_reference:
            sql = sql + "AND (record->'data'->>'application_reference')::text = :application_reference "
            params['application_reference'] = application_reference
        if geometry_application_reference:
            sql = sql + "AND (record->'data'->>'geometry_application_reference')::text = :geometry_application_reference "
            params['geometry_application_reference'] = geometry_application_reference
        if start_date:
            sql = sql + "AND created_date >= :start_date "
            params['start_date'] = start_date
        if end_date:
            sql = sql + "AND created_date <= :end_date "
            params['end_date'] = end_date
        if newest_only:
            sql = sql + "ORDER BY id DESC LIMIT 1 "
        logging.info(self.make_log_msg( 'Thread %s: Retrieving ID(s) from DB...' % (threading.current_thread().ident) ) )
        try:
            rows = self.db_session.execute(sql, params)
            if rows.rowcount < 1:
                logging.info(self.make_log_msg( 'No rows for republish criteria' ) )
                raise Exception("No rows for republish criteria")
            for row in rows:
                if row['id_start'] and row['id_end']:
                    self.send_messages(row['id_start'], row['id_end'], block_size, { 'title_number': title_number, 'application_reference': application_reference,
                                                                                     'geometry_application_reference': geometry_application_reference, 'start_date': start_date,
                                                                                     'end_date': end_date, 'newest_only': newest_only })
                else:
                    logging.info(self.make_log_msg( 'No IDs for republish criteria' ) )
                    raise Exception("No IDs for republish criteria")
        finally:
            self.db_session.remove()
            logging.info( self.make_log_msg( 'Thread %s: Released connection' % (threading.current_thread().ident) ) )
            
    def send_messages(self, id_start, id_end, batch_size, kwargs):
        """Sends messages to the republish queue for the supplied id range.  Set message headers to contain information on the current republish"""
        logging.info( self.make_log_msg( 'Thread %s: Sending republish messages for ID(s) %s - %s' % (threading.current_thread().ident, id_start, id_end) ) )
        connection = self.amqp_pool.acquire(block=True, timeout=10)
        input_queue = connection.SimpleQueue(self.republish_queue)
        try:
            current_start = id_start
            while current_start <= id_end:
                current_end = current_start + (batch_size - 1)
                if current_end > id_end:
                    current_end = id_end
                input_queue.put({ "id_start": current_start, "id_end": current_end },
                                serializer='json',
                                headers={ 'id_start': id_start, 'id_end': id_end, 'batch_size': batch_size, 'kwargs': kwargs })
                current_start += batch_size
        finally:
            input_queue.close()
            connection.release()
            logging.info( self.make_log_msg( 'Thread %s: Released connection' % (threading.current_thread().ident) ) )
    
    def read_messages(self):
        """Main consuming thread, reads messages one by one endlessly until stopped or the queue is empty.  Designed to be run as a threading Thread."""
        logging.info(self.make_log_msg( 'Thread %s: Retrieving republish messages...' % (threading.current_thread().ident) ) )
        connection = self.amqp_pool.acquire(block=True, timeout=10)
        input_queue = connection.SimpleQueue(self.republish_queue)
        try:
            input_queue.consumer.qos(prefetch_count=1)
            while 1:
                message = input_queue.get(block=True, timeout=10)
                self.process_message(message)
                if self.stop_event.is_set():
                    logging.info(self.make_log_msg( 'Thread %s: Stopping thread' % (threading.current_thread().ident) ) )
                    break
                message.ack()
        except input_queue.Empty:
            logging.info(self.make_log_msg( 'Thread %s: No more messages' % (threading.current_thread().ident) ) )
        finally:
            input_queue.close()
            connection.release()
                                
    def process_message(self, message):
        """Processes the supplied message, set progress information for the current republish, and make call to query database"""
        payload = message.payload
        self.set_progress(message.headers['id_start'], message.headers['id_end'], message.headers['batch_size'], message.headers['kwargs'])
        self.query_sor_publish(payload['id_start'], payload['id_end'])
        
    def query_sor_publish(self, id_start, id_end):
        """Query SOR for json for the given id range and publish each to the output queue"""
        logging.info(self.make_log_msg( 'Thread %s: Preparing to send messages to output queue...' % (threading.current_thread().ident) ) )
        connection = self.amqp_pool.acquire(block=True, timeout=10)
        publisher_queue = connection.SimpleQueue(self.output_queue)
        try:
            logging.info(self.make_log_msg( 'Thread %s: Retrieving and publishing record(s) %s - %s' % (threading.current_thread().ident, id_start, id_end) ) )
            sql = "SELECT id, (record->'data'->>'title_number')::text as title, record::text as record FROM records WHERE id BETWEEN :id_start AND :id_end ORDER BY id"
            params = { "id_start": id_start, "id_end": id_end }
            for row in self.db_session.execute(sql, params):
                if self.stop_event.is_set():
                    logging.info(self.make_log_msg( 'Thread %s: Stopping republishing' % (threading.current_thread().ident) ) )
                    break
                publisher_queue.put(row['record'], routing_key=self.output_routing_key, content_type="application/json",
                                    headers={ 'title_number': row['title'] })
            logging.info(self.make_log_msg( 'Thread %s: Records republished' % (threading.current_thread().ident) ) )
        finally:
            publisher_queue.close()
            connection.release()

    def make_log_msg(self, message, title_number=''):
        user = self.linux_user()
        if title_number == '':
            return "{}, Raised by: {}".format( message, user )
        else:
            return "{}, Raised by: {}, Title Number: {}".format( message, user, title_number )

    def linux_user(self):
        try:
            return pwd.getpwuid(os.geteuid()).pw_name
        except Exception as err:
            return "failed to get user: %s" % err