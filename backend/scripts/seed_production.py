#!/usr/bin/env python3
"""
Production seeding script for adding consultants to Weaviate.
This script is optimized for production use with better error handling and logging.
"""
import weaviate
import os
import sys
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import from main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Default to weaviate service name for Docker Compose
weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080")

def connect_to_weaviate(max_retries=30, retry_delay=2):
    """Connect to Weaviate with retries."""
    print(f"Connecting to Weaviate at {weaviate_url}")
    
    import time
    for attempt in range(max_retries):
        try:
            client = weaviate.Client(url=weaviate_url)
            # Test connection by checking schema
            client.schema.get()
            print("✓ Successfully connected to Weaviate")
            return client
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"ERROR: Failed to connect to Weaviate after {max_retries} attempts: {e}")
                sys.exit(1)
    
    return None

def load_consultant_data(data_file):
    """Load consultant data from JSON file."""
    data_path = Path(data_file)
    
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        sys.exit(1)
    
    try:
        with open(data_path, "r") as f:
            consultants = json.load(f)
        
        if not isinstance(consultants, list):
            print(f"ERROR: JSON file must contain an array of consultants")
            sys.exit(1)
        
        print(f"✓ Loaded {len(consultants)} consultants from {data_path}")
        return consultants
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in data file {data_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load data file {data_path}: {e}")
        sys.exit(1)

def validate_consultant(consultant):
    """Validate consultant data structure."""
    required_fields = ["name", "email", "skills", "availability", "experience", "education"]
    missing = [field for field in required_fields if field not in consultant]
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    if not isinstance(consultant["skills"], list):
        return False, "Skills must be a list"
    
    if consultant["availability"] not in ["available", "busy", "unavailable"]:
        return False, f"Availability must be one of: available, busy, unavailable"
    
    return True, None

def insert_consultants(client, consultants, force=False):
    """Insert consultants into Weaviate."""
    # Check if class exists
    print("Checking Weaviate schema...")
    try:
        schema = client.schema.get()
        class_names = [c["class"] for c in schema.get("classes", [])]
        if "Consultant" not in class_names:
            print("ERROR: Consultant class does not exist. Please run init_weaviate.py first.")
            sys.exit(1)
        print("✓ Consultant class exists")
    except Exception as e:
        print(f"ERROR: Failed to check schema: {e}")
        sys.exit(1)
    
    # Check for existing consultants (unless force)
    if not force:
        print("Checking for existing consultants...")
        try:
            result = client.query.get("Consultant", ["name"]).with_limit(1).do()
            existing_count = len(result.get("data", {}).get("Get", {}).get("Consultant", []))
            if existing_count > 0:
                print(f"ℹ Database contains {existing_count} existing consultant(s)")
                print("  (Use --force to add consultants anyway)")
        except Exception as e:
            print(f"WARNING: Could not check existing data: {e}")
    
    # Validate consultants
    print(f"\nValidating {len(consultants)} consultants...")
    valid_consultants = []
    for i, consultant in enumerate(consultants):
        is_valid, error = validate_consultant(consultant)
        if not is_valid:
            print(f"  ✗ Consultant {i+1} ({consultant.get('name', 'Unknown')}): {error}")
            continue
        valid_consultants.append(consultant)
    
    if not valid_consultants:
        print("ERROR: No valid consultants to insert")
        sys.exit(1)
    
    if len(valid_consultants) < len(consultants):
        print(f"⚠ {len(consultants) - len(valid_consultants)} consultant(s) failed validation")
    
    # Batch insert
    print(f"\nInserting {len(valid_consultants)} consultants...")
    inserted_count = 0
    errors = []
    
    try:
        with client.batch as batch:
            batch.batch_size = 10
            batch.num_workers = 1
            
            for consultant in valid_consultants:
                try:
                    batch.add_data_object(
                        data_object=consultant,
                        class_name="Consultant"
                    )
                    inserted_count += 1
                    if inserted_count % 10 == 0:
                        print(f"  Added {inserted_count}/{len(valid_consultants)} consultants...")
                except Exception as e:
                    error_msg = f"Error adding consultant {consultant.get('name', 'Unknown')}: {e}"
                    print(f"  ✗ {error_msg}")
                    errors.append(error_msg)
            
            # Flush any remaining items
            batch.flush()
            
            # Check for batch errors
            if hasattr(batch, 'errors') and batch.errors:
                print(f"WARNING: {len(batch.errors)} errors occurred during batch insert:")
                for error in batch.errors:
                    print(f"  - {error}")
                    errors.append(str(error))
    except Exception as e:
        print(f"ERROR: Batch insert failed: {e}")
        sys.exit(1)
    
    # Verify insertion
    print("\nVerifying insertion...")
    try:
        result = client.query.get("Consultant", ["name"]).with_limit(len(valid_consultants) + 100).do()
        verified_count = len(result.get("data", {}).get("Get", {}).get("Consultant", []))
        print(f"✓ Verified: {verified_count} total consultants in database")
        
        if verified_count < inserted_count:
            print(f"⚠ Expected {inserted_count} new consultants but found {verified_count} total")
    except Exception as e:
        print(f"WARNING: Could not verify insertion: {e}")
    
    if errors:
        print(f"\n⚠ Completed with {len(errors)} error(s). {inserted_count} consultants inserted.")
        return inserted_count, errors
    else:
        print(f"\n✓ Successfully inserted {inserted_count} consultants into Weaviate")
        return inserted_count, []

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Insert consultants into production Weaviate database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Insert from JSON file
  python seed_production.py --data-file /path/to/consultants.json
  
  # Insert and force even if data exists
  python seed_production.py --data-file consultants.json --force
  
  # Insert from stdin (pipe JSON)
  cat consultants.json | python seed_production.py --stdin
        """
    )
    parser.add_argument(
        "--data-file",
        type=str,
        help="Path to JSON file containing consultant data"
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read consultant data from stdin (JSON array)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Insert consultants even if data already exists"
    )
    args = parser.parse_args()
    
    # Load consultant data
    if args.stdin:
        try:
            consultants = json.load(sys.stdin)
            if not isinstance(consultants, list):
                print("ERROR: JSON input must be an array of consultants")
                sys.exit(1)
            print(f"✓ Loaded {len(consultants)} consultants from stdin")
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON from stdin: {e}")
            sys.exit(1)
    elif args.data_file:
        consultants = load_consultant_data(args.data_file)
    else:
        print("ERROR: Must provide either --data-file or --stdin")
        parser.print_help()
        sys.exit(1)
    
    if not consultants:
        print("ERROR: No consultant data to insert")
        sys.exit(1)
    
    # Connect to Weaviate
    client = connect_to_weaviate()
    if not client:
        sys.exit(1)
    
    # Insert consultants
    try:
        insert_consultants(client, consultants, force=args.force)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

