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

##how to run tests
In virtual machine

```
./test.sh
```

##How to run the tester service

```
cd /vagrant
./run-tester.sh -d
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
curl -X POST -d '{"sig":"some_signed_data","data":{"titleno": "DN1"}}' -H "Content-Type: application/json" http://127.0.0.1:5001/insert
```

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
sudo -u postgres psql systemofrecord
```

describe tables with 

```
\d
```

To query, update, delete from a table use sql

```
select * from sor;
```



