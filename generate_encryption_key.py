#!/usr/bin/env python3
"""
Utility script to generate a new encryption key for the Chat Nuff Bot.
Run this script to generate a secure encryption key for your .env file.
"""

import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from encryption_utils import generate_key

if __name__ == "__main__":
    key = generate_key()
    print("Generated encryption key:")
    print(key)
    print("\nAdd this to your .env file:")
    print(f"ENCRYPTION_KEY={key}")
    print("ENCRYPTION_ENABLED=True")