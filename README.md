# system-of-record
Beta version of the system of record

##requirements:
- postgres
- python 3
- python modules listed in requirements.txt

##How to run

```
source ./run.sh
```

##How to insert a row

```
curl -X POST -d '{"titleno" : "DN1"}' -H "Content-Type: application/json" http://0.0.0.0:5000/insert
```

##How to update the database, if necessary

```
python3 manage.py db upgrade
```



