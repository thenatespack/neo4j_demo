import importlib

import answers as _answers_module
from tasks import AnswerFn


def load_answers() -> dict[str, AnswerFn]:
    """Re-read answers.py from disk so edits show up without restarting the app."""
    importlib.reload(_answers_module)
    return _answers_module.ANSWERS
