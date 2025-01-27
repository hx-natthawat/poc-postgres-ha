#!/usr/bin/env python3
import psycopg2
import time
from datetime import datetime
import sys
import os

def create_connection(application_name=None):
    """Create a connection to PostgreSQL through pgpool."""
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'adminpassword',
        'database': 'customdatabase'
    }
    if application_name:
        conn_params['application_name'] = application_name
    
    return psycopg2.connect(**conn_params)

def test_write_operation():
    """Test write operation on master node."""
    print("\n=== Testing Write Operation (Master) ===")
    conn = create_connection()
    try:
        with conn.cursor() as cur:
            # Create test table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS test_replication (
                    id SERIAL PRIMARY KEY,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            # Insert test data
            test_data = f"Test data at {datetime.now()}"
            cur.execute("INSERT INTO test_replication (data) VALUES (%s) RETURNING id", (test_data,))
            inserted_id = cur.fetchone()[0]
            conn.commit()
            print(f"✅ Successfully wrote data with ID: {inserted_id}")
            return inserted_id
    except Exception as e:
        print(f"❌ Write operation failed: {e}")
        raise
    finally:
        conn.close()

def test_read_operation(last_inserted_id):
    """Test read operation on replica node."""
    print("\n=== Testing Read Operation (Replica) ===")
    conn = create_connection(application_name='readonly')
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM test_replication WHERE id = %s", (last_inserted_id,))
            result = cur.fetchone()
            if result:
                print(f"✅ Successfully read data from replica: {result[0]}")
            else:
                print("❌ Data not found in replica")
    except Exception as e:
        print(f"❌ Read operation failed: {e}")
    finally:
        conn.close()

def test_read_write_separation():
    """Test if write operations fail on replica."""
    print("\n=== Testing Read-Write Separation ===")
    conn = create_connection(application_name='readonly')
    try:
        with conn.cursor() as cur:
            # First verify we can read
            cur.execute("SELECT 1")
            print("✅ Read operation successful on replica")
            
            # Set transaction to read-only explicitly
            cur.execute("SET TRANSACTION READ ONLY")
            
            # Now try to write (should fail)
            try:
                # Try an INSERT operation
                cur.execute("INSERT INTO test_replication (data) VALUES ('This should fail')")
                conn.commit()
                print("❌ Write operation succeeded on replica (unexpected)")
            except psycopg2.Error as e:
                if "cannot execute INSERT in a read-only transaction" in str(e) or \
                   "cannot execute INSERT in a read-only mode" in str(e) or \
                   "cannot execute INSERT on a replica" in str(e):
                    print("✅ Write operation correctly failed on replica (expected error)")
                else:
                    print(f"❌ Unexpected error: {e}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        conn.close()

def test_failover():
    """Test failover by monitoring continuous reads and verify system restoration."""
    print("\n=== Testing Failover Capability ===")
    print("Start failing over the master node manually...")
    print("This script will continuously try to read data...")
    
    connection_success = False
    consecutive_successes = 0
    required_successes = 3  # Number of successful consecutive reads to consider system stable
    
    for i in range(60):  # Monitor for 60 seconds
        try:
            conn = create_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM test_replication")
                count = cur.fetchone()[0]
                print(f"✅ Read successful at {datetime.now()}: {count} records")
                consecutive_successes += 1
                if consecutive_successes >= required_successes:
                    connection_success = True
                    break
            conn.close()
        except Exception as e:
            print(f"❌ Read failed at {datetime.now()}: {e}")
            consecutive_successes = 0
        time.sleep(1)
    
    if connection_success:
        print("\n=== Testing Post-Failover System State ===")
        
        # Test 1: Write new data
        try:
            new_id = test_write_operation()
            print("✅ Post-failover write operation successful")
        except Exception as e:
            print(f"❌ Post-failover write operation failed: {e}")
            return
        
        # Wait for replication
        time.sleep(2)
        
        # Test 2: Read from replica
        try:
            test_read_operation(new_id)
            print("✅ Post-failover read operation successful")
        except Exception as e:
            print(f"❌ Post-failover read operation failed: {e}")
            return
            
        # Test 3: Verify read-write separation still works
        try:
            test_read_write_separation()
            print("✅ Post-failover read-write separation verified")
        except Exception as e:
            print(f"❌ Post-failover read-write separation test failed: {e}")
            return
            
        print("\n✅ System fully restored after failover!")
    else:
        print("\n❌ System did not stabilize after failover within the timeout period")

def main():
    print("=== PostgreSQL Master-Replica Test Script ===")
    
    try:
        # Test 1: Write Operation
        last_inserted_id = test_write_operation()
        
        # Wait for replication
        time.sleep(2)
        
        # Test 2: Read Operation
        test_read_operation(last_inserted_id)
        
        # Test 3: Read-Write Separation
        test_read_write_separation()
        
        # Test 4: Failover
        response = input("\nDo you want to test failover? (yes/no): ")
        if response.lower() == 'yes':
            test_failover()
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
