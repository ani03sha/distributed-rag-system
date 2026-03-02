#!/bin/bash
# Creates the Qdrant collection for nomic-embed-text (768 dimensions)
# Run once before first ingestion

curl -X PUT http://localhost:6333/collections/documents \
    -H "Content-Type: application/json" \
    -d '{
      "vectors": {
        "dense": {
          "size": 768,
          "distance": "Cosine"
        }
      },
      "optimizers_config": {
        "indexing_threshold": 1000
      },
      "hnsw_config": {
        "m": 16,
        "ef_construct": 100
      }
    }'

echo ""
echo "Collection created. Verify:"
curl http://localhost:6333/collections/documents | python3 -m json.tool
