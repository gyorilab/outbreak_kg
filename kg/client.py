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
        included_labels = []
        included_names = []
        where_clauses = []
        search_query = "MATCH (n)-[r_m:mentions]->(m)"
        query_parameters = {}
        if timestamp is not None:
            query_parameters["timestamp"] = timestamp
            where_clauses.append("n.timestamp = $timestamp")
        if disease is not None:
            included_labels.append("disease")
            included_names.append(disease)
        if geolocation is not None:
            included_labels.append("geoloc")
            included_names.append(geolocation)
        if pathogen is not None:
            included_labels.append("pathogen")
            included_names.append(pathogen)
        if included_labels and included_names:
            query_parameters["labels"] = included_labels
            query_parameters["names"] = included_names
            where_clauses.append(
                "m.name IN $names AND ANY(label IN labels(m) WHERE label IN $labels)")
        if where_clauses:
            search_query += " WHERE " + " AND ".join(where_clauses)
        if symptom is not None:
            query_parameters["symptom"] = symptom
            search_query += " OPTIONAL MATCH (m)-[r_ph:has_phenotype]->(ph)"
            search_query += " WHERE ph.name = $symptom"
        search_query += " RETURN n, r_m, m, r_ph, ph"

        return self.query_tx(search_query, **query_parameters)


@unit_of_work()
def do_cypher_tx(tx: Transaction, query: str, **query_params) -> List[List]:
    result = tx.run(query, parameters=query_params)
    return [record.values() for record in result]


client = Neo4jClient()
