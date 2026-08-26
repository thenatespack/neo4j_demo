"""Assignment task definitions and the checkers that grade them.

Each task is implemented by the student as a Neo4j transaction function (the
same `tx.run(...)` pattern used in main.py) living in answers.py. We call that
function ourselves via `session.execute_read`, then compare what it returned
against a reference query to decide whether the task is complete.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any, TypedDict

from neo4j import Driver, Record, Transaction
from neo4j.graph import Node, Path, Relationship

AnswerFn = Callable[[Transaction], "list[Record] | None"]

# (attempted, done, message)
CheckResult = tuple[bool, bool, str]
Checker = Callable[[Driver, AnswerFn], CheckResult]


class Task(TypedDict):
    id: str
    title: str
    prompt: str
    checker: Checker


def normalize_value(value: Any) -> Any:
    if isinstance(value, Node):
        return ("NODE", value.element_id)
    if isinstance(value, Relationship):
        return ("REL", value.element_id)
    if isinstance(value, Path):
        return (
            "PATH",
            tuple(n.element_id for n in value.nodes),
            tuple(r.element_id for r in value.relationships),
        )
    if isinstance(value, list):
        return tuple(sorted((normalize_value(v) for v in value), key=repr))
    if isinstance(value, dict):
        return tuple(sorted((k, normalize_value(v)) for k, v in value.items()))
    if type(value).__module__.startswith("neo4j.time"):
        return str(value)
    return value


def record_tuple(record: Record) -> tuple[Any, ...]:
    return tuple(normalize_value(v) for v in record.values())


def run_query(driver: Driver, query: str) -> list[Record]:
    with driver.session() as session:
        return session.execute_read(lambda tx: list(tx.run(query)))


def run_student(driver: Driver, fn: AnswerFn) -> list[Record] | None:
    """Call the student's transaction function and return what it gave back.

    Raises `ResultConsumedError` if the student returned an unconsumed
    `Result` instead of materializing it (e.g. with `list(...)`) before the
    transaction closed.
    """
    with driver.session() as session:
        return session.execute_read(fn)


def collect_node_ids(records: Sequence[Record]) -> set[str]:
    ids: set[str] = set()
    for record in records:
        for value in record.values():
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, Node):
                    ids.add(item.element_id)
    return ids


def check_view_graph(driver: Driver, fn: AnswerFn) -> CheckResult:
    student = run_student(driver, fn)
    if student is None:
        return False, False, "Not attempted yet."

    reference = run_query(driver, "MATCH (n) RETURN elementId(n) AS id")
    reference_ids = {r["id"] for r in reference}
    student_ids = collect_node_ids(student)

    if student_ids == reference_ids:
        return True, True, f"Your query returned all {len(reference_ids)} nodes in the graph."

    missing = len(reference_ids - student_ids)
    extra = len(student_ids - reference_ids)
    parts = []
    if missing:
        parts.append(f"missing {missing} node(s)")
    if extra:
        parts.append(f"{extra} unexpected node(s)")
    return True, False, "Not quite — your query returned " + " and ".join(parts) + "."


def check_ordered(reference_query: str) -> Checker:
    def checker(driver: Driver, fn: AnswerFn) -> CheckResult:
        student_records = run_student(driver, fn)
        if student_records is None:
            return False, False, "Not attempted yet."

        student = [record_tuple(r) for r in student_records]
        reference = [record_tuple(r) for r in run_query(driver, reference_query)]
        if student == reference:
            return True, True, f"Correct — {len(reference)} row(s) in the right order."
        if Counter(student) == Counter(reference):
            return True, False, "Close! You have the right rows, but not in the right order."
        return (
            True,
            False,
            (
                f"Expected {len(reference)} row(s) matching the reference query; "
                "that's not what your function returned."
            ),
        )

    return checker


def check_unordered(reference_query: str) -> Checker:
    def checker(driver: Driver, fn: AnswerFn) -> CheckResult:
        student_records = run_student(driver, fn)
        if student_records is None:
            return False, False, "Not attempted yet."

        student = Counter(record_tuple(r) for r in student_records)
        reference = Counter(record_tuple(r) for r in run_query(driver, reference_query))
        if student == reference:
            return True, True, f"Correct — {sum(reference.values())} row(s) matched."
        return (
            True,
            False,
            (
                f"Expected {sum(reference.values())} row(s) matching the reference query; "
                "that's not what your function returned."
            ),
        )

    return checker


def check_shortest_path(driver: Driver, fn: AnswerFn) -> CheckResult:
    student_records = run_student(driver, fn)
    if student_records is None:
        return False, False, "Not attempted yet."

    reference = run_query(
        driver,
        "MATCH p = shortestPath("
        '(a:Person {name: "Alice"})-[:FRIENDS_WITH*]-(b:Person {name: "Dave"})'
        ") RETURN length(p) AS len",
    )
    expected_len = reference[0]["len"] if reference else None

    paths = [v for r in student_records for v in r.values() if isinstance(v, Path)]
    if not paths:
        return True, False, "Your function didn't return a path."

    path = paths[0]
    endpoints = {path.start_node.get("name"), path.end_node.get("name")}
    if endpoints != {"Alice", "Dave"}:
        return True, False, "Your path doesn't run between Alice and Dave."
    if any(r.type != "FRIENDS_WITH" for r in path.relationships):
        return True, False, "Your path uses a relationship type other than FRIENDS_WITH."
    if len(path.relationships) != expected_len:
        hops = len(path.relationships)
        return True, False, f"Your path has {hops} hop(s); the shortest path has {expected_len}."

    return (
        True,
        True,
        f"Correct — a shortest path with {expected_len} hop(s) between Alice and Dave.",
    )


TASKS: list[Task] = [
    {
        "id": "view_graph",
        "title": "View the whole graph",
        "prompt": "Return every node in the graph.",
        "checker": check_view_graph,
    },
    {
        "id": "friendships_since",
        "title": "Friendships and when they started",
        "prompt": (
            "Return each friendship as (person name, friend's name, time_followed), "
            "ordered by time_followed."
        ),
        "checker": check_ordered(
            "MATCH (a:Person)-[r:FRIENDS_WITH]->(b:Person) "
            "RETURN a.name, b.name, r.time_followed ORDER BY r.time_followed"
        ),
    },
    {
        "id": "groups_per_person",
        "title": "Group memberships per person",
        "prompt": "Return each person's name along with a list of the groups they belong to.",
        "checker": check_unordered(
            "MATCH (p:Person)-[:MEMBER_OF]->(g:Group) RETURN p.name, collect(g.name) AS groups"
        ),
    },
    {
        "id": "friends_of_friends",
        "title": "Friends of friends",
        "prompt": (
            "Return pairs of (person, friend-of-friend) for people who are two hops "
            "apart but not already direct friends."
        ),
        "checker": check_unordered(
            "MATCH (a:Person)-[:FRIENDS_WITH]->(:Person)-[:FRIENDS_WITH]->(fof:Person) "
            "WHERE a <> fof AND NOT (a)-[:FRIENDS_WITH]->(fof) "
            "RETURN DISTINCT a.name, fof.name"
        ),
    },
    {
        "id": "shortest_path",
        "title": "Shortest path between two people",
        "prompt": "Return the shortest FRIENDS_WITH path between Alice and Dave.",
        "checker": check_shortest_path,
    },
]

TASKS_BY_ID: dict[str, Task] = {t["id"]: t for t in TASKS}
