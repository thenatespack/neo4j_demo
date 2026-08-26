# Neo4j Demo: Social Network

A small teaching demo for Neo4j. It models a social network with:

- **Person** nodes — property `name`
- **Group** nodes — property `name`
- **`FRIENDS_WITH`** relationships between people — property `time_followed` (the date one person started following/being friends with the other)
- **`MEMBER_OF`** relationships from a person to a group

## Why this uses different ports

This demo runs Neo4j in Docker on **non-default ports**, because students following
along may already have a Neo4j instance (e.g. Neo4j Desktop) running on the standard
ports (`7474`/`7473`/`7687`). Using different ports here avoids port conflicts with
whatever else is already running:

| Service      | Default port | This demo's port |
|--------------|--------------|-------------------|
| HTTP (Browser) | 7474       | **7475**          |
| HTTPS          | 7473       | **7476**          |
| Bolt           | 7687       | **7688**          |

## Prerequisites

- [Docker](https://www.docker.com/) (for running Neo4j)
- [uv](https://docs.astral.sh/uv/) (for running the Python seed script and website)

## 1. Start Neo4j

```bash
docker run -d --name neo4j-demo -p 7475:7474 -p 7476:7473 -p 7688:7687 -e NEO4J_AUTH=neo4j/demopassword -v neo4j_demo_data:/data neo4j:5
```

This starts Neo4j with:
- user: `neo4j`
- password: `demopassword`

Once it's up, open the Neo4j Browser at **http://localhost:7475** and log in with
the credentials above (make sure the connect URL in the browser uses `bolt://localhost:7688`).

## 2. Seed the graph

```bash
uv run main.py
```

This clears the database and loads a small sample social network: several people,
a few groups, friendships (each with a `time_followed` date), and group memberships.

## 3. Run the website

```bash
uv run app.py
```

Open **http://localhost:5050** in your browser. The site has two pages:

- **Admin** (`/`) — an admin-panel view of the social network: user counts and
  stats, a users table (with each person's friends and groups), a groups table
  (with members), and a friend-activity table — all queried live from the database.
- **Assignment** (`/assignment`) — a checklist of tasks implemented as Neo4j
  transaction functions in **`answers.py`** — the same `tx.run(...)` pattern used
  by the seed functions in `main.py`:

  ```python
  def view_graph(tx: Transaction) -> list[Record] | None:
      return list(tx.run("MATCH (n) RETURN n"))
  ```

  Fill in the body of each function, save the file, then reload the assignment
  page. Each function is called for you and its return value is compared
  read-only against the expected result — the page itself is read-only and
  just shows the graded outcome (including the source of what you wrote).

The assignment tasks are the same exercises as below:

```cypher
// 1. View the whole graph
MATCH (n) RETURN n

// 2. Friendships and when they started
MATCH (a:Person)-[r:FRIENDS_WITH]->(b:Person)
RETURN a.name, b.name, r.time_followed
ORDER BY r.time_followed

// 3. Group memberships per person
MATCH (p:Person)-[:MEMBER_OF]->(g:Group)
RETURN p.name, collect(g.name) AS groups

// 4. Friends of friends (2 hops) who aren't already direct friends
MATCH (a:Person)-[:FRIENDS_WITH]->(:Person)-[:FRIENDS_WITH]->(fof:Person)
WHERE a <> fof AND NOT (a)-[:FRIENDS_WITH]->(fof)
RETURN DISTINCT a.name, fof.name

// 5. Shortest path between two people
MATCH p = shortestPath((a:Person {name: "Alice"})-[:FRIENDS_WITH*]-(b:Person {name: "Grace"}))
RETURN p
```

You can also run these directly in the Neo4j Browser (http://localhost:7475) if
you just want to explore without the assignment tracker.

## Stopping / resetting

```bash
docker stop neo4j-demo                      # stop Neo4j
docker rm neo4j-demo                        # remove the container
docker volume rm neo4j_demo_data            # also delete all data
```

To reset assignment progress, just clear the strings back out in `answers.py`.
