from typing import List, Dict, Set

def bfs_connected_nodes(graph: Dict[str, List[str]], start_node: str, valid_nodes: Set[str] = None) -> Set[str]:
    """
    Finds all nodes connected to start_node.
    If valid_nodes is provided, it only traverses through nodes present in valid_nodes.
    This is useful for finding all cities connected by a specific company's track.
    """
    if valid_nodes is not None and start_node not in valid_nodes:
        return set()

    visited = set()
    queue = [start_node]

    while queue:
        current = queue.pop(0)
        if current not in visited:
            visited.add(current)
            for neighbor in graph.get(current, []):
                if valid_nodes is None or neighbor in valid_nodes:
                    if neighbor not in visited:
                        queue.append(neighbor)

    return visited

def calculate_route_value(connected_nodes: Set[str], node_values: Dict[str, int]) -> int:
    """
    Given a set of connected nodes, calculates the total dividend/revenue value.
    """
    return sum(node_values.get(node, 0) for node in connected_nodes)
