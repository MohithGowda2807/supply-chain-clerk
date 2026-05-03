"""
Bin Assignment Service

Pure-Cypher FEFO bin assignment — no Python-side filtering.

Algorithm (single parameterised query):
  1. Filter bins in the correct zone for the product category.
  2. Exclude full bins (current_occupancy >= capacity).
  3. FEFO: prefer bins already holding the same product with earliest expiry.
  4. Fallback: lowest current_occupancy.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from neo4j import AsyncGraphDatabase

log = logging.getLogger(__name__)

_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
_USER = os.getenv("NEO4J_USER", "neo4j")
_PASS = os.getenv("NEO4J_PASSWORD", "smartguard123")


async def assign_bin(product_category: str, product_name: str) -> Optional[str]:
    """
    Return the bin_code for the optimal storage bin, or None if no bin
    is available in the required zone.
    """
    driver = AsyncGraphDatabase.driver(_URI, auth=(_USER, _PASS))
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (bin:StorageBin {zone: $zone})
            WHERE bin.current_occupancy < bin.capacity
            OPTIONAL MATCH (existing:Batch)-[:STORED_IN]->(bin)
            WHERE existing.product_name = $product_name
            WITH bin,
                 min(existing.expiry_date) AS earliest_expiry,
                 bin.current_occupancy AS occ
            RETURN bin.bin_code AS bin_code
            ORDER BY
                earliest_expiry ASC NULLS LAST,
                occ ASC
            LIMIT 1
            """,
            zone=product_category,
            product_name=product_name,
        )
        record = await result.single()
    await driver.close()

    return record["bin_code"] if record else None


async def write_intake_event(
    batch_no: str,
    product_name: str,
    supplier_name: str,
    expiry_date: Optional[str],
    quantity: Optional[int],
    unit_of_measure: str,
    bin_code: str,
    confidence: float,
) -> str:
    """
    Write the intake event to Neo4j:
      Supplier -[:SUPPLIED]-> Batch -[:STORED_IN]-> StorageBin
      Batch -[:IS_A]-> Product

    Returns the Batch node's elementId for use as intake_id.
    """
    driver = AsyncGraphDatabase.driver(_URI, auth=(_USER, _PASS))
    async with driver.session() as session:
        result = await session.run(
            """
            MERGE (s:Supplier {name: $supplier_name})
            ON CREATE SET s.id = 'S-AUTO-' + toString(id(s)), s.active = true

            MERGE (p:Product {name: $product_name})
            ON CREATE SET p.id = 'P-AUTO-' + toString(id(p)),
                          p.category = 'unknown', p.unit = $unit_of_measure

            CREATE (b:Batch {
                batch_no:        $batch_no,
                product_name:    $product_name,
                expiry_date:     $expiry_date,
                quantity:        $quantity,
                unit_of_measure: $unit_of_measure,
                confidence:      $confidence,
                intake_timestamp: datetime()
            })

            MERGE (bin:StorageBin {bin_code: $bin_code})

            CREATE (s)-[:SUPPLIED]->(b)
            CREATE (b)-[:IS_A]->(p)
            CREATE (b)-[:STORED_IN]->(bin)

            SET bin.current_occupancy = bin.current_occupancy + 1

            RETURN elementId(b) AS intake_id
            """,
            batch_no=batch_no,
            product_name=product_name,
            supplier_name=supplier_name,
            expiry_date=expiry_date,
            quantity=quantity,
            unit_of_measure=unit_of_measure,
            bin_code=bin_code,
            confidence=confidence,
        )
        record = await result.single()
    await driver.close()

    return record["intake_id"]
