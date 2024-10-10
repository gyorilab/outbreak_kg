from typing import Any, List, Optional
from typing_extensions import TypeAlias

import neo4j
from neo4j import GraphDatabase, Transaction, unit_of_work

__all__ = ["client"]

TxResult: TypeAlias = Optional[List[List[Any]]]


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

    def query_graph(
        self,
        disease: str = None,
        geolocation: str = None,
        pathogen: str = None,
        timestamp: str = None,
        symptom: str = None,
    ):
        where_clauses = []
        search_query = "MATCH (n)-[:mentions]->(m)"
        query_parameters = {}
        return_value = ' RETURN n, '
        # TODO: add isa* relationships for all filters
        # TODO: symptoms: it's either mentioned just like a disease or a symptom of a disease which is mentioned
        # TODO: allow for a limit option
        if disease is not None:
            search_query += " MATCH (n)-[r_d:mentions]->(disease:disease {name: $disease})"
            query_parameters["disease"] = disease
            return_value += 'r_d, disease, '
        if geolocation is not None:
            search_query += " MATCH (n)-[r_g:mentions]->(geolocation:geolocation {name: $geolocation})"
            query_parameters["geolocation"] = geolocation
            return_value += 'r_g, geolocation, '
        if pathogen is not None:
            search_query += " MATCH (n)-[r_p:mentions]->(pathogen:pathogen {name: $pathogen})"
            query_parameters["pathogen"] = pathogen
            return_value += 'r_p, pathogen, '
        if timestamp is not None:
            where_clauses.append("n.timestamp = $timestamp")
            query_parameters["timestamp"] = timestamp
        if where_clauses:
            search_query += " WHERE " + " AND ".join(where_clauses)
        if symptom is not None:
            search_query += " OPTIONAL MATCH (disease:disease)-[r_ph:has_phenotype]->({symptom:disease {name: $symptom}})"
            query_parameters["symptom"] = symptom
        search_query += return_value

        return self.query_tx(search_query, **query_parameters)


@unit_of_work()
def do_cypher_tx(tx: Transaction, query: str, **query_params) -> List[List]:
    result = tx.run(query, parameters=query_params)
    return [record.values() for record in result]
