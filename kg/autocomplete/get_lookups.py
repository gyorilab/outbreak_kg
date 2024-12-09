import csv
import gzip

import pandas as pd
from matplotlib.style.core import available

from kg.autocomplete.nodes_trie import NodesTrie, NodeData, TrieIndex, CappedTrie
from kg.api import client

def init_nodes_name(node_mapping: NodeData) -> TrieIndex:
    """Generate a case-insensitive trie index for node names and synonyms

    Parameters
    ----------
    node_mapping :
        A dictionary of node data, where the key is the curie and the value is a
        dictionary containing the node data. The dictionary should contain the keys
        "curie" and "name", it may optionally contain "definition" and "synonyms".
        If synonyms are present, they will be added to the trie with the same data as
        the name.

    Returns
    -------
    :
        A dictionary containing the trie index to initialize a NodesTrie instance
    """
    name_indexing = {}

    for curie, node_dict in node_mapping.items():
        # Get node name in lowercase
        node_name = node_dict["name"].lower()
        # Get node data (first item is the name match)
        node_data = (
            node_dict["name"],
            node_dict["name"],
            curie,
            node_dict.get("definition", ""),
        )
        # Check if the node name is already present in the trie. This could happen if
        # the case-insensitive version of the name is the same as another
        # node's name e.g., from a different namespace
        if node_name in name_indexing:
            ix = 1
            node_name_ = f"{node_name}_{ix}"

            # Increase index until no key is present
            while node_name_ in name_indexing:
                ix += 1
                node_name_ = f"{node_name}_{ix}"
        name_indexing[node_name] = node_data

        # If we have synonyms, add them to the trie with the same data
        if node_dict.get("synonyms"):
            for syn_name in node_dict["synonyms"]:
                # Set the first item of the node data to the synonym
                node_data = (syn_name, *node_data[1:])
                syn = syn_name.lower()
                if syn in name_indexing:
                    ix = 1
                    syn_ = f"{syn}_{ix}"
                    while syn_ in name_indexing:
                        ix += 1
                        syn_ = syn + f"_{ix}"
                    syn = syn_
                name_indexing[syn] = node_data

    return name_indexing


def get_node_by_label_autocomplete(label:str) -> NodesTrie:
    query = f"""\
            MATCH (n:{label})
            RETURN DISTINCT n.curie, n"""
    nodes = client.read_dict(query)
    node_data = {curie: dict(node) for curie, node in nodes.items()}
    node_mapping = init_nodes_name(node_data)
    return NodesTrie(**node_mapping)




