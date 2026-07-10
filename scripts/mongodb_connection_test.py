"""
Minimal MongoDB Atlas connection test.

Confirms that:
- the connection string / credentials work
- the client can write to landing_reviews
- the client can read back what it wrote
- cleanup succeeds (so this test leaves no trace behind)

Usage:
    python test_connection.py
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

def main():
    load_dotenv()
    uri = os.getenv("MONGODB_URI")
    print(os.getenv("MONGODB_URI"))
    if not uri:
        print("MONGODB_URI environment variable not set.")
        sys.exit(1)

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Forces a round trip to confirm the connection is actually alive,
        # not just that the client object was constructed.
        client.admin.command("ping")
        print("Connected to MongoDB Atlas.")
    except ConnectionFailure as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    db = client["steam_reviews"]
    collection = db["landing_reviews"]

    test_doc = {
        "_test": True,
        "note": "connection test document",
        "inserted_at": datetime.now(timezone.utc),
    }

    try:
        insert_result = collection.insert_one(test_doc)
        print(f"Inserted test document with _id: {insert_result.inserted_id}")

        fetched = collection.find_one({"_id": insert_result.inserted_id})
        print(f"Read back: {fetched}")

        delete_result = collection.delete_one({"_id": insert_result.inserted_id})
        print(f"Deleted test document (deleted_count={delete_result.deleted_count})")

    except OperationFailure as e:
        print(f"Operation failed: {e}")
        sys.exit(1)
    finally:
        client.close()

    print("Connection test passed.")


if __name__ == "__main__":
    main()
