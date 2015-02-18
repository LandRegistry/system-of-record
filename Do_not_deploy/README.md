# system-of-record tester
Checks the system of record for an entry.

Used by acceptance tests

##requirements:
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


##How to use


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



