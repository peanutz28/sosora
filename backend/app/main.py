from pathlib import Path

from app.factory import create_app
from app.routing import load_anchors, load_graph
from app.store import Store

ROOT = Path(__file__).resolve().parents[1]
app = create_app(load_graph(), load_anchors(), str(ROOT / "data" / "sosora.db"))

# Imported so the database class stays with the process entrypoint.
_ = Store
