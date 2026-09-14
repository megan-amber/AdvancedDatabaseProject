'''
Name: Megan Gerth
Date: 9/14/2026
Assignment: 2.3 Lab Project
Purpose: To showcase CRUD operations in a MongoDB 
         database utilizing Sample.json.
'''

import sys
import os
import json
import pymongo
from pymongo import MongoClient

DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(DIR, "Sample.json")

DB_NAME = "git_database"
COLLECTION_NAME = "commits"


def connect_mongodb():
    """Connect to local MongoDB server and return collection object."""
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        # Force a server call to verify connection
        client.admin.command('ping')
        db = client[DB_NAME]
        return db[COLLECTION_NAME]
    except pymongo.errors.ConnectionFailure:
        print("Error: Could not connect to MongoDB server. Ensure MongoDB service is running.")
        sys.exit(1)


def seed_mongodb_from_file(collection):
    """Seed MongoDB collection using array items inside Sample.json."""
    if not os.path.exists(JSON_FILE):
        print(f"Error: File '{JSON_FILE}' does not exist.")
        return

    print("\n--- Seeding MongoDB Database from Sample.json ---")
    try:
        with open(JSON_FILE, 'r', encoding='utf-8-sig') as f:
            records = json.load(f)

        if not isinstance(records, list):
            records = [records]

        # Insert records if collection is empty
        if collection.count_documents({}) == 0:
            if records:
                collection.insert_many(records)
                print(f"Loaded {len(records)} records into MongoDB collection '{COLLECTION_NAME}'.")
        else:
            print(f"Collection '{COLLECTION_NAME}' already contains data. Skipping initial seed.")

        print("--- Database Seeding Complete ---\n")

    except json.JSONDecodeError as e:
        print(f"Failed: Invalid JSON syntax in Sample.json ({e})")
    except Exception as e:
        print(f"Failed to seed MongoDB: {e}")


def sync_mongodb_to_file(collection):
    """Save all documents from MongoDB collection back to Sample.json."""
    documents = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB's internal _id field

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=4, ensure_ascii=False)


# --- REPORT GENERATION ---

def generate_author_report(collection):
    """Generate and print a formatted summary using MongoDB Aggregation."""
    if collection.count_documents({}) == 0:
        print("\nNo records found in MongoDB database.")
        return

    # Use MongoDB Aggregation Pipeline to count commits by author
    pipeline = [
        {
            "$group": {
                "_id": "$author.name",
                "email": {"$first": "$author.email"},
                "record_count": {"$sum": 1}
            }
        },
        {"$sort": {"record_count": -1}}
    ]

    results = list(collection.aggregate(pipeline))

    # Print Formatted Report
    print("\n=========================================================================")
    print("                    AUTHOR RECORD CREATION REPORT                        ")
    print("=========================================================================")
    print(f"{'Author Name':<25} | {'Email Address':<32} | {'Record Count':<12}")
    print("-" * 73)

    total_records = 0
    for row in results:
        author = row.get("_id") if row.get("_id") else "Unknown Author"
        email = row.get("email") if row.get("email") else "N/A"
        count = row.get("record_count", 0)

        print(f"{author:<25} | {email:<32} | {count:<12}")
        total_records += count

    print("-" * 73)
    print(f"Total Authors: {len(results):<10} | Total Records: {total_records}")
    print("=========================================================================\n")


# --- CRUD OPERATIONS ---

def create_record(collection):
    print("\n--- Create New Commit Record ---")
    commit_hash = input("Enter unique commit hash ID: ").strip()

    if collection.find_one({"commit": commit_hash}):
        print(f"Commit '{commit_hash}' already exists in MongoDB. Use Update instead.")
        return

    # Prompt for author details
    print("\n[Author Information]")
    author_name = input("Enter Author Name: ").strip()
    author_email = input("Enter Author Email: ").strip()

    # Prompt for committer details
    print("\n[Committer Information]")
    committer_name = input("Enter Committer Name: ").strip()
    committer_email = input("Enter Committer Email: ").strip()

    # Prompt for commit metadata
    print("\n[Commit Details]")
    message = input("Enter Commit Message: ").strip()
    repo_name = input("Enter Repository Name (e.g., owner/repo): ").strip()
    parent_commit = input("Enter Parent Commit Hash (optional, press Enter to skip): ").strip()
    tree_hash = input("Enter Tree Hash (optional, press Enter to skip): ").strip()

    new_record = {
        "author": {
            "email": author_email,
            "name": author_name
        },
        "commit": commit_hash,
        "committer": {
            "email": committer_email,
            "name": committer_name
        },
        "message": message,
        "parent": [parent_commit] if parent_commit else [],
        "repo_name": [repo_name] if repo_name else [],
        "subject": message,
        "tree": tree_hash
    }

    # Insert into MongoDB
    collection.insert_one(new_record)

    # Sync back to Sample.json file
    sync_mongodb_to_file(collection)
    print(f"\nSuccess! Commit '{commit_hash}' inserted and saved to Sample.json.")


def read_record(collection):
    commit_hash = input("\nEnter Commit Hash to search: ").strip()

    doc = collection.find_one({"commit": commit_hash}, {"_id": 0})
    if not doc:
        print(f"Error: Commit '{commit_hash}' does not exist in MongoDB.")
        return

    print(f"\n--- Data for Commit: '{commit_hash}' ---")
    print(json.dumps(doc, indent=4))
    print("------------------------------------")


def update_record(collection):
    commit_hash = input("\nEnter Commit Hash to update: ").strip()

    doc = collection.find_one({"commit": commit_hash})
    if not doc:
        print(f"Error: Commit '{commit_hash}' does not exist.")
        return

    print(f"\nCurrent Data for '{commit_hash}':")
    clean_doc = {k: v for k, v in doc.items() if k != '_id'}
    print(json.dumps(clean_doc, indent=4))

    field = input("\nEnter field to update (author, committer, message, repo_name, parent, tree): ").strip().lower()

    # Handle nested object structures (author / committer)
    if field in ["author", "committer"]:
        print(f"\n--- Updating {field.capitalize()} Information ---")
        current_sub = doc.get(field, {})
        if not isinstance(current_sub, dict):
            current_sub = {}

        name = input(f"Enter {field} Name (leave blank to keep '{current_sub.get('name', '')}'): ").strip()
        email = input(f"Enter {field} Email (leave blank to keep '{current_sub.get('email', '')}'): ").strip()

        updated_sub = {
            "name": name if name else current_sub.get("name", ""),
            "email": email if email else current_sub.get("email", "")
        }
        collection.update_one({"commit": commit_hash}, {"$set": {field: updated_sub}})

    # Handle array fields (repo_name / parent)
    elif field in ["repo_name", "parent"]:
        val = input(f"Enter new value for {field} array (comma-separated if multiple): ").strip()
        new_list = [item.strip() for item in val.split(",")] if val else []
        collection.update_one({"commit": commit_hash}, {"$set": {field: new_list}})

    # Handle standard string fields (message, subject, tree)
    else:
        value = input(f"Enter new value for '{field}': ").strip()
        update_payload = {field: value}
        if field == "message":
            update_payload["subject"] = value

        collection.update_one({"commit": commit_hash}, {"$set": update_payload})

    # Save to disk
    sync_mongodb_to_file(collection)
    print(f"\nSuccess! Commit '{commit_hash}' updated in MongoDB and synchronized to Sample.json.")


def delete_record(collection):
    commit_hash = input("\nEnter the Commit Hash to delete: ").strip()

    if not collection.find_one({"commit": commit_hash}):
        print(f"Error: Commit '{commit_hash}' does not exist.")
        return

    confirm = input(f"Are you sure you want to delete '{commit_hash}'? (y/n): ").strip().lower()
    if confirm == 'y':
        collection.delete_one({"commit": commit_hash})
        sync_mongodb_to_file(collection)
        print(f"Commit '{commit_hash}' deleted from MongoDB and Sample.json updated.")
    else:
        print("Deletion cancelled.")


def delete_all_data(collection):
    confirm = input("WARNING: Erase ALL documents in MongoDB collection and wipe Sample.json? (yes/no): ").strip().lower()
    if confirm == 'yes':
        collection.delete_many({})
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("All records successfully deleted from MongoDB and disk.")
    else:
        print("Operation cancelled.")


def main():
    collection = connect_mongodb()
    seed_mongodb_from_file(collection)

    while True:
        print("\n--- MONGODB JSON MANAGEMENT MENU ---")
        print("1. Create a new record")
        print("2. Read a record")
        print("3. Update a record")
        print("4. Delete a specific commit record")
        print("5. Delete ALL data from database")
        print("6. View Author Record Summary Report")
        print("7. Exit")
        print("------------------------------------")

        choice = input("Enter your choice (1-7): ").strip()

        if choice == '1':
            create_record(collection)
        elif choice == '2':
            read_record(collection)
        elif choice == '3':
            update_record(collection)
        elif choice == '4':
            delete_record(collection)
        elif choice == '5':
            delete_all_data(collection)
        elif choice == '6':
            generate_author_report(collection)
        elif choice == '7':
            print("Exiting application. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number from 1 to 7.")


if __name__ == '__main__':
    main()
