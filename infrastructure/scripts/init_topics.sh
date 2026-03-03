#!/bin/bash
set -e

echo "Waiting for Redpanda to be ready..."
until docker exec rag-redpanda rpk cluster health > /dev/null 2>&1; do
    sleep 2
done

# Creates a topic only if it doesn't already exist.
# rpk has no --if-not-exists flag, so we check the topic list first.
create_topic() {
    local topic=$1
    local partitions=$2
    if docker exec rag-redpanda rpk topic list 2>/dev/null | grep -q "^${topic}"; then
        echo "  [skip] ${topic} already exists"
    else
        docker exec rag-redpanda rpk topic create "${topic}" --partitions "${partitions}" --replicas 1
        echo "  [created] ${topic}"
    fi
}

echo "Creating topics..."
create_topic "rag.ingest.requested" 3
create_topic "rag.ingest.completed" 3
create_topic "rag.ingest.failed"    3
create_topic "rag.ingest.dlq"       1

echo ""
echo "Topics ready:"
docker exec rag-redpanda rpk topic list
