import os
import chromadb

CHROMA_PATH = "data/chroma_db"
os.makedirs(CHROMA_PATH, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(name="incident_history")

if collection.count() == 0:
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


def query_historical_memory(query: str) -> str:
    results = collection.query(query_texts=[query], n_results=1)
    if results.get('documents') and results['documents'][0]:
        return results['documents'][0][0]
    return "No historical precedent found. Rely on manifest baselines."