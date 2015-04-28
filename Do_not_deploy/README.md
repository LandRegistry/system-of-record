# system-of-record tester
Checks the system of record for an entry.  Should never be deployed to production.

Used by acceptance tests

##requirements:
- python 3
- python modules listed in requirements.txt

##How to use the virtual environment

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
python3 run_tester.py
```


##Examples curl commands

To find the number of rows on the system of record

```
curl http://0.0.0.0:5002/count
```

Get the data from the last record.

```
curl http://0.0.0.0:5002/getlastrecord
```

Delete the last record.

```
curl http://0.0.0.0:5002/deletelastrecord
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



