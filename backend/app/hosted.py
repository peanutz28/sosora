"""Explicit hosted-only entrypoint; app.main and local service settings stay unchanged."""
import os

# A public free-CPU replay must never fall through to a private live model service.
os.environ['DEMO_MODE'] = 'true'

from app.factory import create_app
from app.routing import load_anchors, load_graph

app = create_app(load_graph(), load_anchors(), '/tmp/sosora-hosted-demo.sqlite3')
