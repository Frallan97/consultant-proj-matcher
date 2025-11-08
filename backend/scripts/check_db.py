#!/usr/bin/env python3
"""
Check Weaviate database status - schema and data.
Can be run locally or in production to diagnose database issues.
"""
import weaviate
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Default to weaviate service name for Docker Compose, fallback to localhost for local dev
weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080")

print(f"Connecting to Weaviate at {weaviate_url}")
print("=" * 60)

try:
    client = weaviate.Client(url=weaviate_url)
    
    # Check if Weaviate is ready
    try:
        ready = client.is_ready()
        print(f"Weaviate is ready: {ready}")
    except Exception as e:
        print(f"Error checking Weaviate readiness: {e}")
        sys.exit(1)
    
    # Get schema
    print("\n" + "=" * 60)
    print("SCHEMA STATUS")
    print("=" * 60)
    try:
        schema = client.schema.get()
        classes = schema.get("classes", [])
        class_names = [c["class"] for c in classes]
        
        print(f"Total classes found: {len(classes)}")
        print(f"Class names: {class_names}")
        
        # Check for Consultant class
        if "Consultant" in class_names:
            print("\n✓ Consultant class EXISTS")
            consultant_class = next((c for c in classes if c["class"] == "Consultant"), None)
            if consultant_class:
                print(f"  Properties: {[p['name'] for p in consultant_class.get('properties', [])]}")
        else:
            print("\n✗ Consultant class DOES NOT EXIST")
        
        # Check for Resume class
        if "Resume" in class_names:
            print("\n✓ Resume class EXISTS")
        else:
            print("\n✗ Resume class DOES NOT EXIST")
            
    except Exception as e:
        print(f"Error getting schema: {e}")
        sys.exit(1)
    
    # Check data
    print("\n" + "=" * 60)
    print("DATA STATUS")
    print("=" * 60)
    
    if "Consultant" in class_names:
        try:
            # Count consultants
            result = (
                client.query
                .aggregate("Consultant")
                .with_meta_count()
                .do()
            )
            
            if "data" in result and "Aggregate" in result["data"]:
                aggregate = result["data"]["Aggregate"]
                if "Consultant" in aggregate and len(aggregate["Consultant"]) > 0:
                    count = aggregate["Consultant"][0].get("meta", {}).get("count", 0)
                    print(f"✓ Found {count} consultant(s) in database")
                else:
                    print("✗ No consultants found in database")
            else:
                print("✗ Could not count consultants")
            
            # Get a few sample consultants
            try:
                sample = (
                    client.query
                    .get("Consultant", ["name", "email", "skills"])
                    .with_limit(5)
                    .do()
                )
                
                if "data" in sample and "Get" in sample["data"] and "Consultant" in sample["data"]["Get"]:
                    consultants = sample["data"]["Get"]["Consultant"]
                    if consultants:
                        print(f"\nSample consultants (showing up to 5):")
                        for i, consultant in enumerate(consultants, 1):
                            name = consultant.get("name", "Unknown")
                            email = consultant.get("email", "N/A")
                            skills = consultant.get("skills", [])
                            print(f"  {i}. {name} ({email}) - Skills: {len(skills)}")
                    else:
                        print("\nNo consultants found in sample query")
                else:
                    print("\nCould not retrieve sample consultants")
            except Exception as e:
                print(f"\nError getting sample consultants: {e}")
                
        except Exception as e:
            print(f"Error checking consultant data: {e}")
    else:
        print("Cannot check data - Consultant class does not exist")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if "Consultant" in class_names:
        print("✓ Schema is initialized")
        try:
            result = (
                client.query
                .aggregate("Consultant")
                .with_meta_count()
                .do()
            )
            if "data" in result and "Aggregate" in result["data"]:
                aggregate = result["data"]["Aggregate"]
                if "Consultant" in aggregate and len(aggregate["Consultant"]) > 0:
                    count = aggregate["Consultant"][0].get("meta", {}).get("count", 0)
                    print(f"✓ Database has {count} consultant(s)")
                else:
                    print("✗ Database has 0 consultants")
        except:
            print("? Could not determine consultant count")
    else:
        print("✗ Schema is NOT initialized - run init_weaviate.py")
    
    print("=" * 60)
    
except Exception as e:
    print(f"Error connecting to Weaviate: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


