# system-of-record
Beta version of the system of record

##requirements:
- postgres
- python 3
- python modules listed in requirements.txt

##How to run

Puppet will setup everything with vagrant up.  However tables will need 
to be created, so run

```
source ./environment.sh 
```

```
python3 manage.py db init
```

```
python3 manage.py db migrate
```

```
python3 manage.py db upgrade
```

Then type this to run the application

```
source ./run.sh
```

##How to insert a row

```
curl -X POST -d '{"titleno" : "DN1"}' -H "Content-Type: application/json" http://192.168.50.5:5000/insert
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



