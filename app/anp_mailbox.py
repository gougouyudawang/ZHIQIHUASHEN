"""Durable group messages with immutable IDs and idempotent receipt storage."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException

class Mailbox:
    def __init__(self,path):self.path=Path(path)
    @contextmanager
    def db(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        c=sqlite3.connect(self.path,timeout=15);c.row_factory=sqlite3.Row
        try:
            with c:
                c.execute('CREATE TABLE IF NOT EXISTS messages (direction TEXT, sender TEXT, id TEXT, target TEXT, content TEXT, timestamp TEXT, status TEXT, receipt TEXT, PRIMARY KEY(direction,sender,id))')
                yield c
        finally:c.close()
    def reserve(self,direction,sender,mid,target,content):
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM messages WHERE direction=? AND sender=? AND id=?',(direction,sender,mid)).fetchone()
            if row:
                if row['target']!=target or row['content']!=content:raise HTTPException(409,'消息编号已被其他内容使用')
                return dict(row)
            stamp=datetime.now(timezone.utc).isoformat()
            c.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)',(direction,sender,mid,target,content,stamp,'pending',None))
            return dict(direction=direction,sender=sender,id=mid,target=target,content=content,timestamp=stamp,status='pending',receipt=None)
    def finish(self,direction,sender,mid,status,receipt=None):
        with self.db() as c:
            # A late failure cannot overwrite an acknowledged delivery.
            c.execute("UPDATE messages SET status=?,receipt=COALESCE(?,receipt) WHERE direction=? AND sender=? AND id=? AND status NOT IN ('delivered','received')",
                (status,json.dumps(receipt,ensure_ascii=False) if receipt else None,direction,sender,mid))
    def listing(self,direction):
        with self.db() as c:
            rows=c.execute('SELECT * FROM messages WHERE direction=? ORDER BY timestamp DESC LIMIT 50',(direction,)).fetchall()
        return [dict(message_id=r['id'],sender_did='local:'+r['sender'],target_id=r['target'],content=r['content'],timestamp=r['timestamp'],status=r['status']) for r in rows]
