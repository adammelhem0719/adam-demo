from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import networkx as nx
from .config import Edge

@dataclass(frozen=True)
class PropagationGraph:
    graph: nx.DiGraph

def build_graph(edges: List[Edge]) -> PropagationGraph:
    g = nx.DiGraph()
    for e in edges:
        g.add_edge(e.src, e.dst, delay_days=int(e.delay_days), amplification=float(e.amplification))
    return PropagationGraph(graph=g)

def edge_list(pg: PropagationGraph) -> List[Dict]:
    out = []
    for u, v, d in pg.graph.edges(data=True):
        out.append({"src": u, "dst": v, "delay_days": d["delay_days"], "amplification": d["amplification"]})
    return out
