from flask import Blueprint, request, jsonify

from kg.autocomplete.get_lookups import (
    get_node_by_label_autocomplete
)

auto_blueprint = Blueprint("autocomplete", __name__, url_prefix="/autocomplete")

# Get the autocomplete tries for each node type
geoloc_trie = get_node_by_label_autocomplete("geoloc")
disease_trie = get_node_by_label_autocomplete("disease")
pathogen_trie = get_node_by_label_autocomplete("pathogen")
indicator_trie = get_node_by_label_autocomplete("indicator")
alert_trie = get_node_by_label_autocomplete("alert")


@auto_blueprint.route("/geolocations", methods=["GET"])
def autocomplete_search():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)

    return jsonify(
        geoloc_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/diseases", methods=["GET"])
def autocomplete_search():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)

    return jsonify(
        disease_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/pathogens", methods=["GET"])
def autocomplete_search():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)

    return jsonify(
        pathogen_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/indicators", methods=["GET"])
def autocomplete_search():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)

    return jsonify(
        indicator_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/alerts", methods=["GET"])
def autocomplete_search():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)

    return jsonify(
        alert_trie.case_insensitive_search(prefix, top_n=top_n)
    )
