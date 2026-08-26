import inspect
import re
import textwrap
from typing import TypedDict

from flask import Flask, render_template
from flask.typing import ResponseReturnValue
from neo4j.exceptions import Neo4jError, ResultConsumedError

from answers_store import load_answers
from db import get_driver
from tasks import TASKS, Task

app = Flask(__name__)
driver = get_driver()

EMPTY_QUERY_RE = re.compile(r"""tx\.run\(\s*["']\s*["']\s*\)""")


class TaskView(TypedDict):
    task: Task
    source: str
    attempted: bool
    done: bool
    message: str


def grade_answers() -> tuple[list[TaskView], int]:
    answers = load_answers()
    results: list[TaskView] = []
    done_count = 0

    for task in TASKS:
        fn = answers[task["id"]]
        source = textwrap.dedent(inspect.getsource(fn)).strip()

        if EMPTY_QUERY_RE.search(source):
            attempted, done, message = False, False, "Not attempted yet."
        else:
            try:
                attempted, done, message = task["checker"](driver, fn)
            except ResultConsumedError:
                attempted, done = True, False
                message = (
                    "Your function returned an unconsumed result — return "
                    "list(tx.run(...)) instead of tx.run(...) directly."
                )
            except Neo4jError as e:
                attempted, done, message = True, False, str(e.message)

        if done:
            done_count += 1
        results.append(
            {
                "task": task,
                "source": source,
                "attempted": attempted,
                "done": done,
                "message": message,
            }
        )

    return results, done_count


@app.route("/")
def index() -> ResponseReturnValue:
    with driver.session() as session:
        users = session.execute_read(
            lambda tx: [
                dict(r)
                for r in tx.run(
                    """
                    MATCH (p:Person)
                    RETURN p.name AS name,
                           [(p)-[:FRIENDS_WITH]->(f) | f.name] AS friends,
                           [(p)-[:MEMBER_OF]->(g) | g.name] AS groups
                    ORDER BY p.name
                    """
                )
            ]
        )
        groups = session.execute_read(
            lambda tx: [
                dict(r)
                for r in tx.run(
                    """
                    MATCH (g:Group)
                    RETURN g.name AS name, [(p:Person)-[:MEMBER_OF]->(g) | p.name] AS members
                    ORDER BY g.name
                    """
                )
            ]
        )
        friendships = session.execute_read(
            lambda tx: [
                dict(r)
                for r in tx.run(
                    """
                    MATCH (a:Person)-[r:FRIENDS_WITH]->(b:Person)
                    RETURN a.name AS person, b.name AS friend, toString(r.time_followed) AS since
                    ORDER BY r.time_followed DESC
                    """
                )
            ]
        )

    return render_template("index.html", users=users, groups=groups, friendships=friendships)


@app.route("/assignment")
def assignment() -> ResponseReturnValue:
    results, done_count = grade_answers()
    return render_template(
        "assignment.html",
        results=results,
        done_count=done_count,
        total=len(TASKS),
    )


if __name__ == "__main__":
    app.run(port=5050, debug=True)
