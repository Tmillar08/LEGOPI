from __future__ import annotations

import sqlite3
from pathlib import Path

from .db_paths import catalog_db_path


def connect(path: Path | None = None):
    con = sqlite3.connect(path or catalog_db_path(), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def owned_sets(path: Path | None = None):
    con = connect(path)
    try:
        return con.execute(
            """
            SELECT u.set_num, s.name FROM user_owned_sets u
            LEFT JOIN sets s ON s.set_num=u.set_num ORDER BY u.set_num
            """
        ).fetchall()
    finally:
        con.close()


def resolve_set(set_name: str | None, path: Path | None = None) -> str | None:
    if not set_name:
        return None
    wanted = set_name.strip().lower()
    rows = owned_sets(path)
    exact = [r for r in rows if (r[1] or "").lower() == wanted]
    if len(exact) == 1:
        return exact[0][0]
    partial = [r for r in rows if wanted in (r[1] or "").lower() or (r[1] or "").lower() in wanted]
    return partial[0][0] if len(partial) == 1 else None


def start_session(set_num: str) -> tuple[bool, str]:
    con = connect()
    try:
        owned = con.execute(
            """
            SELECT u.set_num,s.name,s.num_parts FROM user_owned_sets u
            JOIN sets s ON s.set_num=u.set_num WHERE u.set_num=?
            """, (set_num,)
        ).fetchone()
        if not owned:
            return False, f"Set {set_num} is not in your owned set library."

        inv = con.execute(
            "SELECT id,version FROM inventories WHERE set_num=? ORDER BY CAST(version AS INTEGER) DESC,id DESC LIMIT 1",
            (set_num,),
        ).fetchone()
        if not inv:
            return False, f"I found set {set_num}, but I do not have its parts inventory."

        con.execute("UPDATE build_sessions SET status='inactive' WHERE status='active'")
        cur = con.execute(
            "INSERT INTO build_sessions(set_num,set_name,status) VALUES(?,?,'active')",
            (owned["set_num"], owned["name"]),
        )
        session_id = cur.lastrowid
        rows = con.execute(
            """
            SELECT ip.part_num,ip.color_id,c.name color_name,SUM(CAST(ip.quantity AS INTEGER)) required_qty
            FROM inventory_parts ip LEFT JOIN colors c ON c.id=ip.color_id
            WHERE ip.inventory_id=? AND COALESCE(ip.is_spare,0)=0
            GROUP BY ip.part_num,ip.color_id,c.name
            """, (inv["id"],),
        ).fetchall()
        con.executemany(
            """
            INSERT INTO build_required_parts(session_id,part_num,color_id,color_name,required_qty,found_qty)
            VALUES(?,?,?,?,?,0)
            """,
            [(session_id,r["part_num"],r["color_id"],r["color_name"],r["required_qty"]) for r in rows],
        )
        con.commit()
        total = sum(int(r["required_qty"]) for r in rows)
        return True, f"{owned['name']} is now the active rebuild set. I loaded its parts inventory."
    finally:
        con.close()


def active_set() -> str | None:
    con = connect()
    try:
        row = con.execute(
            "SELECT set_num,set_name FROM build_sessions WHERE status='active' ORDER BY session_id DESC LIMIT 1"
        ).fetchone()
        return row["set_name"] if row else None
    finally:
        con.close()
