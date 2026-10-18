"""Uvicorn factory for a rehearsal that cannot reset the filming database."""
from pathlib import Path
from tempfile import mkdtemp
from app.factory import create_app
from app.routing import load_anchors, load_graph


def create():
    database = Path(mkdtemp(prefix='sosora-rehearsal-')) / 'state.db'
    return create_app(load_graph(), load_anchors(), str(database))
