#!/bin/bash

# Create backup directories if they don't exist
mkdir -p backups/pg-0
mkdir -p backups/pg-1

# Get current timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup pg-0 (primary)
echo "Backing up primary node (pg-0)..."
docker exec poc-01-pg-0-1 pg_dumpall -U postgres > backups/pg-0/full_backup_${TIMESTAMP}.sql
if [ $? -eq 0 ]; then
    echo "Primary backup completed successfully"
else
    echo "Primary backup failed"
fi

# Backup pg-1 (replica)
echo "Backing up replica node (pg-1)..."
docker exec poc-01-pg-1-1 pg_dumpall -U postgres > backups/pg-1/full_backup_${TIMESTAMP}.sql
if [ $? -eq 0 ]; then
    echo "Replica backup completed successfully"
else
    echo "Replica backup failed"
fi

# Compress backups
echo "Compressing backups..."
cd backups/pg-0 && tar czf full_backup_${TIMESTAMP}.tar.gz full_backup_${TIMESTAMP}.sql && rm full_backup_${TIMESTAMP}.sql
cd ../pg-1 && tar czf full_backup_${TIMESTAMP}.tar.gz full_backup_${TIMESTAMP}.sql && rm full_backup_${TIMESTAMP}.sql

echo "Backup completed at ${TIMESTAMP}"
