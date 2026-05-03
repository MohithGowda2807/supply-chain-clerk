"""
Neo4j Cypher Benchmark Queries
Run these in the Neo4j browser at http://localhost:7474

These are the 4 key queries for the paper's benchmark section.
Copy-paste each block into the Neo4j browser query editor.
"""

QUERIES = {
    "Q1_supplier_batches_30d": """
// Q1: All batches from a supplier in last 30 days
MATCH (s:Supplier {name:'Himalaya Herbs'})-[:SUPPLIED]->(b:Batch)
WHERE b.intake_timestamp > datetime() - duration('P30D')
RETURN b.batch_no, b.expiry_date, b.quantity, b.intake_timestamp
ORDER BY b.intake_timestamp DESC
    """,

    "Q2_expiring_within_30d": """
// Q2: All products expiring within 30 days
MATCH (b:Batch)-[:STORED_IN]->(bin:StorageBin)
WHERE b.expiry_date < date() + duration('P30D')
RETURN b.batch_no, b.product_name, b.expiry_date, bin.bin_code
ORDER BY b.expiry_date ASC
    """,

    "Q3_bin_history": """
// Q3: Full history of bin A01
MATCH (b:Batch)-[:STORED_IN]->(bin:StorageBin {bin_code:'A01'})
RETURN b.batch_no, b.product_name, b.expiry_date, b.intake_timestamp
ORDER BY b.intake_timestamp DESC
    """,

    "Q4_quarantine_impact": """
// Q4: All bins if supplier Himalaya Herbs is quarantined
MATCH (s:Supplier {name:'Himalaya Herbs'})-[:SUPPLIED]->(b:Batch)-[:STORED_IN]->(bin:StorageBin)
RETURN DISTINCT bin.bin_code, b.batch_no, b.expiry_date, b.product_name
ORDER BY bin.bin_code
    """,

    "Q5_supplier_graph": """
// Q5: Full supplier-product graph (for React Force Graph visualisation)
MATCH (s:Supplier)-[:SUPPLIED]->(b:Batch)-[:IS_A]->(p:Product)
RETURN s.name AS supplier, p.name AS product, COUNT(b) AS batch_count
ORDER BY batch_count DESC
    """,
}

if __name__ == "__main__":
    """
    Run all benchmark queries against a live Neo4j instance and print results.
    Usage: python tests/neo4j_benchmarks.py
    """
    import os, time
    from neo4j import GraphDatabase

    uri  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw   = os.getenv("NEO4J_PASSWORD", "smartguard123")

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    with driver.session() as session:
        for name, cql in QUERIES.items():
            t0 = time.perf_counter()
            result = session.run(cql)
            rows = result.data()
            ms = round((time.perf_counter() - t0) * 1000, 2)
            print(f"\n{'='*60}")
            print(f"[{name}]  {len(rows)} rows  {ms}ms")
            for r in rows[:5]:
                print(" ", dict(r))
    driver.close()
