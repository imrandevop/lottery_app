#!/usr/bin/env python
"""
Test Firebase Lite Version Setup
Run this to verify your Firebase lite credentials work
"""

import os
import sys
import django

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set APP_VERSION to 'lite' for testing
os.environ['APP_VERSION'] = 'lite'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kerala_lottery_project.settings')

django.setup()

from firebase_admin import credentials
import firebase_admin
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    # Clear any existing Firebase app
    if firebase_admin._apps:
        del firebase_admin._apps[firebase_admin._DEFAULT_APP_NAME]
    
    # Load lite credentials
    firebase_file = BASE_DIR / 'lotto-lite-firebase-adminsdk-fbsvc-ddad6470de.json'
    
    if firebase_file.exists():
        print(f"✅ Found Firebase lite credentials: {firebase_file.name}")
        
        # Initialize Firebase
        cred = credentials.Certificate(str(firebase_file))
        firebase_admin.initialize_app(cred)
        
        print("✅ Firebase LITE version initialized successfully!")
        print(f"📱 Project ID: lotto-lite")
        
        # Try sending a test notification
        print("\n🧪 Testing notification service...")
        from results.services.fcm_service import FCMService
        
        # Check if there are any tokens
        from results.models import FcmToken
        token_count = FcmToken.objects.filter(is_active=True).count()
        
        print(f"📊 Found {token_count} active FCM tokens")
        
        if token_count > 0:
            print("\n🚀 Sending test notification to all users...")
            result = FCMService.send_custom_notification(
                title="🎉 Lite Version Test",
                body="Firebase notifications are working for Lite version!"
            )
            print(f"✅ Result: {result}")
        else:
            print("⚠️  No FCM tokens found. Register a token from Flutter app first.")
        
    else:
        print(f"❌ Firebase lite credentials not found at: {firebase_file}")
        print("Make sure the file exists in the project root")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
