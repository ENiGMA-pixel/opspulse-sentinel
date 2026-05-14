# Cell 2.5: Expanded ChromaDB Historical Memory (The Memory Bank)
import chromadb

# 1. Start up the memory engine
chroma_client = chromadb.Client()

# 2. Reset the collection for a clean slate
try:
    chroma_client.delete_collection(name="incident_history")
except Exception:
    pass
collection = chroma_client.create_collection(name="incident_history")

# 3. Populate with diverse historical incidents
collection.add(
    documents=[
        "Resolution: Reverted Ingress controller proxy-connect-timeout to baseline 30s after deployment caused 503s.",
        "Resolution: ServiceA OOMKilled due to memory leak in v1.1.0. Rolled back to v1.0.9.",
        "Resolution: Database lock timeout exceeded during massive batch insert on PostgreSQL-Main. Terminated idle transactions.",
        "Resolution: BGP routing flap caused transient 504 Gateway Timeouts. Reset peering session.",
        "Resolution: Auth-Service SSL certificate expiration caused silent connection drops. Rotated certs."
    ],
    ids=["inc_001", "inc_002", "inc_003", "inc_004", "inc_005"]
)

# 4. Search using an ambiguous query to prove semantic matching
results = collection.query(
    query_texts=["Helm upgrade reduced the proxy timeout causing service drops"],
    n_results=1
)

print(f"📚 Memory Bank populated with 5 incidents.")
print(f"🔍 Vector Search Test: Found top semantic match -> ID {results['ids'][0]}")