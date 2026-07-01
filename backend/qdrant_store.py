import os
import sys
import json
from typing import List
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_mistralai import MistralAIEmbeddings

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import using absolute path
from backend.config import POLICY_TEXT

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "policy_collection"
EMBEDDING_MODEL = "mistral-embed"

class QdrantRetriever:
    def __init__(self):
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.embeddings = MistralAIEmbeddings(model=EMBEDDING_MODEL)
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == COLLECTION_NAME for c in collections):
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE)
                )
                self._seed_policy()
        except Exception as e:
            print(f"Error connecting to Qdrant: {e}")
            print("Make sure Qdrant is running: docker-compose up -d")
            sys.exit(1)

    def _seed_policy(self):
        chunks = [p.strip() for p in POLICY_TEXT.split("\n\n") if p.strip()]
        points = []
        for idx, chunk in enumerate(chunks):
            embedding = self.embeddings.embed_query(chunk)
            points.append(
                models.PointStruct(
                    id=idx,
                    vector=embedding,
                    payload={"text": chunk}
                )
            )
        self.client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"✅ Seeded {len(points)} policy chunks into Qdrant.")

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        embedding = self.embeddings.embed_query(query)
        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            limit=top_k
        )
        return [hit.payload["text"] for hit in results]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="Seed Qdrant with policy")
    args = parser.parse_args()
    if args.seed:
        retriever = QdrantRetriever()
        print("✅ Seeding done.")