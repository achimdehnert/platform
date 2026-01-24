#!/usr/bin/env python
"""Object Creator - Create files, directories, and more from JSON specification"""
import json
import os
import sys
import shutil
from pathlib import Path


class ObjectCreator:
    """Create various types of objects from JSON specification"""
    
    def __init__(self):
        self.stats = {
            'files': 0,
            'directories': 0,
            'symlinks': 0,
            'errors': 0
        }
    
    def create_from_json(self, json_path):
        """
        Create objects from JSON specification
        
        JSON Format:
        {
            "objects": [
                {
                    "type": "file",
                    "path": "path/to/file.py",
                    "content": "file content"
                },
                {
                    "type": "directory",
                    "path": "path/to/dir"
                },
                {
                    "type": "symlink",
                    "path": "link/path",
                    "target": "target/path"
                }
            ]
        }
        
        Legacy format also supported:
        {
            "files": [{"path": "...", "content": "..."}]
        }
        """
        # Read JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both 'objects' and legacy 'files' format
        objects = data.get('objects', [])
        if not objects and 'files' in data:
            # Convert legacy format
            objects = [{'type': 'file', **f} for f in data['files']]
        
        if not objects:
            print("❌ No objects found in JSON")
            return
        
        print(f"\n🚀 Creating {len(objects)} objects...\n")
        
        for obj_spec in objects:
            obj_type = obj_spec.get('type', 'file').lower()
            
            if obj_type == 'file':
                self._create_file(obj_spec)
            elif obj_type == 'directory':
                self._create_directory(obj_spec)
            elif obj_type == 'symlink':
                self._create_symlink(obj_spec)
            else:
                print(f"⚠️  Unknown type: {obj_type}")
                self.stats['errors'] += 1
        
        self._print_summary()
    
    def _create_file(self, spec):
        """Create a file"""
        file_path = spec.get('path')
        content = spec.get('content', '')
        
        if not file_path:
            print("⚠️  Skipping file without path")
            self.stats['errors'] += 1
            return
        
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ File: {path}")
            self.stats['files'] += 1
            
        except Exception as e:
            print(f"❌ Error creating file {file_path}: {e}")
            self.stats['errors'] += 1
    
    def _create_directory(self, spec):
        """Create a directory"""
        dir_path = spec.get('path')
        
        if not dir_path:
            print("⚠️  Skipping directory without path")
            self.stats['errors'] += 1
            return
        
        try:
            path = Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
            
            print(f"📁 Directory: {path}")
            self.stats['directories'] += 1
            
        except Exception as e:
            print(f"❌ Error creating directory {dir_path}: {e}")
            self.stats['errors'] += 1
    
    def _create_symlink(self, spec):
        """Create a symbolic link"""
        link_path = spec.get('path')
        target = spec.get('target')
        
        if not link_path or not target:
            print("⚠️  Skipping symlink without path or target")
            self.stats['errors'] += 1
            return
        
        try:
            path = Path(link_path)
            target_path = Path(target)
            
            # Create parent directory
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove existing symlink if exists
            if path.exists() or path.is_symlink():
                path.unlink()
            
            # Create symlink
            path.symlink_to(target_path)
            
            print(f"🔗 Symlink: {path} → {target}")
            self.stats['symlinks'] += 1
            
        except Exception as e:
            print(f"❌ Error creating symlink {link_path}: {e}")
            self.stats['errors'] += 1
    
    def _print_summary(self):
        """Print creation summary"""
        print(f"\n📊 Summary:")
        print(f"   📄 Files: {self.stats['files']}")
        print(f"   📁 Directories: {self.stats['directories']}")
        print(f"   🔗 Symlinks: {self.stats['symlinks']}")
        print(f"   ❌ Errors: {self.stats['errors']}")
        total = sum(self.stats.values()) - self.stats['errors']
        print(f"   ✅ Total: {total}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_needed.py <json_file>")
        print("\nExample JSON format:")
        print(json.dumps({
            "objects": [
                {
                    "type": "file",
                    "path": "example/file.py",
                    "content": "print('Hello World')"
                },
                {
                    "type": "directory",
                    "path": "example/subdir"
                },
                {
                    "type": "symlink",
                    "path": "link/to/file",
                    "target": "example/file.py"
                }
            ]
        }, indent=2))
        print("\nLegacy format also supported:")
        print(json.dumps({
            "files": [
                {"path": "file.py", "content": "..."}
            ]
        }, indent=2))
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        sys.exit(1)
    
    creator = ObjectCreator()
    creator.create_from_json(json_file)