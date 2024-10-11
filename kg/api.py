from flask import Flask, request, jsonify
from client import Neo4jClient

import neo4j

app = Flask(__name__)
client = Neo4jClient()


@app.route("/search", methods=["GET"])
def search():
    disease = request.json.get("disease")
    geolocation = request.json.get("geolocation")
    pathogen = request.json.get("pathogen")
    timestamp = request.json.get("timestamp")
    symptom = request.json.get("symptom")
    limit = request.json.get("limit")

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
