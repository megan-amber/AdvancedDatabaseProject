'''
Name: Megan Gerth
Date: 9/23/2026
Assignment: Lab Project - Neo4j Edition
Purpose: To showcase CRUD operations and author querying in a Neo4j 
         graph database utilizing Sample.json.
'''

import sys
import os
import json
from neo4j import GraphDatabase

DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(DIR, "Sample.json")

# Neo4j Connection Credentials
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password1"  


def connect_neo4j():
    """Connect to local Neo4j instance and verify connectivity."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(f"Error: Could not connect to Neo4j database ({e}). Ensure Neo4j is running.")
        sys.exit(1)


def seed_neo4j_from_file(driver):
    """Seed Neo4j database with :Commit nodes using array items inside Sample.json."""
    if not os.path.exists(JSON_FILE):
        print(f"Error: File '{JSON_FILE}' does not exist.")
        return

    print("\n--- Seeding Neo4j Database from Sample.json ---")
    try:
        with driver.session() as session:
            # Create the unique constraint first so the label is registered in the DB schema
            session.run("CREATE CONSTRAINT commit_hash_unique IF NOT EXISTS FOR (c:Commit) REQUIRE c.commit IS UNIQUE")

            # Check count safely
            count = session.run("MATCH (c:Commit) RETURN count(c) AS total").single()["total"]

            if count == 0:
                with open(JSON_FILE, 'r', encoding='utf-8-sig') as f:
                    records = json.load(f)

                if not isinstance(records, list):
                    records = [records]

                cypher = """
                UNWIND $batch AS rec
                CREATE (c:Commit {
                    commit: rec.commit,
                    author_name: rec.author.name,
                    author_email: rec.author.email,
                    committer_name: rec.committer.name,
                    committer_email: rec.committer.email,
                    message: rec.message,
                    subject: rec.subject,
                    tree: rec.tree,
                    parent: rec.parent,
                    repo_name: rec.repo_name
                })
                """
                session.run(cypher, batch=records)
                print(f"Loaded {len(records)} records as :Commit nodes into Neo4j.")
            else:
                print(f"Neo4j database already contains {count} commit nodes. Skipping initial seed.")

        print("--- Database Seeding Complete ---\n")

    except json.JSONDecodeError as e:
        print(f"Failed: Invalid JSON syntax in Sample.json ({e})")
    except Exception as e:
        print(f"Failed to seed Neo4j: {e}")


def node_to_dict(record):
    """Helper to convert a Neo4j record into standard Sample.json format."""
    c = record["c"]
    return {
        "author": {
            "email": c.get("author_email", ""),
            "name": c.get("author_name", "")
        },
        "commit": c.get("commit", ""),
        "committer": {
            "email": c.get("committer_email", ""),
            "name": c.get("committer_name", "")
        },
        "message": c.get("message", ""),
        "parent": list(c.get("parent", [])),
        "repo_name": list(c.get("repo_name", [])),
        "subject": c.get("subject", ""),
        "tree": c.get("tree", "")
    }


def sync_neo4j_to_file(driver):
    """Save all :Commit nodes from Neo4j back to Sample.json."""
    with driver.session() as session:
        result = session.run("MATCH (c:Commit) RETURN c")
        records = [node_to_dict(rec) for rec in result]

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4, ensure_ascii=False)


#Query by author

def query_by_author(driver):
    """Search and display all commits created by a specific author name using Cypher Regex."""
    search_name = input("\nEnter Author Name to search for: ").strip()

    if not search_name:
        print("Author name cannot be blank.")
        return

    cypher = """
    MATCH (c:Commit)
    WHERE c.author_name =~ (?i).*' + $search_name + '.*'
    RETURN c
    """

    # Alternative safe Cypher syntax using CONTAINS:
    cypher_safe = """
    MATCH (c:Commit)
    WHERE toLower(c.author_name) CONTAINS toLower($search_name)
    RETURN c
    """

    with driver.session() as session:
        result = session.run(cypher_safe, search_name=search_name)
        matching_records = [node_to_dict(rec) for rec in result]

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


#CRUD OPERATIONS

def create_record(driver):
    print("\n--- Create New Commit Record ---")
    commit_hash = input("Enter unique commit hash ID: ").strip()

    with driver.session() as session:
        existing = session.run("MATCH (c:Commit {commit: $hash}) RETURN c", hash=commit_hash).single()
        if existing:
            print(f"Commit '{commit_hash}' already exists in Neo4j. Use Update instead.")
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

        cypher = """
        CREATE (c:Commit {
            commit: $commit,
            author_name: $author_name,
            author_email: $author_email,
            committer_name: $committer_name,
            committer_email: $committer_email,
            message: $message,
            subject: $subject,
            tree: $tree,
            parent: $parent,
            repo_name: $repo_name
        })
        """
        session.run(cypher,
                    commit=commit_hash,
                    author_name=author_name,
                    author_email=author_email,
                    committer_name=committer_name,
                    committer_email=committer_email,
                    message=message,
                    subject=message,
                    tree=tree_hash,
                    parent=[parent_commit] if parent_commit else [],
                    repo_name=[repo_name] if repo_name else [])

    # Sync back to Sample.json file
    sync_neo4j_to_file(driver)
    print(f"\nSuccess! Commit '{commit_hash}' inserted into Neo4j and saved to Sample.json.")


def read_record(driver):
    commit_hash = input("\nEnter Commit Hash to search: ").strip()

    with driver.session() as session:
        result = session.run("MATCH (c:Commit {commit: $hash}) RETURN c", hash=commit_hash).single()

        if not result:
            print(f"Error: Commit '{commit_hash}' does not exist in Neo4j.")
            return

        record = node_to_dict(result)
        print(f"\n--- Data for Commit: '{commit_hash}' ---")
        print(json.dumps(record, indent=4))
        print("------------------------------------")


def update_record(driver):
    commit_hash = input("\nEnter Commit Hash to update: ").strip()

    with driver.session() as session:
        result = session.run("MATCH (c:Commit {commit: $hash}) RETURN c", hash=commit_hash).single()

        if not result:
            print(f"Error: Commit '{commit_hash}' does not exist.")
            return

        record = node_to_dict(result)
        print(f"\nCurrent Data for '{commit_hash}':")
        print(json.dumps(record, indent=4))

        field = input("\nEnter field to update (author, committer, message, repo_name, parent, tree): ").strip().lower()

        if field == "author":
            print("\n--- Updating Author Information ---")
            name = input(f"Enter Author Name (leave blank to keep '{record['author']['name']}'): ").strip()
            email = input(f"Enter Author Email (leave blank to keep '{record['author']['email']}'): ").strip()

            new_name = name if name else record['author']['name']
            new_email = email if email else record['author']['email']

            session.run("""
                MATCH (c:Commit {commit: $hash})
                SET c.author_name = $name, c.author_email = $email
            """, hash=commit_hash, name=new_name, email=new_email)

        elif field == "committer":
            print("\n--- Updating Committer Information ---")
            name = input(f"Enter Committer Name (leave blank to keep '{record['committer']['name']}'): ").strip()
            email = input(f"Enter Committer Email (leave blank to keep '{record['committer']['email']}'): ").strip()

            new_name = name if name else record['committer']['name']
            new_email = email if email else record['committer']['email']

            session.run("""
                MATCH (c:Commit {commit: $hash})
                SET c.committer_name = $name, c.committer_email = $email
            """, hash=commit_hash, name=new_name, email=new_email)

        elif field in ["repo_name", "parent"]:
            val = input(f"Enter new value for {field} array (comma-separated if multiple): ").strip()
            new_list = [item.strip() for item in val.split(",")] if val else []

            session.run(f"""
                MATCH (c:Commit {{commit: $hash}})
                SET c.{field} = $val
            """, hash=commit_hash, val=new_list)

        elif field == "message":
            value = input("Enter new message value: ").strip()
            session.run("""
                MATCH (c:Commit {commit: $hash})
                SET c.message = $val, c.subject = $val
            """, hash=commit_hash, val=value)

        elif field == "tree":
            value = input("Enter new tree value: ").strip()
            session.run("""
                MATCH (c:Commit {commit: $hash})
                SET c.tree = $val
            """, hash=commit_hash, val=value)

        else:
            print(f"Field '{field}' is invalid or cannot be modified.")
            return

    # Sync to disk
    sync_neo4j_to_file(driver)
    print(f"\nSuccess! Commit '{commit_hash}' updated in Neo4j and synchronized to Sample.json.")


def delete_record(driver):
    commit_hash = input("\nEnter the Commit Hash to delete: ").strip()

    with driver.session() as session:
        result = session.run("MATCH (c:Commit {commit: $hash}) RETURN c", hash=commit_hash).single()
        if not result:
            print(f"Error: Commit '{commit_hash}' does not exist.")
            return

        confirm = input(f"Are you sure you want to delete '{commit_hash}'? (y/n): ").strip().lower()
        if confirm == 'y':
            session.run("MATCH (c:Commit {commit: $hash}) DETACH DELETE c", hash=commit_hash)
            sync_neo4j_to_file(driver)
            print(f"Commit '{commit_hash}' deleted from Neo4j and Sample.json updated.")
        else:
            print("Deletion cancelled.")


def delete_all_data(driver):
    confirm = input("WARNING: Erase ALL :Commit nodes in Neo4j and wipe Sample.json? (yes/no): ").strip().lower()
    if confirm == 'yes':
        with driver.session() as session:
            session.run("MATCH (c:Commit) DETACH DELETE c")

        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("All records successfully deleted from Neo4j and disk.")
    else:
        print("Operation cancelled.")


def main():
    driver = connect_neo4j()
    seed_neo4j_from_file(driver)

    try:
        while True:
            print("\n--- NEO4J JSON MANAGEMENT MENU ---")
            print("1. Create a new record")
            print("2. Read a record")
            print("3. Update a record")
            print("4. Delete a specific commit record")
            print("5. Delete ALL data from database")
            print("6. Query records by author name")
            print("7. Exit")
            print("----------------------------------")

            choice = input("Enter your choice (1-7): ").strip()

            if choice == '1':
                create_record(driver)
            elif choice == '2':
                read_record(driver)
            elif choice == '3':
                update_record(driver)
            elif choice == '4':
                delete_record(driver)
            elif choice == '5':
                delete_all_data(driver)
            elif choice == '6':
                query_by_author(driver)
            elif choice == '7':
                print("Exiting application. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter a number from 1 to 7.")

    finally:
        driver.close()


if __name__ == '__main__':
    main()
