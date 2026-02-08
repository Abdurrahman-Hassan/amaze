#!/usr/bin/env python3
"""
Generate a secure API key for your QR Code Microservice
Run this script to generate a random API key
"""

import secrets

print("=" * 60)
print("🔑 API Key Generator for QR Code Microservice")
print("=" * 60)
print()

# Generate a secure random API key
api_key = secrets.token_urlsafe(32)

print("Your new API key:")
print()
print(f"  {api_key}")
print()
print("=" * 60)
print()
print("📋 Next Steps:")
print()
print("1. For LOCAL testing:")
print(f"   - Open .env file")
print(f"   - Replace: API_KEY=your-api-key-here")
print(f"   - With: API_KEY={api_key}")
print()
print("2. For APPWRITE deployment:")
print("   - Go to Appwrite Console")
print("   - Functions → Your Function → Settings")
print("   - Environment Variables → Add Variable")
print(f"   - Key: API_KEY")
print(f"   - Value: {api_key}")
print("   - Redeploy your function")
print()
print("⚠️  IMPORTANT: Keep this key secret!")
print("   - Don't commit to Git")
print("   - Don't share in public")
print("   - Rotate every 3-6 months")
print()
print("=" * 60)
