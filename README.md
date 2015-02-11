# system-of-record
At the moment this service posts data to a postgres database.

##requirements:
- postgres
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
./run.sh -d
```

##how to run tests
In virtual machine

```
./test.sh
```


##How to insert a row

```
curl -X POST -d '{"sig":"some_signed_data","data":{"titleno": "DN1"}}' -H "Content-Type: application/json" http://192.168.50.5:5000/insert
```

##How to check that the service is running:

```
curl http://192.168.50.5:5000/
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



