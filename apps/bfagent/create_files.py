#!/usr/bin/env python
"""File Creator - Create multiple files from JSON specification"""
import json
import os
import sys
from pathlib import Path


def create_files_from_json(json_path):
    """
    Create files from JSON specification
    
    JSON Format:
    {
        "files": [
            {
                "path": "relative/or/absolute/path/to/file.py",
                "content": "file content here"
            }
        ]
    }
    """
    # Read JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    files = data.get('files', [])
    
    if not files:
        print("❌ No files found in JSON")
        return
    
    created_count = 0
    error_count = 0
    
    print(f"\n🚀 Creating {len(files)} files...\n")
    
    for file_spec in files:
        file_path = file_spec.get('path')
        content = file_spec.get('content', '')
        
        if not file_path:
            print(f"⚠️  Skipping entry without path")
            error_count += 1
            continue
        
        try:
            # Convert to Path object
            path = Path(file_path)
            
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Created: {path}")
            created_count += 1
            
        except Exception as e:
            print(f"❌ Error creating {file_path}: {e}")
            error_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Created: {created_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📁 Total: {len(files)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_files.py <json_file>")
        print("\nExample JSON format:")
        print(json.dumps({
            "files": [
                {
                    "path": "example/file.py",
                    "content": "print('Hello World')"
                }
            ]
        }, indent=2))
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        sys.exit(1)
    
    create_files_from_json(json_file)