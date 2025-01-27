#!/bin/bash

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/pg-0/full_backup_20250127_120000.tar.gz"
    exit 1
fi

BACKUP_FILE=$1

# Extract backup file
echo "Extracting backup file..."
BACKUP_DIR=$(dirname "$BACKUP_FILE")
cd "$BACKUP_DIR"
tar xzf $(basename "$BACKUP_FILE")
SQL_FILE=$(basename "$BACKUP_FILE" .tar.gz).sql

# Stop the containers but keep volumes
echo "Stopping containers..."
docker-compose down

# Start only the primary database
echo "Starting primary database..."
docker-compose up -d pg-0
sleep 10

# Restore the backup to primary
echo "Restoring backup to primary node..."
cat "$SQL_FILE" | docker exec -i poc-01-pg-0-1 psql -U postgres
if [ $? -eq 0 ]; then
    echo "Primary restore completed successfully"
else
    echo "Primary restore failed"
    exit 1
fi

# Start the remaining services
echo "Starting remaining services..."
docker-compose up -d

# Clean up
rm "$SQL_FILE"

echo "Restore completed. Waiting for services to be ready..."
sleep 30

# Verify the cluster status
echo "Checking cluster status..."
docker exec poc-01-pg-0-1 psql -U postgres -c "SELECT application_name, state, sync_state FROM pg_stat_replication;"
