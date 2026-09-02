from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def lookup_part(path: Path, part_num: str, color: str | None = None):
    con = connect(path)
    try:
        exact = []
        if color and color != "unknown":
            exact = con.execute(
                """
                SELECT i.part_name, i.color_name, i.quantity, i.location_id, l.spoken_location
                FROM inventory i JOIN locations l ON l.location_id=i.location_id
                WHERE lower(i.rebrickable_part_num)=lower(?) AND lower(i.color_name)=lower(?)
                ORDER BY i.quantity DESC
                """,
                (part_num, color),
            ).fetchall()
        if exact:
            return "exact", exact[0]
        rows = con.execute(
            """
            SELECT i.part_name, i.color_name, i.quantity, i.location_id, l.spoken_location
            FROM inventory i JOIN locations l ON l.location_id=i.location_id
            WHERE lower(i.rebrickable_part_num)=lower(?)
            ORDER BY i.quantity DESC
            """,
            (part_num,),
        ).fetchall()
        return "part", rows[0] if rows else None
    finally:
        con.close()


def add_part(path: Path, part_num: str, part_name: str, color: str) -> dict:
    con = connect(path)
    try:
        exact = con.execute(
            """
            SELECT i.inventory_id, i.quantity, i.location_id, l.spoken_location
            FROM inventory i JOIN locations l ON l.location_id=i.location_id
            WHERE lower(i.rebrickable_part_num)=lower(?) AND lower(i.color_name)=lower(?)
            ORDER BY i.quantity DESC LIMIT 1
            """,
            (part_num, color),
        ).fetchone()

        if exact:
            new_qty = int(exact["quantity"]) + 1
            con.execute(
                "UPDATE inventory SET quantity=?, last_verified=datetime('now') WHERE inventory_id=?",
                (new_qty, exact["inventory_id"]),
            )
            location_id = exact["location_id"]
            spoken = exact["spoken_location"] or location_id
            action = "ADD_EXISTING"
        else:
            same_part = con.execute(
                """
                SELECT i.location_id, l.spoken_location
                FROM inventory i JOIN locations l ON l.location_id=i.location_id
                WHERE lower(i.rebrickable_part_num)=lower(?)
                ORDER BY i.quantity DESC LIMIT 1
                """,
                (part_num,),
            ).fetchone()
            if same_part:
                location_id = same_part["location_id"]
                spoken = same_part["spoken_location"] or location_id
                action = "ADD_NEW_COLOR"
            else:
                location = con.execute(
                    """
                    SELECT l.location_id, l.spoken_location
                    FROM locations l
                    WHERE NOT EXISTS (SELECT 1 FROM inventory i WHERE i.location_id=l.location_id)
                    ORDER BY l.unit,l.drawer,l.y_row,l.x_column LIMIT 1
                    """
                ).fetchone()
                if not location:
                    raise RuntimeError("No unused storage locations available")
                location_id = location["location_id"]
                spoken = location["spoken_location"] or location_id
                action = "ADD_NEW_PART"

            con.execute(
                """
                INSERT INTO inventory(
                    rebrickable_part_num,part_name,color_id,color_name,quantity,location_id,
                    rebrickable_set_num,last_verified,notes
                ) VALUES(?,?,NULL,?,1,?,NULL,datetime('now'),'Added by Jarvis scan')
                """,
                (part_num, part_name, color, location_id),
            )
            new_qty = 1

        con.execute(
            """
            INSERT INTO inventory_history(
                timestamp,action,rebrickable_part_num,color_name,quantity_change,
                old_location_id,new_location_id,source,spoken_command,notes
            ) VALUES(datetime('now'),?,?,?,1,NULL,?,'voice','add this brick',?)
            """,
            (action, part_num, color, location_id, part_name),
        )
        con.commit()
        return {
            "action": action,
            "quantity": new_qty,
            "location_id": location_id,
            "spoken_location": spoken,
        }
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
