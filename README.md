# system-of-record
At the moment this service posts data to a postgres database.

##requirements:
- postgres
- rabbitmq
- python 3
- python modules listed in requirements.txt

##How to run

```
vagrant up
```

```
vagrant ssh
```

```
cd /vagrant
```

```
source ~/venvs/system-of-record/bin/activate
```

```
./run.sh -d
```

Note:  Occasionally there is an issue starting Rabbitmq if you are already running a Register Publisher VM.

##how to run tests
In virtual machine

```
./test.sh
```

##How to run the tester service

```
cd srv/system-of-record
workon system-of-record
python run_tester.py

```
###To count the rows on postgres
```
curl http://127.0.0.1:5002/count
```

###To get the data for the last row on postgres
```
curl http://127.0.0.1:5002/getlastrecord
```

###To delete the last row on postgres
```
curl http://127.0.0.1:5002/deletelastrecord
```

###To get and remove the last message from RabbitMQ
```
curl http://127.0.0.1:5002/getnextqueuemessage
```

##How to insert a row
Note:  Use 0.0.0.0 when running from host.  Use 10.0.2.2 when calling from another VM.

```
curl -X POST -d '{"sig":"some_signed_data","data":{"title_number": "DN1", "application_reference":"ABR123"}}' -H "Content-Type: application/json" http://127.0.0.1:5001/insert
```

##How to republish messages for stored titles:

###Republish latest version of one title:

```
curl -X POST -d '{"titles": [{"title_number":"DN1"}]}' -H "Content-Type: application/json" http://127.0.0.1:5001/republish
```

###Republish all versions of a title with the same ABR (NB. Multiple versions are possible where geometry application references differ)

```
curl -X POST -d '{"titles": [{"title_number":"DN1", "application_reference": "ABR123"}]}' -H "Content-Type: application/json" http://127.0.0.1:5001/republish
```

###Republish specific version of a title 

```
curl -X POST -d '{"titles": [{"title_number":"DN1", "application_reference": "ABR123", "geometry_application_reference": "GEO123"}]}' -H "Content-Type: application/json" http://127.0.0.1:5001/republish
```
###Republish more than one title in a single message:
```
curl -X POST -d '{"titles": [{"title_number":"DN1", "application_reference": "ABR123"}, {"title_number":"DN2", "application_reference": "ABR1234"}, {"title_number":"DN3", "application_reference": "ABR12345"} ]}' -H "Content-Type: application/json" http://127.0.0.1:5001/republish
```

###Republish all versions of a title:
```
curl -X POST -d '{"titles": [{"title_number":"DN1", "all_versions":true}]}' -H "Content-Type: application/json" http://127.0.0.1:5001/republish
```

###Republish everything:
```
curl http://127.0.0.1:5001/republish/everything
```

The republisheverything endpoint creates a 'republish_progress.json' file.  This file is populated with a count value
and the last id on the target database.  After the file is created, a thread iterates through the system of record database 100 rows at a time and writes the json record and title number to the 'register_publisher' queue.  
When the 'last_id' value is reached, the file will be deleted.

 

The threads are spawned in republish_all.py, which is called in the init of the flask app. 


##How to check that the service is running:

```
curl http://127.0.0.1:5001/
```

##How to manage rabbitmq:
Status of the server

```
service rabbitmq-server status
```

Stop the server

```
service rabbitmq-server stop
```

Start the server

```
service rabbitmq-server start
```

List queues, and show queue detail

```
rabbitmqadmin list queues
```

or

```
sudo rabbitmqctl list_queues
```

put a message on the queue:

```
rabbitmqadmin publish exchange=amq.default routing_key=system_of_record payload="hello, world"
```

##How to update the database, if necessary

```
source ./environment.sh
```

```
python3 manage.py db upgrade
```

##How to query the database with PSQL

- Login to the centos virtual machine.
- switch to root with

```
sudo -i
```

- login to the system of record database with this

```
psql -U systemofrecord systemofrecord
```

The main table in the systemofrecord database is called records. To describe this table use the following command

```
\d records
```

To query, update, delete from the table use sql.

```
select * from records;
```
