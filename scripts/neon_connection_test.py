import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("NEON_URI")

def test_connection():
    conn = None
    try:
        print("Connecting to Neon Postgres...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("Connected.")

        # Create temp test table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS connection_test (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            )
        """)
        conn.commit()
        print("Test table created.")

        # Insert a row
        now = datetime.now(timezone.utc)
        cur.execute(
            "INSERT INTO connection_test (message, created_at) VALUES (%s, %s) RETURNING id",
            ("hello from steam-review-analysis", now)
        )
        # Pylance doesn't know fetchone() will return a row at runtime, so it flags the subscripts as potentially None, the code will run fine
        inserted_id = cur.fetchone()[0] # type: ignore 

        conn.commit()
        print(f"Inserted row with id={inserted_id}.")

        # Read it back
        cur.execute("SELECT id, message, created_at FROM connection_test WHERE id = %s", (inserted_id,))
        row = cur.fetchone()
        # Pylance doesn't know fetchone() will return a row at runtime, so it flags the subscripts as potentially None, the code will run fine
        print(f"Read back: id={row[0]}, message='{row[1]}', created_at={row[2]}") # type: ignore
        

        # Clean up
        cur.execute("DROP TABLE connection_test")
        conn.commit()
        print("Test table dropped. All clean.")

        print("\nPostgres connection test passed.")

    except Exception as e:
        print(f"Connection test failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_connection()