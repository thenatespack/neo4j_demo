"""Fill in each function below to complete the assignment tasks.

Each function is a Neo4j transaction function — the same pattern used for the
seed functions in main.py. Fill in the Cypher query inside `tx.run("")` for
each task, e.g.:

    def view_graph(tx: Transaction) -> list[Record] | None:
        return list(tx.run("MATCH (n) RETURN n"))

Leave the query as `tx.run("")` if you haven't attempted a task yet.
Save this file and reload http://localhost:5050/assignment to get graded.
"""

from neo4j import Record, Transaction


def view_graph(tx: Transaction) -> list[Record] | None:
    """Return every node in the graph."""
    return list(tx.run(""))


def friendships_since(tx: Transaction) -> list[Record] | None:
    """Return each friendship as (person, friend, time_followed), ordered by time_followed."""
    return list(tx.run(""))


def groups_per_person(tx: Transaction) -> list[Record] | None:
    """Return each person's name along with the groups they belong to."""
    return list(tx.run(""))


def friends_of_friends(tx: Transaction) -> list[Record] | None:
    """Return (person, friend-of-friend) pairs for people two hops apart, not already friends."""
    return list(tx.run(""))


def shortest_path(tx: Transaction) -> list[Record] | None:
    """Return the shortest FRIENDS_WITH path between Alice and Dave."""
    return list(tx.run(""))


ANSWERS = {
    "view_graph": view_graph,
    "friendships_since": friendships_since,
    "groups_per_person": groups_per_person,
    "friends_of_friends": friends_of_friends,
    "shortest_path": shortest_path,
}
