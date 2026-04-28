from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kg_workbench.models import KGEdge, KGNode
from kg_workbench.utils import to_jsonable

try:
    import kuzu
except ImportError:  # pragma: no cover - optional dependency path
    kuzu = None


class KuzuGraphStore:
    def __init__(self, db_path: Path):
        if kuzu is None:
            raise ImportError("Kuzu is not installed. Install it with `pip install kuzu`.")
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = kuzu.Database(str(self.db_path))
        self.conn = kuzu.Connection(self.db)
        self._init_schema()

    def _init_schema(self) -> None:
        try:
            self.conn.execute(
                "CREATE NODE TABLE Entity(id STRING, name STRING, entity_type STRING, data STRING, PRIMARY KEY(id))"
            )
        except RuntimeError:
            pass
        try:
            self.conn.execute("CREATE REL TABLE Relation(FROM Entity TO Entity, id STRING, relation_type STRING, data STRING)")
        except RuntimeError:
            pass

    def clear(self) -> None:
        self.conn.execute("MATCH (n) DETACH DELETE n")

    def upsert_nodes(self, nodes: list[KGNode]) -> None:
        for node in nodes:
            data = json.dumps(to_jsonable(node), ensure_ascii=False)
            self.conn.execute(
                """
                MERGE (n:Entity {id: $id})
                ON MATCH SET n.name = $name, n.entity_type = $entity_type, n.data = $data
                ON CREATE SET n.name = $name, n.entity_type = $entity_type, n.data = $data
                """,
                {"id": node.id, "name": node.name, "entity_type": node.entity_type, "data": data},
            )

    def insert_edges(self, edges: list[KGEdge]) -> None:
        for edge in edges:
            data = json.dumps(to_jsonable(edge), ensure_ascii=False)
            self.conn.execute(
                """
                MATCH (a:Entity {id: $src}), (b:Entity {id: $tgt})
                CREATE (a)-[:Relation {id: $id, relation_type: $relation_type, data: $data}]->(b)
                """,
                {
                    "src": edge.src,
                    "tgt": edge.tgt,
                    "id": edge.id,
                    "relation_type": edge.relation_type,
                    "data": data,
                },
            )

    def persist(self, nodes: list[KGNode], edges: list[KGEdge]) -> dict[str, Any]:
        self.clear()
        self.upsert_nodes(nodes)
        self.insert_edges(edges)
        return self.stats()

    def stats(self) -> dict[str, int]:
        node_result = self.conn.execute("MATCH (n:Entity) RETURN count(n)")
        edge_result = self.conn.execute("MATCH ()-[e:Relation]->() RETURN count(e)")
        return {
            "stored_node_count": int(node_result.get_next()[0]),
            "stored_edge_count": int(edge_result.get_next()[0]),
        }

