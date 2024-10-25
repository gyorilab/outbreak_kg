from flask import Flask, request, jsonify
from client import Neo4jClient

import neo4j

app = Flask(__name__)
client = Neo4jClient()


@app.route("/v1/node", methods=["GET"])
def search():
    disease = request.args.get("disease")
    geolocation = request.args.get("geolocation")
    pathogen = request.args.get("pathogen")
    timestamp = request.args.get("timestamp")
    symptom = request.args.get("symptom")
    limit = request.args.get("limit")

    search_results = client.query_graph(
        disease, geolocation, pathogen, timestamp, symptom, limit
    )
    return_value = {}
    for path_index, path in enumerate(search_results):
        return_value[path_index] = []
        for path_compartment in path:
            if isinstance(path_compartment, neo4j.graph.Node):
                dict_path_compartment = dict(path_compartment)
                return_value[path_index].append(dict_path_compartment)
            elif path_compartment is not None:
                return_value[path_index].append(path_compartment.type)

    return jsonify(return_value)


@app.route("/v1/healthcheck", methods=["GET"])
def healthcheck():
    return "OK", 200
