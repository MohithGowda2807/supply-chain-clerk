"""
Neo4j Schema Initialisation

Idempotent — safe to call on every startup.
Creates constraints and seed data for the demo.
"""
from __future__ import annotations

import logging
import os

from neo4j import AsyncGraphDatabase

log = logging.getLogger(__name__)

_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
_USER = os.getenv("NEO4J_USER", "neo4j")
_PASS = os.getenv("NEO4J_PASSWORD", "smartguard123")


async def init_neo4j_schema() -> None:
    """Run constraints + seed data. Idempotent."""
    driver = AsyncGraphDatabase.driver(_URI, auth=(_USER, _PASS))
    async with driver.session() as session:
        # ── Constraints ───────────────────────────────────────────────────────
        constraints = [
            "CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT product_id  IF NOT EXISTS FOR (p:Product)  REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT batch_no    IF NOT EXISTS FOR (b:Batch)    REQUIRE b.batch_no IS UNIQUE",
            "CREATE CONSTRAINT bin_code    IF NOT EXISTS FOR (bin:StorageBin) REQUIRE bin.bin_code IS UNIQUE",
        ]
        for cql in constraints:
            await session.run(cql)

        # ── Composite index for expiry monitoring ─────────────────────────────
        await session.run(
            "CREATE INDEX batch_expiry IF NOT EXISTS FOR (b:Batch) ON (b.expiry_date, b.product_id)"
        )

        # ── Seed Suppliers ────────────────────────────────────────────────────
        suppliers = [
            {"id": "S001", "name": "Himalaya Herbs",  "region": "Karnataka",   "active": True},
            {"id": "S002", "name": "Dabur Pharma",    "region": "Delhi",       "active": True},
            {"id": "S003", "name": "Patanjali",       "region": "Uttarakhand", "active": True},
            {"id": "S004", "name": "Sun Pharma",      "region": "Mumbai",      "active": True},
            {"id": "S005", "name": "Cipla Ltd",       "region": "Goa",         "active": True},
        ]
        for s in suppliers:
            await session.run(
                "MERGE (s:Supplier {id:$id}) SET s.name=$name, s.region=$region, s.active=$active",
                **s,
            )

        # ── Seed Products ─────────────────────────────────────────────────────
        products = [
            {"id": "P001", "name": "Ashwagandha Extract",  "category": "herbal",     "unit": "units"},
            {"id": "P002", "name": "Paracetamol 500mg",    "category": "analgesic",  "unit": "strips"},
            {"id": "P003", "name": "Vitamin C 1000mg",     "category": "supplement", "unit": "bottles"},
            {"id": "P004", "name": "Turmeric Extract",     "category": "herbal",     "unit": "units"},
            {"id": "P005", "name": "Ibuprofen 400mg",      "category": "analgesic",  "unit": "strips"},
            {"id": "P006", "name": "Omega-3 Fish Oil",     "category": "supplement", "unit": "bottles"},
            {"id": "P007", "name": "Tulsi Drops",          "category": "herbal",     "unit": "units"},
            {"id": "P008", "name": "Aspirin 75mg",         "category": "analgesic",  "unit": "strips"},
            {"id": "P009", "name": "Multivitamin Complex", "category": "supplement", "unit": "bottles"},
            {"id": "P010", "name": "Neem Capsules",        "category": "herbal",     "unit": "units"},
        ]
        for p in products:
            await session.run(
                "MERGE (p:Product {id:$id}) SET p.name=$name, p.category=$category, p.unit=$unit",
                **p,
            )

        # ── Seed Storage Bins (20 bins across 3 zones) ────────────────────────
        bins = [
            # Herbal zone (A)
            {"bin_code": "A01", "zone": "herbal",     "capacity": 50,  "current_occupancy": 0, "led_index": 0},
            {"bin_code": "A02", "zone": "herbal",     "capacity": 50,  "current_occupancy": 0, "led_index": 1},
            {"bin_code": "A03", "zone": "herbal",     "capacity": 50,  "current_occupancy": 0, "led_index": 2},
            {"bin_code": "A04", "zone": "herbal",     "capacity": 50,  "current_occupancy": 0, "led_index": 3},
            {"bin_code": "A05", "zone": "herbal",     "capacity": 50,  "current_occupancy": 0, "led_index": 4},
            {"bin_code": "A06", "zone": "herbal",     "capacity": 50,  "current_occupancy": 0, "led_index": 5},
            {"bin_code": "A07", "zone": "herbal",     "capacity": 50,  "current_occupancy": 0, "led_index": 6},
            # Analgesic zone (B)
            {"bin_code": "B01", "zone": "analgesic",  "capacity": 100, "current_occupancy": 0, "led_index": 7},
            {"bin_code": "B02", "zone": "analgesic",  "capacity": 100, "current_occupancy": 0, "led_index": 8},
            {"bin_code": "B03", "zone": "analgesic",  "capacity": 100, "current_occupancy": 0, "led_index": 9},
            {"bin_code": "B04", "zone": "analgesic",  "capacity": 100, "current_occupancy": 0, "led_index": 10},
            {"bin_code": "B05", "zone": "analgesic",  "capacity": 100, "current_occupancy": 0, "led_index": 11},
            {"bin_code": "B06", "zone": "analgesic",  "capacity": 100, "current_occupancy": 0, "led_index": 12},
            # Supplement zone (C)
            {"bin_code": "C01", "zone": "supplement", "capacity": 75,  "current_occupancy": 0, "led_index": 13},
            {"bin_code": "C02", "zone": "supplement", "capacity": 75,  "current_occupancy": 0, "led_index": 14},
            {"bin_code": "C03", "zone": "supplement", "capacity": 75,  "current_occupancy": 0, "led_index": 15},
            {"bin_code": "C04", "zone": "supplement", "capacity": 75,  "current_occupancy": 0, "led_index": 16},
            {"bin_code": "C05", "zone": "supplement", "capacity": 75,  "current_occupancy": 0, "led_index": 17},
            {"bin_code": "C06", "zone": "supplement", "capacity": 75,  "current_occupancy": 0, "led_index": 18},
            {"bin_code": "C07", "zone": "supplement", "capacity": 75,  "current_occupancy": 0, "led_index": 19},
        ]
        for b in bins:
            await session.run(
                "MERGE (bin:StorageBin {bin_code:$bin_code}) "
                "SET bin.zone=$zone, bin.capacity=$capacity, "
                "bin.current_occupancy=$current_occupancy, bin.led_index=$led_index",
                **b,
            )

    await driver.close()
    log.info("Neo4j schema initialised and seed data loaded.")
