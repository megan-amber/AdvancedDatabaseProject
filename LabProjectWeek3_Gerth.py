'''
Name: Megan Gerth
Date: 9/20/2026
Assignment: Lab Project - Cassandra Edition
Purpose: To showcase CRUD operations and author querying in an Apache 
         Cassandra database utilizing Sample.json.
'''

import sys
import os
import json
from cassandra.cluster import Cluster

DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(DIR, "Sample.json")

KEYSPACE = "git_keyspace"
TABLE_NAME = "commits"


def connect_cassandra():
    """Connect to local Cassandra cluster, create Keyspace and Table if missing."""
    try:
        cluster = Cluster(['127.0.0.1'], port=9042)
        session = cluster.connect()

        # Create Keyspace if it doesn't exist
        session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}};
        """)

        session.set_keyspace(KEYSPACE)

        # Create Table matching Sample.json structure
        session.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                commit text PRIMARY KEY,
                author_name text,
                author_email text,
                committer_name text,
                committer_email text,
                message text,
                subject text,
                tree text,
                parent list<text>,
                repo_name list<text>
            );
        """)

        return session, cluster
    except Exception as e:
        print(f"Error: Could not connect to Cassandra cluster ({e}). Ensure Cassandra is running.")
        sys.exit(1)


def seed_cassandra_from_file(session):
    """Seed Cassandra table using array items inside Sample.json."""
    if not os.path.exists(JSON_FILE):
        print(f"Error: File '{JSON_FILE}' does not exist.")
        return

    print("\n--- Seeding Cassandra Database from Sample.json ---")
    try:
        count_result = session.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
        row_count = count_result.one()[0]

        if row_count == 0:
            with open(JSON_FILE, 'r', encoding='utf-8-sig') as f:
                records = json.load(f)

            if not isinstance(records, list):
                records = [records]

            insert_stmt = session.prepare(f"""
                INSERT INTO {TABLE_NAME} (
                    commit, author_name, author_email, committer_name, committer_email,
                    message, subject, tree, parent, repo_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)

            for rec in records:
                author = rec.get('author', {}) or {}
                committer = rec.get('committer', {}) or {}

                session.execute(insert_stmt, (
                    rec.get('commit', ''),
                    author.get('name', ''),
                    author.get('email', ''),
                    committer.get('name', ''),
                    committer.get('email', ''),
                    rec.get('message', ''),
                    rec.get('subject', ''),
                    rec.get('tree', ''),
                    rec.get('parent', []),
                    rec.get('repo_name', [])
                ))

            print(f"Loaded {len(records)} records into Cassandra table '{TABLE_NAME}'.")
        else:
            print(f"Table '{TABLE_NAME}' already contains data. Skipping initial seed.")

        print("--- Database Seeding Complete ---\n")

    except json.JSONDecodeError as e:
        print(f"Failed: Invalid JSON syntax in Sample.json ({e})")
    except Exception as e:
        print(f"Failed to seed Cassandra: {e}")


def row_to_dict(row):
    """Helper to convert Cassandra Row object into standard Sample.json format."""
    return {
        "author": {
            "email": row.author_email or "",
            "name": row.author_name or ""
        },
        "commit": row.commit,
        "committer": {
            "email": row.committer_email or "",
            "name": row.committer_name or ""
        },
        "message": row.message or "",
        "parent": list(row.parent) if row.parent else [],
        "repo_name": list(row.repo_name) if row.repo_name else [],
        "subject": row.subject or "",
        "tree": row.tree or ""
    }


def sync_cassandra_to_file(session):
    """Save all records from Cassandra table back to Sample.json."""
    rows = session.execute(f"SELECT * FROM {TABLE_NAME};")
    records = [row_to_dict(row) for row in rows]

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4, ensure_ascii=False)


# --- QUERY BY AUTHOR ---

def query_by_author(session):
    """Search and display all commits created by a specific author name."""
    search_name = input("\nEnter Author Name to search for: ").strip()

    if not search_name:
        print("Author name cannot be blank.")
        return

    rows = session.execute(f"SELECT * FROM {TABLE_NAME};")
    matching_records = []

    for row in rows:
        author_name = row.author_name or ""
        # Check for case-insensitive exact or partial match
        if search_name.lower() in author_name.lower():
            matching_records.append(row_to_dict(row))

    if not matching_records:
        print(f"\nNo commit records found for author: '{search_name}'")
        return

    print(f"\n=========================================================================")
    print(f"             SEARCH RESULTS FOR AUTHOR: '{search_name}' ({len(matching_records)} found)")
    print(f"=========================================================================")

    for idx, rec in enumerate(matching_records, start=1):
        print(f"\n[{idx}] Commit Hash: {rec['commit']}")
        print(f"    Author   : {rec['author']['name']} <{rec['author']['email']}>")
        print(f"    Committer: {rec['committer']['name']} <{rec['committer']['email']}>")
        print(f"    Repo     : {', '.join(rec['repo_name']) if rec['repo_name'] else 'N/A'}")
        print(f"    Message  : {rec['message'].strip()}")

    print("=========================================================================\n")


# --- CRUD OPERATIONS ---

def create_record(session):
    print("\n--- Create New Commit Record ---")
    commit_hash = input("Enter unique commit hash ID: ").strip()

    stmt = session.prepare(f"SELECT commit FROM {TABLE_NAME} WHERE commit = ?;")
    if session.execute(stmt, [commit_hash]).one():
        print(f"Commit '{commit_hash}' already exists in Cassandra. Use Update instead.")
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

    insert_stmt = session.prepare(f"""
        INSERT INTO {TABLE_NAME} (
            commit, author_name, author_email, committer_name, committer_email,
            message, subject, tree, parent, repo_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    session.execute(insert_stmt, (
        commit_hash, author_name, author_email, committer_name, committer_email,
        message, message, tree_hash,
        [parent_commit] if parent_commit else [],
        [repo_name] if repo_name else []
    ))

    # Sync back to Sample.json file
    sync_cassandra_to_file(session)
    print(f"\nSuccess! Commit '{commit_hash}' inserted and saved to Sample.json.")


def read_record(session):
    commit_hash = input("\nEnter Commit Hash to search: ").strip()

    stmt = session.prepare(f"SELECT * FROM {TABLE_NAME} WHERE commit = ?;")
    row = session.execute(stmt, [commit_hash]).one()

    if not row:
        print(f"Error: Commit '{commit_hash}' does not exist in Cassandra.")
        return

    record = row_to_dict(row)
    print(f"\n--- Data for Commit: '{commit_hash}' ---")
    print(json.dumps(record, indent=4))
    print("------------------------------------")


def update_record(session):
    commit_hash = input("\nEnter Commit Hash to update: ").strip()

    stmt = session.prepare(f"SELECT * FROM {TABLE_NAME} WHERE commit = ?;")
    row = session.execute(stmt, [commit_hash]).one()

    if not row:
        print(f"Error: Commit '{commit_hash}' does not exist.")
        return

    record = row_to_dict(row)
    print(f"\nCurrent Data for '{commit_hash}':")
    print(json.dumps(record, indent=4))

    field = input("\nEnter field to update (author, committer, message, repo_name, parent, tree): ").strip().lower()

    if field == "author":
        print("\n--- Updating Author Information ---")
        name = input(f"Enter Author Name (leave blank to keep '{record['author']['name']}'): ").strip()
        email = input(f"Enter Author Email (leave blank to keep '{record['author']['email']}'): ").strip()

        new_name = name if name else record['author']['name']
        new_email = email if email else record['author']['email']

        u_stmt = session.prepare(f"UPDATE {TABLE_NAME} SET author_name = ?, author_email = ? WHERE commit = ?;")
        session.execute(u_stmt, (new_name, new_email, commit_hash))

    elif field == "committer":
        print("\n--- Updating Committer Information ---")
        name = input(f"Enter Committer Name (leave blank to keep '{record['committer']['name']}'): ").strip()
        email = input(f"Enter Committer Email (leave blank to keep '{record['committer']['email']}'): ").strip()

        new_name = name if name else record['committer']['name']
        new_email = email if email else record['committer']['email']

        u_stmt = session.prepare(f"UPDATE {TABLE_NAME} SET committer_name = ?, committer_email = ? WHERE commit = ?;")
        session.execute(u_stmt, (new_name, new_email, commit_hash))

    elif field in ["repo_name", "parent"]:
        val = input(f"Enter new value for {field} array (comma-separated if multiple): ").strip()
        new_list = [item.strip() for item in val.split(",")] if val else []

        u_stmt = session.prepare(f"UPDATE {TABLE_NAME} SET {field} = ? WHERE commit = ?;")
        session.execute(u_stmt, (new_list, commit_hash))

    elif field == "message":
        value = input("Enter new message value: ").strip()
        u_stmt = session.prepare(f"UPDATE {TABLE_NAME} SET message = ?, subject = ? WHERE commit = ?;")
        session.execute(u_stmt, (value, value, commit_hash))

    elif field == "tree":
        value = input("Enter new tree value: ").strip()
        u_stmt = session.prepare(f"UPDATE {TABLE_NAME} SET tree = ? WHERE commit = ?;")
        session.execute(u_stmt, (value, commit_hash))

    else:
        print(f"Field '{field}' is invalid or cannot be modified.")
        return

    # Sync to disk
    sync_cassandra_to_file(session)
    print(f"\nSuccess! Commit '{commit_hash}' updated in Cassandra and synchronized to Sample.json.")


def delete_record(session):
    commit_hash = input("\nEnter the Commit Hash to delete: ").strip()

    stmt = session.prepare(f"SELECT commit FROM {TABLE_NAME} WHERE commit = ?;")
    if not session.execute(stmt, [commit_hash]).one():
        print(f"Error: Commit '{commit_hash}' does not exist.")
        return

    confirm = input(f"Are you sure you want to delete '{commit_hash}'? (y/n): ").strip().lower()
    if confirm == 'y':
        del_stmt = session.prepare(f"DELETE FROM {TABLE_NAME} WHERE commit = ?;")
        session.execute(del_stmt, [commit_hash])
        sync_cassandra_to_file(session)
        print(f"Commit '{commit_hash}' deleted from Cassandra and Sample.json updated.")
    else:
        print("Deletion cancelled.")


def delete_all_data(session):
    confirm = input("WARNING: Erase ALL records in Cassandra table and wipe Sample.json? (yes/no): ").strip().lower()
    if confirm == 'yes':
        session.execute(f"TRUNCATE {TABLE_NAME};")
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("All records successfully deleted from Cassandra and disk.")
    else:
        print("Operation cancelled.")


def main():
    session, cluster = connect_cassandra()
    seed_cassandra_from_file(session)

    try:
        while True:
            print("\n--- CASSANDRA JSON MANAGEMENT MENU ---")
            print("1. Create a new record")
            print("2. Read a record")
            print("3. Update a record")
            print("4. Delete a specific commit record")
            print("5. Delete ALL data from database")
            print("6. Query records by author name")
            print("7. Exit")
            print("--------------------------------------")

            choice = input("Enter your choice (1-7): ").strip()

            if choice == '1':
                create_record(session)
            elif choice == '2':
                read_record(session)
            elif choice == '3':
                update_record(session)
            elif choice == '4':
                delete_record(session)
            elif choice == '5':
                delete_all_data(session)
            elif choice == '6':
                query_by_author(session)
            elif choice == '7':
                print("Exiting application. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter a number from 1 to 7.")

    finally:
        cluster.shutdown()


if __name__ == '__main__':
    main()
