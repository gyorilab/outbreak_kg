from flask import Blueprint, request, jsonify


auto_blueprint = Blueprint("autocomplete", __name__, url_prefix="/autocomplete")

@auto_blueprint.route("/geolocations", methods=["GET"])
def autocomplete_geolocations():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)
    from get_lookups import geoloc_trie
    return jsonify(
        geoloc_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/diseases", methods=["GET"])
def autocomplete_diseases():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)
    from get_lookups import disease_trie
    return jsonify(
        disease_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/pathogens", methods=["GET"])
def autocomplete_pathogens():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)
    from get_lookups import pathogen_trie
    return jsonify(
        pathogen_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/indicators", methods=["GET"])
def autocomplete_indicators():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)
    from get_lookups import indicator_trie
    return jsonify(
        indicator_trie.case_insensitive_search(prefix, top_n=top_n)
    )

@auto_blueprint.route("/alerts", methods=["GET"])
def autocomplete_alerts():
    """Get the autocomplete suggestions for a given prefix."""
    prefix = request.args.get("prefix")
    top_n = min(int(request.args.get("top_n", 100)), 100)
    from get_lookups import alert_trie
    return jsonify(
        alert_trie.case_insensitive_search(prefix, top_n=top_n)
    )
