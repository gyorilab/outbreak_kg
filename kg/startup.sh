#!/bin/bash

set -eoxu pipefail

echo "Starting database"
neo4j start

echo "Waiting for database"
until [ \
  "$(curl -s -w '%{http_code}' -o /dev/null "http://localhost:7474")" \
  -eq 200 ]
do
  sleep 5
done

neo4j status

cd /sw/outbreak_kg/kg
# start the service
gunicorn --bind 0.0.0.0:8771 api:app
