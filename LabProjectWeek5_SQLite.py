'''
Name: Megan Gerth
Date: 10/1/2026
Assignment: Lab Project - SQLite Edition
Purpose: To showcase CRUD operations, author commit counts, and phrase 
         searching in a SQLite relational database utilizing Sample.json.
'''

import sys
import os
import json
import sqlite3

DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(DIR, "Sample.json")
DB_FILE = os.path.join(DIR, "git_database.db")

TABLE_NAME = "Commits"

def connect_sqlite():
    """Connect to local SQLite database file, create table if missing."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                [commit] TEXT PRIMARY KEY,
                author_name TEXT,
                author_email TEXT,
                committer_name TEXT,
                committer_email TEXT,
                message TEXT,
                subject TEXT,
                tree TEXT,
                parent TEXT,
                repo_name TEXT
            );
        """)
        conn.commit()
        return conn
    except Exception as e:
        print(f"Error: Could not connect to SQLite database ({e}).")
        sys.exit(1)


def seed_sqlite_from_file(conn):
    """Seed SQLite table using array items inside Sample.json."""
    if not os.path.exists(JSON_FILE):
        print(f"Error: File '{JSON_FILE}' does not exist.")
        return

    print("\n--- Seeding SQLite Database from Sample.json ---")
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
        row_count = cursor.fetchone()[0]

        if row_count == 0:
            with open(JSON_FILE, 'r', encoding='utf-8-sig') as f:
                records = json.load(f)

            if not isinstance(records, list):
                records = [records]

            insert_sql = f"""
                INSERT INTO {TABLE_NAME} (
                    [commit], author_name, author_email, committer_name, committer_email,
                    message, subject, tree, parent, repo_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            for rec in records:
                author = rec.get('author', {}) or {}
                committer = rec.get('committer', {}) or {}

                cursor.execute(insert_sql, (
                    rec.get('commit', ''),
                    author.get('name', ''),
                    author.get('email', ''),
                    committer.get('name', ''),
                    committer.get('email', ''),
                    rec.get('message', ''),
                    rec.get('subject', ''),
                    rec.get('tree', ''),
                    json.dumps(rec.get('parent', [])),
                    json.dumps(rec.get('repo_name', []))
                ))

            conn.commit()
            print(f"Loaded {len(records)} records into SQLite table '{TABLE_NAME}'.")
        else:
            print(f"Table '{TABLE_NAME}' already contains data. Skipping initial seed.")

        print("--- Database Seeding Complete ---\n")

    except json.JSONDecodeError as e:
        print(f"Failed: Invalid JSON syntax in Sample.json ({e})")
    except Exception as e:
        print(f"Failed to seed SQLite database: {e}")


def row_to_dict(row):
    """Helper to convert a SQLite Row object into standard Sample.json format."""
    parent_data = json.loads(row['parent']) if row['parent'] else []
    repo_data = json.loads(row['repo_name']) if row['repo_name'] else []

    return {
        "author": {
            "email": row['author_email'] or "",
            "name": row['author_name'] or ""
        },
        "commit": row['commit'],
        "committer": {
            "email": row['committer_email'] or "",
            "name": row['committer_name'] or ""
        },
        "message": row['message'] or "",
        "parent": parent_data,
        "repo_name": repo_data,
        "subject": row['subject'] or "",
        "tree": row['tree'] or ""
    }


def sync_sqlite_to_file(conn):
    """Save all records from SQLite table back to Sample.json."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_NAME};")
    rows = cursor.fetchall()

    records = [row_to_dict(row) for row in rows]

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4, ensure_ascii=False)


# --- MENU FUNCTIONS ---

def read_record(conn):
    """1. Display a record"""
    commit_hash = input("\nEnter Commit Hash to search: ").strip()

    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE [commit] = ?;", (commit_hash,))
    row = cursor.fetchone()

    if not row:
        print(f"Error: Commit '{commit_hash}' does not exist in SQLite.")
        return

    record = row_to_dict(row)
    print(f"\n--- Data for Commit: '{commit_hash}' ---")
    print(json.dumps(record, indent=4))
    print("------------------------------------")


def create_record(conn):
    """2. Create a record"""
    print("\n--- Create New Commit Record ---")
    commit_hash = input("Enter unique commit hash ID: ").strip()

    cursor = conn.cursor()
    cursor.execute(f"SELECT [commit] FROM {TABLE_NAME} WHERE [commit] = ?;", (commit_hash,))
    if cursor.fetchone():
        print(f"Commit '{commit_hash}' already exists in SQLite. Use Update instead.")
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

    insert_sql = f"""
        INSERT INTO {TABLE_NAME} (
            [commit], author_name, author_email, committer_name, committer_email,
            message, subject, tree, parent, repo_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    cursor.execute(insert_sql, (
        commit_hash, author_name, author_email, committer_name, committer_email,
        message, message, tree_hash,
        json.dumps([parent_commit] if parent_commit else []),
        json.dumps([repo_name] if repo_name else [])
    ))
    conn.commit()

    sync_sqlite_to_file(conn)
    print(f"\nSuccess! Commit '{commit_hash}' inserted into SQLite and saved to Sample.json.")


def update_record(conn):
    """3. Update a record"""
    commit_hash = input("\nEnter Commit Hash to update: ").strip()

    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE [commit] = ?;", (commit_hash,))
    row = cursor.fetchone()

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

        cursor.execute(f"UPDATE {TABLE_NAME} SET author_name = ?, author_email = ? WHERE commit = ?;",
                       (new_name, new_email, commit_hash))

    elif field == "committer":
        print("\n--- Updating Committer Information ---")
        name = input(f"Enter Committer Name (leave blank to keep '{record['committer']['name']}'): ").strip()
        email = input(f"Enter Committer Email (leave blank to keep '{record['committer']['email']}'): ").strip()

        new_name = name if name else record['committer']['name']
        new_email = email if email else record['committer']['email']

        cursor.execute(f"UPDATE {TABLE_NAME} SET committer_name = ?, committer_email = ? WHERE [commit] = ?;",
                       (new_name, new_email, commit_hash))

    elif field in ["repo_name", "parent"]:
        val = input(f"Enter new value for {field} array (comma-separated if multiple): ").strip()
        new_list = [item.strip() for item in val.split(",")] if val else []

        cursor.execute(f"UPDATE {TABLE_NAME} SET {field} = ? WHERE [commit] = ?;",
                       (json.dumps(new_list), commit_hash))

    elif field == "message":
        value = input("Enter new message value: ").strip()
        cursor.execute(f"UPDATE {TABLE_NAME} SET message = ?, subject = ? WHERE [commit] = ?;",
                       (value, value, commit_hash))

    elif field == "tree":
        value = input("Enter new tree value: ").strip()
        cursor.execute(f"UPDATE {TABLE_NAME} SET tree = ? WHERE [commit] = ?;",
                       (value, commit_hash))

    else:
        print(f"Field '{field}' is invalid or cannot be modified.")
        return

    conn.commit()
    sync_sqlite_to_file(conn)
    print(f"\nSuccess! Commit '{commit_hash}' updated in SQLite and synchronized to Sample.json.")


def count_author_commits(conn):
    """4. Count of each author's commits"""
    cursor = conn.cursor()
    query = f"""
        SELECT author_name, COUNT(*) AS commit_count 
        FROM {TABLE_NAME} 
        GROUP BY author_name 
        ORDER BY commit_count DESC;
    """
    cursor.execute(query)
    results = cursor.fetchall()

    if not results:
        print("\nNo records found in the database.")
        return

    print("\n=========================================================")
    print("                AUTHOR COMMIT COUNT REPORT               ")
    print("=========================================================")
    print(f"{'Author Name':<35} | {'Total Commits':<12}")
    print("-" * 55)

    total_commits = 0
    for row in results:
        author = row['author_name'] if row['author_name'] else "Unknown Author"
        count = row['commit_count']
        print(f"{author:<35} | {count:<12}")
        total_commits += count

    print("-" * 55)
    print(f"Total Authors: {len(results):<15} | Total Commits: {total_commits}")
    print("=========================================================\n")


def find_records_by_phrase(conn):
    """5. Find records by phrase in commit message"""
    phrase = input("\nEnter the keyword or phrase to search for: ").strip()

    if not phrase:
        print("Search phrase cannot be blank.")
        return

    cursor = conn.cursor()
    query = f"SELECT * FROM {TABLE_NAME} WHERE message LIKE ?;"
    cursor.execute(query, (f"%{phrase}%",))
    rows = cursor.fetchall()

    matching_records = [row_to_dict(row) for row in rows]

    if not matching_records:
        print(f"\nNo commit records found containing phrase: '{phrase}'")
        return

    print(f"\n=========================================================================")
    print(f"          SEARCH RESULTS FOR PHRASE: '{phrase}' ({len(matching_records)} found)")
    print(f"=========================================================================")

    for idx, rec in enumerate(matching_records, start=1):
        print(f"\n[{idx}] Commit Hash: {rec['commit']}")
        print(f"    Author   : {rec['author']['name']} <{rec['author']['email']}>")
        print(f"    Committer: {rec['committer']['name']} <{rec['committer']['email']}>")
        print(f"    Repo     : {', '.join(rec['repo_name']) if rec['repo_name'] else 'N/A'}")
        print(f"    Message  : {rec['message'].strip()}")

    print("=========================================================================\n")


def delete_record(conn):
    """6. Delete a specific record"""
    commit_hash = input("\nEnter the Commit Hash to delete: ").strip()

    cursor = conn.cursor()
    cursor.execute(f"SELECT [commit] FROM {TABLE_NAME} WHERE [commit] = ?;", (commit_hash,))
    if not cursor.fetchone():
        print(f"Error: Commit '{commit_hash}' does not exist.")
        return

    confirm = input(f"Are you sure you want to delete '{commit_hash}'? (y/n): ").strip().lower()
    if confirm == 'y':
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE [commit] = ?;", (commit_hash,))
        conn.commit()
        sync_sqlite_to_file(conn)
        print(f"Commit '{commit_hash}' deleted from SQLite and Sample.json updated.")
    else:
        print("Deletion cancelled.")


def delete_all_data(conn):
    """7. Delete all records"""
    confirm = input("WARNING: Erase ALL records in SQLite database and wipe Sample.json? (yes/no): ").strip().lower()
    if confirm == 'yes':
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {TABLE_NAME};")
        conn.commit()

        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("All records successfully deleted from SQLite and disk.")
    else:
        print("Operation cancelled.")


def main():
    conn = connect_sqlite()
    seed_sqlite_from_file(conn)

    try:
        while True:
            print("\n--- SQLITE JSON MANAGEMENT MENU ---")
            print("1. Display a record")
            print("2. Create a record")
            print("3. Update a record")
            print("4. Count of each author's commits")
            print("5. Find records by phrase in commit message")
            print("6. Delete a specific record")
            print("7. Delete all records")
            print("8. Exit the program")
            print("-----------------------------------")

            choice = input("Enter your choice (1-8): ").strip()

            if choice == '1':
                read_record(conn)
            elif choice == '2':
                create_record(conn)
            elif choice == '3':
                update_record(conn)
            elif choice == '4':
                count_author_commits(conn)
            elif choice == '5':
                find_records_by_phrase(conn)
            elif choice == '6':
                delete_record(conn)
            elif choice == '7':
                delete_all_data(conn)
            elif choice == '8':
                print("Exiting application. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter a number from 1 to 8.")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
