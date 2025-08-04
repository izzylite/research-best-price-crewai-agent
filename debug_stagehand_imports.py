#!/usr/bin/env python3
"""
Debug script to understand the correct Stagehand imports and API.
"""

import os
import sys
import inspect

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def explore_stagehand_package():
    """Explore the stagehand package structure."""
    print("🔍 Exploring stagehand package structure...")
    
    try:
        import stagehand
        print(f"✅ stagehand package imported from: {stagehand.__file__}")
        print(f"📦 stagehand package contents: {dir(stagehand)}")
        
        # Try to find the main classes
        for attr_name in dir(stagehand):
            if not attr_name.startswith('_'):
                try:
                    attr = getattr(stagehand, attr_name)
                    if inspect.isclass(attr):
                        print(f"🏗️ Found class: {attr_name} -> {attr}")
                    elif inspect.ismodule(attr):
                        print(f"📁 Found module: {attr_name} -> {attr}")
                        # Explore submodules
                        for sub_attr_name in dir(attr):
                            if not sub_attr_name.startswith('_'):
                                sub_attr = getattr(attr, sub_attr_name)
                                if inspect.isclass(sub_attr):
                                    print(f"  🏗️ Subclass: {sub_attr_name} -> {sub_attr}")
                except Exception as e:
                    print(f"❌ Error exploring {attr_name}: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import stagehand: {e}")
        return False

def try_different_imports():
    """Try different import patterns to find the correct API."""
    print("\n🧪 Trying different import patterns...")
    
    import_patterns = [
        # Pattern 1: Direct import
        ("from stagehand import Stagehand", "stagehand", "Stagehand"),
        
        # Pattern 2: From client module
        ("from stagehand.client import Stagehand", "stagehand.client", "Stagehand"),
        
        # Pattern 3: From base module
        ("from stagehand.base import Stagehand", "stagehand.base", "Stagehand"),
        
        # Pattern 4: Different class name
        ("from stagehand import StagehandClient", "stagehand", "StagehandClient"),
        
        # Pattern 5: From main module
        ("from stagehand.main import Stagehand", "stagehand.main", "Stagehand"),
    ]
    
    successful_imports = []
    
    for pattern_desc, module_name, class_name in import_patterns:
        try:
            print(f"🔄 Trying: {pattern_desc}")
            
            # Import the module
            module = __import__(module_name, fromlist=[class_name])
            
            # Get the class
            cls = getattr(module, class_name)
            
            print(f"✅ Success: {pattern_desc}")
            print(f"   Class: {cls}")
            print(f"   Methods: {[m for m in dir(cls) if not m.startswith('_')]}")
            
            successful_imports.append((pattern_desc, cls))
            
        except ImportError as e:
            print(f"❌ Failed: {pattern_desc} - ImportError: {e}")
        except AttributeError as e:
            print(f"❌ Failed: {pattern_desc} - AttributeError: {e}")
        except Exception as e:
            print(f"❌ Failed: {pattern_desc} - {type(e).__name__}: {e}")
    
    return successful_imports

def try_schemas_import():
    """Try to find the schemas module."""
    print("\n🔍 Looking for schemas module...")
    
    schema_patterns = [
        "stagehand.schemas",
        "stagehand.types",
        "stagehand.models",
        "stagehand.config",
    ]
    
    for pattern in schema_patterns:
        try:
            print(f"🔄 Trying: {pattern}")
            module = __import__(pattern, fromlist=[''])
            print(f"✅ Success: {pattern}")
            print(f"   Contents: {[attr for attr in dir(module) if not attr.startswith('_')]}")
            
            # Look for AvailableModel or similar
            for attr_name in dir(module):
                if 'model' in attr_name.lower() or 'available' in attr_name.lower():
                    attr = getattr(module, attr_name)
                    print(f"   🎯 Found: {attr_name} -> {attr}")
                    
        except ImportError as e:
            print(f"❌ Failed: {pattern} - {e}")
        except Exception as e:
            print(f"❌ Failed: {pattern} - {type(e).__name__}: {e}")

def check_package_version():
    """Check the installed package version."""
    print("\n📋 Checking package version...")
    
    try:
        import stagehand
        if hasattr(stagehand, '__version__'):
            print(f"📦 stagehand version: {stagehand.__version__}")
        else:
            print("❓ Version not found in package")
            
        # Try to get version from pip
        import subprocess
        result = subprocess.run(['pip', 'show', 'stagehand-py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    print(f"📦 pip shows stagehand-py version: {line.split(':', 1)[1].strip()}")
                    break
                    
    except Exception as e:
        print(f"❌ Error checking version: {e}")

def main():
    """Main function."""
    print("🔧 Stagehand Import Debug Tool")
    print("=" * 50)
    
    # Check package version
    check_package_version()
    
    # Explore package structure
    package_exists = explore_stagehand_package()
    
    if package_exists:
        # Try different import patterns
        successful_imports = try_different_imports()
        
        # Try to find schemas
        try_schemas_import()
        
        print("\n" + "=" * 50)
        print("📊 Summary:")
        if successful_imports:
            print("✅ Successful imports:")
            for pattern, cls in successful_imports:
                print(f"   {pattern}")
        else:
            print("❌ No successful imports found")
    else:
        print("❌ Cannot proceed - stagehand package not available")

if __name__ == "__main__":
    main()
