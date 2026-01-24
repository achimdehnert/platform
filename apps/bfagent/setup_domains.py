"""
Setup Domain Structure for BF Agent
Creates folders and __init__.py files for domain-based architecture
"""
import os
from pathlib import Path

# Base path
BASE = Path("apps/bfagent/domains")

# Domain structure
STRUCTURE = {
    "book_writing": {
        "views": ["__init__.py", "project_views.py", "chapter_views.py", "character_views.py", "essay_views.py"],
        "handlers": ["__init__.py"],
    },
    "science_writer": {
        "views": ["__init__.py", "research_views.py", "paper_views.py"],
        "handlers": ["__init__.py"],
    },
    "expert_hub": {
        "views": ["__init__.py", "report_views.py", "forensic_views.py"],
        "handlers": ["__init__.py"],
    },
    "workflow_engine": {
        "views": ["__init__.py", "handler_views.py", "handler_generator_views.py"],
    },
    "control_center": {
        "general": ["__init__.py", "dashboard_views.py"],
        "general_writing": ["__init__.py", "booktype_views.py"],
        "general_medtrans": ["__init__.py"],
        "master_data": ["__init__.py", "agent_views.py"],
    },
}

def create_structure():
    """Create all folders and files"""
    print("🚀 Creating Domain Structure...")
    
    # Create base domains folder
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "__init__.py").touch()
    print(f"✅ Created: {BASE}")
    
    # Create domain structures
    for domain, structure in STRUCTURE.items():
        domain_path = BASE / domain
        domain_path.mkdir(exist_ok=True)
        (domain_path / "__init__.py").touch()
        print(f"✅ Created domain: {domain}")
        
        for folder, files in structure.items():
            folder_path = domain_path / folder
            folder_path.mkdir(exist_ok=True)
            print(f"  📁 Created: {folder}/")
            
            for file in files:
                file_path = folder_path / file
                if not file_path.exists():
                    file_path.touch()
                    print(f"    📄 Created: {file}")
    
    print("\n🎉 Domain structure created successfully!")
    print(f"\n📊 Summary:")
    print(f"  Domains: {len(STRUCTURE)}")
    print(f"  Folders created: {sum(len(s) for s in STRUCTURE.values())}")
    print(f"  Files created: {sum(len(files) for s in STRUCTURE.values() for files in s.values())}")

if __name__ == "__main__":
    create_structure()
