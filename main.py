from datetime import date

from neo4j import Transaction

from db import get_driver

PEOPLE = ["Alice", "Bob", "Carol", "Dave", "Erin", "Frank", "Grace"]

GROUPS = ["Book Club", "Hiking Crew", "Chess Club"]

MEMBERSHIPS: list[tuple[str, str]] = [
    ("Alice", "Book Club"),
    ("Bob", "Book Club"),
    ("Carol", "Book Club"),
    ("Bob", "Hiking Crew"),
    ("Dave", "Hiking Crew"),
    ("Erin", "Hiking Crew"),
    ("Frank", "Chess Club"),
    ("Grace", "Chess Club"),
    ("Alice", "Chess Club"),
]

# (person, friend, time_followed)
FRIENDSHIPS: list[tuple[str, str, date]] = [
    ("Alice", "Bob", date(2019, 3, 14)),
    ("Alice", "Carol", date(2020, 6, 1)),
    ("Bob", "Dave", date(2021, 1, 20)),
    ("Bob", "Erin", date(2018, 11, 5)),
    ("Carol", "Frank", date(2022, 4, 9)),
    ("Dave", "Grace", date(2017, 8, 30)),
    ("Erin", "Frank", date(2023, 2, 14)),
    ("Frank", "Grace", date(2019, 9, 23)),
    ("Grace", "Alice", date(2021, 12, 25)),
]


def reset(tx: Transaction) -> None:
    tx.run("MATCH (n) DETACH DELETE n")


def add_constraints(tx: Transaction) -> None:
    tx.run("CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE")
    tx.run("CREATE CONSTRAINT group_name IF NOT EXISTS FOR (g:Group) REQUIRE g.name IS UNIQUE")


def add_people(tx: Transaction, names: list[str]) -> None:
    tx.run(
        "UNWIND $names AS name MERGE (:Person {name: name})",
        names=names,
    )


def add_groups(tx: Transaction, names: list[str]) -> None:
    tx.run(
        "UNWIND $names AS name MERGE (:Group {name: name})",
        names=names,
    )


def add_memberships(tx: Transaction, memberships: list[tuple[str, str]]) -> None:
    tx.run(
        """
        UNWIND $memberships AS m
        MATCH (p:Person {name: m[0]})
        MATCH (g:Group {name: m[1]})
        MERGE (p)-[:MEMBER_OF]->(g)
        """,
        memberships=memberships,
    )


def add_friendships(tx: Transaction, friendships: list[tuple[str, str, date]]) -> None:
    tx.run(
        """
        UNWIND $friendships AS f
        MATCH (a:Person {name: f[0]})
        MATCH (b:Person {name: f[1]})
        MERGE (a)-[r:FRIENDS_WITH]->(b)
        SET r.time_followed = date(f[2])
        """,
        friendships=[(a, b, d.isoformat()) for a, b, d in friendships],
    )


def main() -> None:
    with get_driver() as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            session.execute_write(reset)
            session.execute_write(add_constraints)
            session.execute_write(add_people, PEOPLE)
            session.execute_write(add_groups, GROUPS)
            session.execute_write(add_memberships, MEMBERSHIPS)
            session.execute_write(add_friendships, FRIENDSHIPS)

    print("Seeded the social network graph.")
    print("Run `uv run app.py` and open http://localhost:5050 for the site,")
    print("or explore directly in Neo4j Browser at http://localhost:7475.")


if __name__ == "__main__":
    main()
