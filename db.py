from neo4j import Driver, GraphDatabase

URI = "bolt://localhost:7688"
AUTH = ("neo4j", "demopassword")


def get_driver() -> Driver:
    return GraphDatabase.driver(URI, auth=AUTH)
