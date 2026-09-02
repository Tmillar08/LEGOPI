from __future__ import annotations

from .config import DEMO_CATALOG_DB, DEMO_INVENTORY_DB, REAL_CATALOG_DB, REAL_INVENTORY_DB
from .mode import enabled


def inventory_db_path():
    return DEMO_INVENTORY_DB if enabled() else REAL_INVENTORY_DB


def catalog_db_path():
    return DEMO_CATALOG_DB if enabled() else REAL_CATALOG_DB
