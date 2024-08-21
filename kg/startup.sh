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

echo "Keeping the container running by monitoring docker neo4j logs"
tail -f /var/log/neo4j/neo4j.log
