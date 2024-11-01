import json
from typing import Any, List, Optional
from typing_extensions import TypeAlias

import gilda
import neo4j
from neo4j import GraphDatabase, Transaction, unit_of_work

__all__ = ["Neo4jClient"]

from kg.test import create_custom_grounder

TxResult: TypeAlias = Optional[List[List[Any]]]

customer_grounder = create_custom_grounder()

class Neo4jClient:
    """A client to Neo4j."""

    _session: Optional[neo4j.Session]

    def __init__(
        self,
    ) -> None:
        """Initialize the Neo4j client."""
        # We initialize this so that the del doesn't error if some
        # exception occurs before it's initialized
        self.driver = None
        url = "bolt://localhost:7687"
        user = None
        password = None

        # Set max_connection_lifetime to something smaller than the timeouts
        # on the server or on the way to the server. See
        # https://github.com/neo4j/neo4j-python-driver/issues/316#issuecomment-564020680
        self.driver = GraphDatabase.driver(
            url,
            auth=(user, password) if user and password else None,
            max_connection_lifetime=3 * 60,
        )
        self._session = None

    def __del__(self):
        if self.driver is not None:
            self.driver.close()

    def query_tx(self, query: str, **query_params) -> Optional[TxResult]:
        with self.driver.session() as session:
            values = session.read_transaction(do_cypher_tx, query, **query_params)
        return values

    def query_indicators(
        self,
        geolocation: str,
        indicator_filter: str,
    ):
        geolocation_curie = get_curie(geolocation)
        query = \
            """
            MATCH (i:indicator)<-[r:has_indicator]-(geolocation:geoloc)-
            [:isa*0..]->(geolocation_isa:geoloc {curie: $geolocation_curie})
            WHERE i.name CONTAINS $indicator_filter
            RETURN i, r, geolocation, geolocation_isa
            """
        query_parameters = {
            "geolocation_curie": geolocation_curie,
            "indicator_filter": indicator_filter
        }
        res = self.query_tx(query, **query_parameters)
        data = [
            {
                'indicator': dict(row[0]),
                'data': json.loads(dict(row[1])['years_data']),
                'geolocation': dict(row[2]),
                'geolocation_isa': dict(row[3]),
            }
            for row in res
        ]
        return data

    def query_graph(
        self,
        disease: str = None,
        geolocation: str = None,
        pathogen: str = None,
        timestamp: str = None,
        symptom: str = None,
        limit: int = None
    ):
        search_query = "MATCH (n:alert)-[:mentions]->(m)"
        query_parameters = {}
        return_value = " RETURN DISTINCT n, n.timestamp"
        result_elements = []
        if timestamp is not None:
            search_query += " WHERE n.timestamp = $timestamp"
            query_parameters["timestamp"] = timestamp
        if disease is not None:
            disease_curie = get_curie(disease)
            if disease_curie is None:
                return []
            search_query += (
                " MATCH (n:alert)-[r_d:mentions]->(disease:disease)-"
                "[:isa*0..]->(disease_isa:disease {curie: $disease_curie})"
            )
            query_parameters["disease_curie"] = disease
            return_value += ", disease, disease_isa"
            result_elements.append('disease')
        if geolocation is not None:
            geolocation_curie = get_curie(geolocation)
            if geolocation_curie is None:
                return []
            search_query += (
                " MATCH (n:alert)-[r_g:mentions]->(geolocation:geoloc)-"
                "[:isa*0..]->(geolocation_isa:geoloc {curie: $geolocation_curie})"
            )
            query_parameters["geolocation_curie"] = geolocation
            return_value += ", geolocation, geolocation_isa"
            result_elements.append('geoloc')
        if pathogen is not None:
            pathogen_curie = get_curie(pathogen)
            if pathogen_curie is None:
                return []
            search_query += (
                " MATCH (n:alert)-[r_p:mentions]->(pathogen:pathogen)-"
                "[:isa*0..]->(pathogen_isa:pathogen {curie: $pathogen_curie})"
            )
            query_parameters["pathogen_curie"] = pathogen
            return_value += ", pathogen, pathogen_isa"
            result_elements.append('pathogen')
        if symptom is not None:
            symptom_curie = get_curie(symptom)
            if symptom_curie is None:
                return []
            search_query += (
                " MATCH (n)-[r_s:mentions]->(symptom:disease)-"
                "[:has_phenotype|isa*0..]->(symptom_isa:disease {curie:$symptom_curie})"
            )
            query_parameters["symptom_curie"] = symptom
            return_value += ", symptom, symptom_isa"
            result_elements.append('symptom')
        search_query += return_value
        if limit:
            search_query += f" LIMIT {limit}"
        res = self.query_tx(search_query, **query_parameters)
        all_data = []
        for row in res:
            alert = dict(row[0])
            alert['timestamp'] = row[1]
            data = {'alert': alert}
            for idx, element in enumerate(result_elements):
                # First element is the given entity, the next is any isa entity
                i = idx * 2 + 2
                data[element] = dict(row[i])
                data[element + '_isa'] = dict(row[i + 1])
            all_data.append(data)
        return all_data

    def annotate_text_query(self, text: str):
        annotations = gilda.annotate(text, namespaces=['MESH', 'geonames'])
        curies = [
            f'{a.matches[0].term.db}:{a.matches[0].term.id}'
            for a in annotations
        ]
        print('Looking up CURIEs:', ', '.join(sorted(curies)))
        # Query for direct relationships between the terms
        # TODO: we should add an entity tag to all of the
        # domain-specific terms to make these queries scale
        query = """
            MATCH (a:entity)-[r]->(b:entity)
            WHERE a.curie IN $curies AND b.curie IN $curies
            RETURN a, r, b
        """
        res_direct = self.query_tx(query, entities=curies)
        data = {'direct': []}
        for res in res_direct:
            a, r, b = res
            entry = {
                'a': dict(a),
                'b': dict(b),
                'r': dict(r)
            }
            data['direct'].append(entry)
        # Query for alerts in which these co-occur in any pairs
        query = """
            MATCH (n:alert)-[:mentions]->(a)
            MATCH (n:alert)-[:mentions]->(b)
            WHERE a.curie IN $curies AND b.curie IN $curies
            AND a <> b
            RETURN n, a, b
        """
        res_alerts = self.query_tx(query, curies=curies)
        data['alerts'] = []
        for res in res_alerts:
            alert = dict(res[0])
            entities = [dict(res[1]), dict(res[2])]
            data['alerts'].append({'alert': alert, 'entities': entities})
        return data


@unit_of_work()
def do_cypher_tx(tx: Transaction, query: str, **query_params) -> List[List]:
    result = tx.run(query, parameters=query_params)
    return [record.values() for record in result]


def create_custom_grounder():
    """Returns a custom grounder for geonames and MeSH terms"""
    from gilda.generate_terms import generate_mesh_terms
    from gilda import Term
    from gilda.process import (
        normalize,
        replace_dashes,
        replace_greek_uni,
        replace_greek_latin,
        replace_greek_spelled_out,
        replace_roman_arabic,
    )
    import pandas as pd

    mesh_gilda_terms = generate_mesh_terms(ignore_mappings=True)
    geoname_node_df = pd.read_csv("geoname_nodes.tsv", sep="\t")
    geoname_gilda_terms = []
    for _, geoname_info in geoname_node_df.iterrows():
        name = geoname_info["name:string"]
        curie_elements = geoname_info["curie:ID"].split(":")
        db_name = curie_elements[0]
        db_id = curie_elements[1]
        norm_name = replace_dashes(name, " ")
        norm_name = replace_greek_uni(norm_name)
        norm_name = replace_greek_latin(norm_name)
        norm_name = replace_greek_spelled_out(norm_name)
        norm_name = replace_roman_arabic(norm_name)
        norm_name = normalize(norm_name)
        geoname_gilda_term = Term(
            norm_text=norm_name,
            text=name,
            db=db_name,
            id=db_id,
            entry_name=name,
            status="name",
            source=db_name,
        )
        geoname_gilda_terms.append(geoname_gilda_term)
    custom_grounder_terms = geoname_gilda_terms + mesh_gilda_terms
    custom_grounder = gilda.grounder.Grounder(custom_grounder_terms)
    return custom_grounder


def get_curie(name):
    """Return a MeSH CURIE based on a text name."""
    matches = customer_grounder.ground(name, namespaces=['MESH'])
    if not matches:
        return None
    curie = f'MESH:{matches[0].term.id}'
    return curie