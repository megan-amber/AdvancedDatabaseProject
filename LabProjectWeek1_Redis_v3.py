'''
Name: Megan Gerth
Date: 9/10/2026
Assignment: 1.6 Lab Project
Purpose: To showcase CRUD operations and author reporting in a Redis 
         database utilizing Sample.json.
'''

import sys
import redis
import os
import json
from collections import Counter

DIR = os.path.dirname(os.path.abspath(__file__))
# Point directly to Sample.json
JSON_FILE = os.path.join(DIR, "Sample.json")


def connect_redis():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        return r
    except redis.ConnectionError:
        print("Error: Could not connect to Redis server. Ensure Redis is running.")
        sys.exit(1)


def redis_from_files(r):
    """Seed Redis using array items inside Sample.json."""
    if not os.path.exists(JSON_FILE):
        print(f"Error: File '{JSON_FILE}' does not exist.")
        return

    print("\n--- Seeding Redis Database from Sample.json ---")
    try:
        with open(JSON_FILE, 'r', encoding='utf-8-sig') as f:
            records = json.load(f)

        if not isinstance(records, list):
            records = [records]

        for record in records:
            # Use the 'commit' hash as the primary key suffix
            commit_hash = record.get('commit')
            if commit_hash:
                key_name = f"commit:{commit_hash}"
                r.set(key_name, json.dumps(record))
                print(f"Loaded record -> Redis Key: '{key_name}'")

        print("--- Database Seeding Complete ---\n")

    except json.JSONDecodeError as e:
        print(f"Failed: Invalid JSON syntax in Sample.json ({e})")
    except Exception as e:
        print(f"Failed to seed Redis: {e}")


def sync_redis_to_file(r):
    """Save all 'commit:*' records back to Sample.json to keep disk in sync."""
    keys = r.keys("commit:*")
    updated_records = []

    for key in keys:
        raw_data = r.get(key)
        if raw_data:
            updated_records.append(json.loads(raw_data))

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(updated_records, f, indent=4, ensure_ascii=False)


# --- REPORT GENERATION ---

def generate_author_report(r):
    """Generate and print a formatted summary showing record counts per author."""
    keys = r.keys("commit:*")

    if not keys:
        print("\nNo records found in Redis database.")
        return

    author_counts = Counter()
    author_emails = {}

    for key in keys:
        raw_data = r.get(key)
        if raw_data:
            try:
                data = json.loads(raw_data)
                author_obj = data.get("author", {})
                name = author_obj.get("name", "Unknown Author").strip()
                email = author_obj.get("email", "N/A").strip()

                author_counts[name] += 1
                if name not in author_emails or author_emails[name] == "N/A":
                    author_emails[name] = email
            except json.JSONDecodeError:
                continue

    # Print Formatted Report
    print("\n=========================================================================")
    print("                    AUTHOR RECORD CREATION REPORT                        ")
    print("=========================================================================")
    print(f"{'Author Name':<25} | {'Email Address':<32} | {'Record Count':<12}")
    print("-" * 73)

    total_records = 0
    for author, count in author_counts.most_common():
        email = author_emails.get(author, "N/A")
        print(f"{author:<25} | {email:<32} | {count:<12}")
        total_records += count

    print("-" * 73)
    print(f"Total Authors: {len(author_counts):<10} | Total Records: {total_records}")
    print("=========================================================================\n")


# --- CRUD OPERATIONS ---

def create_record(r):
    print("\n--- Create New Commit Record ---")
    commit_hash = input("Enter unique commit hash ID: ").strip()
    key = f"commit:{commit_hash}"

    if r.exists(key):
        print(f"Key '{key}' already exists in Redis. Use Update instead.")
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

    # Store in Redis
    r.set(key, json.dumps(new_record))

    # Sync array back to Sample.json file
    sync_redis_to_file(r)
    print(f"\nSuccess! Record created under key '{key}' and written to Sample.json.")


def read_record(r):
    commit_input = input("\nEnter Commit Hash or Key (e.g., commit:00000...): ").strip()
    key = commit_input if commit_input.startswith("commit:") else f"commit:{commit_input}"

    raw_data = r.get(key)
    if not raw_data:
        print(f"Error: Key '{key}' does not exist in Redis.")
        return

    parsed_data = json.loads(raw_data)
    print(f"\n--- Data for Key: '{key}' ---")
    print(json.dumps(parsed_data, indent=4))
    print("------------------------------------")


def update_record(r):
    commit_input = input("\nEnter Commit Hash or Key to update: ").strip()
    key = commit_input if commit_input.startswith("commit:") else f"commit:{commit_input}"

    raw_data = r.get(key)
    if not raw_data:
        print(f"Error: Key '{key}' does not exist.")
        return

    data = json.loads(raw_data)
    print(f"\nCurrent Data for '{key}':")
    print(json.dumps(data, indent=4))

    field = input("\nEnter field to update (author, committer, message, repo_name, parent, tree): ").strip().lower()

    # Handle nested object structures (author / committer)
    if field in ["author", "committer"]:
        print(f"\n--- Updating {field.capitalize()} Information ---")
        current_sub = data.get(field, {})

        name = input(f"Enter {field} Name (leave blank to keep '{current_sub.get('name', '')}'): ").strip()
        email = input(f"Enter {field} Email (leave blank to keep '{current_sub.get('email', '')}'): ").strip()

        data[field] = {
            "name": name if name else current_sub.get("name", ""),
            "email": email if email else current_sub.get("email", "")
        }

    # Handle array fields (repo_name / parent)
    elif field in ["repo_name", "parent"]:
        val = input(f"Enter new value for {field} array (comma-separated if multiple): ").strip()
        data[field] = [item.strip() for item in val.split(",")] if val else []

    # Handle standard string fields (message, subject, tree)
    else:
        value = input(f"Enter new value for '{field}': ").strip()
        data[field] = value
        # Automatically keep subject in sync if message changes
        if field == "message":
            data["subject"] = value

    # Save to Redis and disk
    r.set(key, json.dumps(data))
    sync_redis_to_file(r)
    print(f"\nSuccess! Key '{key}' updated in Redis and synchronized to Sample.json.")


def delete_record(r):
    commit_input = input("\nEnter the Commit Hash or Key to delete: ").strip()
    key = commit_input if commit_input.startswith("commit:") else f"commit:{commit_input}"

    if not r.exists(key):
        print(f"Error: Key '{key}' does not exist.")
        return

    confirm = input(f"Are you sure you want to delete '{key}'? (y/n): ").strip().lower()
    if confirm == 'y':
        r.delete(key)
        sync_redis_to_file(r)
        print(f"Key '{key}' deleted from Redis and Sample.json updated.")
    else:
        print("Deletion cancelled.")


def delete_all_data(r):
    confirm = input("WARNING: Erase ALL keys in Redis and wipe Sample.json? (yes/no): ").strip().lower()
    if confirm == 'yes':
        r.flushdb()
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("All records successfully deleted from Redis and disk.")
    else:
        print("Operation cancelled.")


def main():
    r = connect_redis()
    redis_from_files(r)

    while True:
        print("\n--- REDIS JSON MANAGEMENT MENU ---")
        print("1. Create a new record")
        print("2. Read a record")
        print("3. Update a record")
        print("4. Delete a specific commit record")
        print("5. Delete ALL data from database")
        print("6. View Author Record Summary Report")
        print("7. Exit")
        print("----------------------------------")

        choice = input("Enter your choice (1-7): ").strip()

        if choice == '1':
            create_record(r)
        elif choice == '2':
            read_record(r)
        elif choice == '3':
            update_record(r)
        elif choice == '4':
            delete_record(r)
        elif choice == '5':
            delete_all_data(r)
        elif choice == '6':
            generate_author_report(r)
        elif choice == '7':
            print("Exiting application. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a number from 1 to 7.")


if __name__ == '__main__':
    main()
