#!/usr/bin/env python3
"""
Setup script for VIT Exam Paper Processing Tool
Handles initial configuration and directory setup
"""

import os
import sys
import shutil
from pathlib import Path


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(text):
    print(f"✓ {text}")


def print_error(text):
    print(f"✗ {text}")


def print_info(text):
    print(f"ℹ {text}")


def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    print_header("Environment Setup")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        print_info(".env already exists - skipping")
        return True
    
    if not env_example.exists():
        print_error(".env.example not found!")
        return False
    
    try:
        shutil.copy(env_example, env_file)
        print_success(".env created from .env.example")
        print_info("Edit .env to add your API keys (if needed)")
        return True
    except Exception as e:
        print_error(f"Failed to create .env: {e}")
        return False


def create_directories():
    """Create required directories"""
    print_header("Creating Directories")
    
    dirs = [
        "backend/ai/agent/data/raw_papers",
        "backend/ai/agent/data/cache",
        "backend/ai/agent/outputs",
        "backend/ai/agent/outputs/analysis",
        "backend/ai/agent/logs",
    ]
    
    for dir_path in dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print_success(f"Created: {dir_path}")
        except Exception as e:
            print_error(f"Failed to create {dir_path}: {e}")
            return False
    
    return True


def check_gitignore():
    """Verify .gitignore properly excludes .env"""
    print_header("Verifying Git Configuration")
    
    gitignore = Path(".gitignore")
    
    if not gitignore.exists():
        print_error(".gitignore not found!")
        return False
    
    with open(gitignore, 'r') as f:
        content = f.read()
    
    if ".env" in content:
        print_success(".gitignore properly excludes .env file")
        return True
    else:
        print_error(".env not found in .gitignore!")
        print_info("Add '.env' to .gitignore manually")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    required = [
        "requests",
        "beautifulsoup4",
        "pdfplumber",
        "fitz",
        "PIL",
        "pytesseract",
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is NOT installed")
            missing.append(package)
    
    if missing:
        print("\n" + "!" * 60)
        print("To install missing packages, run:")
        print(f"  pip install -r requirements.txt")
        print("!" * 60)
        return False
    
    return True


def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     VIT Exam Paper Processing Tool - Setup Script         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    steps = [
        ("Create directories", create_directories),
        ("Setup environment (.env)", create_env_file),
        ("Verify .gitignore", check_gitignore),
        ("Check dependencies", check_dependencies),
    ]
    
    results = []
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print_error(f"Error in {step_name}: {e}")
            results.append((step_name, False))
    
    # Summary
    print_header("Setup Summary")
    
    all_success = True
    for step_name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {step_name}")
        if not result:
            all_success = False
    
    if all_success:
        print_header("✓ Setup Complete!")
        print("\nNext steps:")
        print("1. Review and edit .env (add API keys if needed)")
        print("2. Run: python main_demo.py")
        print("3. Choose option 3 to scrape papers")
        print("4. Choose option 4 to extract questions")
        print("\nFor more details, see: QUICK_START.md")
        return 0
    else:
        print_header("⚠ Setup Incomplete")
        print("\nPlease fix the issues above and run setup again.")
        print("For help, see README.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
