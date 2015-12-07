#!/bin/bash
for i in {1..10000}
do
   pt1="{ \"sig\" : \"some_signed_data\" , \"data\" : {\"title_number\": \"DN$i\", \"application_reference\":$i }}"
   #echo $pt1
   curl -X POST -d "$pt1" -H "Content-Type: application/json" http://127.0.0.1:5001/insert
done