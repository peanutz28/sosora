from __future__ import annotations

import json
import sqlite3


class Store:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            "create table if not exists incidents (client_id text primary key, body text not null, created_at text not null)"
        )
        self.conn.execute("create table if not exists events (id integer primary key, body text not null)")
        self.conn.commit()

    def reset(self) -> None:
        self.conn.execute("delete from incidents")
        self.conn.execute("delete from events")
        self.conn.commit()

    def save_incident(self, incident: dict) -> None:
        self.conn.execute(
            "insert or replace into incidents (client_id, body, created_at) values (?, ?, ?)",
            (incident["client_id"], json.dumps(incident), incident["created_at"]),
        )
        self.conn.commit()

    def save_event(self, event: dict) -> None:
        self.conn.execute(
            "insert or replace into events (id, body) values (?, ?)",
            (event["id"], json.dumps(event)),
        )
        self.conn.commit()

    def counts(self) -> dict:
        incidents = self.conn.execute("select count(*) from incidents").fetchone()[0]
        events = self.conn.execute("select count(*) from events").fetchone()[0]
        return {"incidents": incidents, "events": events}
