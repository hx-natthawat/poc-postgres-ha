# PostgreSQL High Availability POC

This proof of concept demonstrates a highly available PostgreSQL cluster setup using PostgreSQL, repmgr for replication management, and pgpool-II for connection pooling and load balancing.

## Architecture

The setup consists of:

1. **PostgreSQL Nodes**:

   - `pg-0`: Primary PostgreSQL server (port 32776)
   - `pg-1`: Replica PostgreSQL server (port 32777)
   - Both nodes use repmgr for automatic failover

2. **Connection Pooling**:
   - `pgpool`: Manages connections, load balancing, and read-write splitting (port 5432)

## Features

- Automatic failover using repmgr
- Read-write splitting (master for writes, replica for reads)
- Connection pooling with pgpool
- Load balancing for read queries
- Automatic backup archiving
- Health monitoring

## Directory Structure

```
poc-01/
├── app/                    # Application directory
│   └── Dockerfile         # Application Dockerfile
├── backups/               # Backup directory
│   ├── pg-0/             # Primary node backups
│   └── pg-1/             # Replica node backups
├── docker-compose.yml     # Container orchestration
├── test_postgres_cluster.py  # Test suite
├── .env.example          # Template for environment variables
└── requirements.txt       # Python dependencies
```

## Configuration Details

### Environment Variables

The application uses environment variables for configuration. Copy `.env.example` to `.env` and configure the following variables:

```
POSTGRES_USER      # Database user (default: customuser)
POSTGRES_PASSWORD  # Database password (required)
POSTGRES_HOST      # Database host (default: pgpool)
POSTGRES_PORT      # Database port (default: 5432)
POSTGRES_DB        # Database name (default: customdatabase)
```

### PostgreSQL Configuration

- Database: Configured via environment variables
- Users: Configured via environment variables
- Replication:
  - Streaming replication enabled
  - Automatic failover configured
  - Archive mode enabled
- Security:
  - Credentials stored in environment variables
  - No hardcoded passwords in code
  - `.env` files excluded from version control

### Pgpool-II Configuration

- Load Balancing:
  - Enabled for read queries
  - Write queries routed to primary
  - Statement-level load balancing
- Connection Settings:
  - Port: 5432
  - Max Pool: 10 connections
  - Health check enabled
- Read-Write Separation:
  - Based on application_name='readonly'
  - Write operations blocked on replica

## Getting Started

1. Start the cluster:

   ```bash
   docker-compose up -d
   ```

2. Install test dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the test suite:
   ```bash
   python test_postgres_cluster.py
   ```

## Testing Scenarios

The test suite (`test_postgres_cluster.py`) verifies:

1. **Write Operations**

   - Creates test table
   - Inserts test data
   - Verifies write success

2. **Read Operations**

   - Reads from replica
   - Verifies replication
   - Tests load balancing

3. **Read-Write Separation**

   - Confirms reads work on replica
   - Verifies writes are blocked on replica
   - Tests transaction isolation

4. **Failover Testing**
   - Monitors continuous reads
   - Tests system during failover
   - Verifies system recovery
   - Validates post-failover functionality

## Failover Process

1. Start failover test in script
2. Stop primary node:
   ```bash
   docker stop poc-01-pg-0-1
   ```
3. Observe automatic failover
4. Verify system recovery

## Monitoring

- Health checks run every 10 seconds
- Failover is logged in PostgreSQL logs
- pgpool logs show connection routing

## Backup and Recovery

Backups are automatically archived to:

- Primary: `./backups/pg-0/`
- Replica: `./backups/pg-1/`

## Security Notes

- TLS is disabled for this POC
- Default passwords are used (change in production)
- Network is isolated using Docker network

## Production Considerations

1. Enable TLS for all connections
2. Use secure passwords
3. Implement proper backup strategy
4. Add monitoring and alerting
5. Configure proper resource limits
6. Use persistent volumes for data
7. Implement proper security measures

## Troubleshooting

1. View logs:

   ```bash
   docker-compose logs -f [service_name]
   ```

2. Check node status:

   ```bash
   docker exec -it poc-01-pg-0-1 repmgr node status
   ```

3. Common issues:
   - Connection refused: Check if services are running
   - Replication lag: Monitor with pgpool logs
   - Failover issues: Check repmgr logs
