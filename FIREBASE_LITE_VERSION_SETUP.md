# Firebase Notification Setup for Lite Version - Complete Guide

## 🎯 Overview
This guide will help you set up Firebase Cloud Messaging (FCM) notifications for your **lite version** lottery app, mirroring the same notification system used in your full version.

---

## 📋 Prerequisites

### 1. Firebase Console Setup
1. **Go to Firebase Console**: https://console.firebase.google.com/
2. **Create a New Project** (or use existing)
   - Project Name: `lottery-lite-app` (or your choice)
   - Enable Google Analytics (optional)
   - Click "Create Project"

3. **Add Your Flutter App**
   - Click "Add App" → Select Android (🤖)
   - **Package Name**: Use your lite app's package name (e.g., `com.yourcompany.lottery_lite`)
   - **App Nickname**: "Lottery Lite App"
   - Download `google-services.json`

4. **Enable Cloud Messaging**
   - Go to Project Settings → Cloud Messaging
   - Note down your **Sender ID** and **Server Key**

---

## 🔧 Backend Setup (Django)

### Step 1: Install Firebase Admin SDK (Already Done ✅)
Your main app already has `firebase-admin==6.9.0` installed. Same dependencies work for lite version.

### Step 2: Create Separate Firebase Project for Lite Version

**Option A: Use Same Firebase Project with Different Topics**
- Both apps share same Firebase project
- Use **topics** to differentiate: `full_app` vs `lite_app`
- Users subscribe to relevant topics

**Option B: Create Separate Firebase Project** (Recommended)
- Complete isolation between full and lite versions
- Separate service account JSON file
- Different credentials in environment variables

---

## 🔑 Step 3: Get Firebase Service Account Key

### For Firebase Console:
1. Go to **Project Settings** → **Service Accounts**
2. Click **"Generate New Private Key"**
3. Download the JSON file
4. Save as `firebase-lite-service-account-key.json`

### File Structure:
```json
{
  "type": "service_account",
  "project_id": "lottery-lite-xxxxxx",
  "private_key_id": "xxxxxxxxxxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\nXXXXXXX\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@lottery-lite-xxxxxx.iam.gserviceaccount.com",
  "client_id": "xxxxxxxxxxxxx",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40lottery-lite-xxxxxx.iam.gserviceaccount.com"
}
```

---

## 🗄️ Step 4: Database Models (Copy from Main App)

### Create `FcmToken` model for storing user tokens:

```python
# In your lite app's models.py
from django.db import models
from django.utils import timezone

class FcmToken(models.Model):
    """Store FCM tokens for push notifications"""
    
    phone_number = models.CharField(max_length=15, db_index=True)
    name = models.CharField(max_length=100)
    fcm_token = models.TextField(unique=True)
    notifications_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'fcm_tokens'
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
```

### Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## ⚙️ Step 5: Settings Configuration

### Update `settings.py` for Lite Version:

```python
# settings.py

import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials

BASE_DIR = Path(__file__).resolve().parent.parent

# ... your existing settings ...

def get_firebase_credentials():
    """Get Firebase credentials for LITE version"""
    try:
        # Option 1: Use service account file (development)
        firebase_file = BASE_DIR / 'firebase-lite-service-account-key.json'
        if firebase_file.exists() and not os.getenv('ENVIRONMENT') == 'production':
            return firebase_file
        
        # Option 2: Use environment variables (production)
        firebase_creds = {
            "type": "service_account",
            "project_id": os.environ.get('FIREBASE_LITE_PROJECT_ID'),
            "private_key_id": os.environ.get('FIREBASE_LITE_PRIVATE_KEY_ID'),
            "private_key": os.environ.get('FIREBASE_LITE_PRIVATE_KEY', '').replace('\\\\n', '\\n'),
            "client_email": os.environ.get('FIREBASE_LITE_CLIENT_EMAIL'),
            "client_id": os.environ.get('FIREBASE_LITE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('FIREBASE_LITE_CLIENT_EMAIL')}"
        }
        
        # Validate required fields
        required_fields = ['private_key_id', 'private_key', 'client_email', 'client_id']
        if all(firebase_creds.get(field) for field in required_fields):
            return firebase_creds
        else:
            print("⚠️ Firebase credentials incomplete")
            return None
            
    except Exception as e:
        print(f"❌ Firebase credential error: {e}")
        return None

# Set Firebase credentials
FIREBASE_CREDENTIALS = get_firebase_credentials()

# Initialize Firebase when Django starts
def initialize_firebase():
    """Initialize Firebase Admin SDK for Lite Version"""
    if firebase_admin._apps:
        return  # Already initialized
    
    try:
        firebase_creds = get_firebase_credentials()
        
        if firebase_creds is None:
            print("⚠️ Firebase not initialized - credentials missing")
            return
        
        if isinstance(firebase_creds, Path):
            cred = credentials.Certificate(str(firebase_creds))
            print("🔥 Firebase Lite initialized with service account file")
        else:
            cred = credentials.Certificate(firebase_creds)
            print("🔥 Firebase Lite initialized with environment variables")
        
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Lite initialized successfully")
        
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")

# Initialize Firebase
initialize_firebase()
```

---

## 🚀 Step 6: FCM Service Class

### Create `fcm_service.py` in your lite app:

```python
# fcm_service.py (Use the same as main app, I'll create it below)
```

I'll create this file separately for you in the next step.

---

## 📱 Step 7: Flutter Integration

### 1. Add dependencies in `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # Firebase dependencies
  firebase_core: ^2.24.2
  firebase_messaging: ^14.7.10
  flutter_local_notifications: ^16.3.0
```

### 2. Update `android/app/build.gradle`:

```gradle
dependencies {
    // Firebase
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging'
}
```

### 3. Add `google-services.json` to `android/app/`

### 4. Update `android/build.gradle`:

```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

### 5. In `android/app/build.gradle` (at bottom):

```gradle
apply plugin: 'com.google.gms.google-services'
```

---

## 🔔 Step 8: Flutter Notification Service

### Create `notification_service.dart`:

```dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class NotificationService {
  static final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  static final FlutterLocalNotificationsPlugin _localNotifications = 
      FlutterLocalNotificationsPlugin();
  
  // Initialize notifications
  static Future<void> initialize() async {
    // Request permission
    NotificationSettings settings = await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    
    print('Notification permission: ${settings.authorizationStatus}');
    
    // Initialize local notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    
    await _localNotifications.initialize(initSettings);
    
    // Get FCM token
    String? token = await _firebaseMessaging.getToken();
    print('FCM Token: $token');
    
    if (token != null) {
      // Send token to your backend
      await registerToken(token);
    }
    
    // Listen for token refresh
    _firebaseMessaging.onTokenRefresh.listen((newToken) {
      registerToken(newToken);
    });
    
    // Handle foreground messages
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print('Foreground message: ${message.notification?.title}');
      _showLocalNotification(message);
    });
  }
  
  // Register token with backend
  static Future<void> registerToken(String token) async {
    try {
      final response = await http.post(
        Uri.parse('https://your-api.com/api/fcm-token/register/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'phone_number': 'USER_PHONE_HERE',  // Get from user data
          'name': 'USER_NAME_HERE',            // Get from user data
          'fcm_token': token,
        }),
      );
      
      if (response.statusCode == 200) {
        print('✅ FCM token registered successfully');
      }
    } catch (e) {
      print('❌ Failed to register FCM token: $e');
    }
  }
  
  // Show local notification
  static Future<void> _showLocalNotification(RemoteMessage message) async {
    const androidDetails = AndroidNotificationDetails(
      'default_channel',
      'Default Notifications',
      importance: Importance.high,
      priority: Priority.high,
    );
    
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(android: androidDetails, iOS: iosDetails);
    
    await _localNotifications.show(
      message.hashCode,
      message.notification?.title,
      message.notification?.body,
      details,
    );
  }
}
```

### Initialize in `main.dart`:

```dart
import 'package:firebase_core/firebase_core.dart';
import 'notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase
  await Firebase.initializeApp();
  
  // Initialize notifications
  await NotificationService.initialize();
  
  runApp(MyApp());
}
```

---

## 🌐 Step 9: API Endpoints

### Create views for FCM token management:

```python
# views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import FcmToken

@api_view(['POST'])
def register_fcm_token(request):
    """Register or update FCM token"""
    phone_number = request.data.get('phone_number')
    name = request.data.get('name')
    fcm_token = request.data.get('fcm_token')
    
    if not all([phone_number, name, fcm_token]):
        return Response(
            {'error': 'Missing required fields'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create or update token
    token_obj, created = FcmToken.objects.update_or_create(
        fcm_token=fcm_token,
        defaults={
            'phone_number': phone_number,
            'name': name,
            'is_active': True,
            'notifications_enabled': True
        }
    )
    
    return Response({
        'success': True,
        'message': 'FCM token registered successfully'
    })
```

---

## 🎨 Step 10: Environment Variables (Production)

### Add to your `.env` or hosting platform:

```bash
# Firebase Lite Version Credentials
FIREBASE_LITE_PROJECT_ID=lottery-lite-xxxxxx
FIREBASE_LITE_PRIVATE_KEY_ID=xxxxxxxxxxxxx
FIREBASE_LITE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nXXXXXX\n-----END PRIVATE KEY-----\n"
FIREBASE_LITE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@lottery-lite-xxxxxx.iam.gserviceaccount.com
FIREBASE_LITE_CLIENT_ID=xxxxxxxxxxxxx
```

---

## ✅ Step 11: Testing

### Test notification from Django:

```python
from results.services.fcm_service import FCMService

# Send test notification
result = FCMService.send_result_ready_notification(
    lottery_name="KARUNYA",
    draw_number="KR-123"
)

print(result)
```

### Or use Django Admin to send notifications

---

## 🔄 Step 12: Sharing Code Between Full and Lite Versions

### Option A: Use Same Codebase with Feature Flags

```python
# settings.py
APP_VERSION = os.getenv('APP_VERSION', 'full')  # 'full' or 'lite'

if APP_VERSION == 'lite':
    # Lite-specific Firebase credentials
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_LITE_PROJECT_ID')
else:
    # Full version Firebase credentials
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
```

### Option B: Separate Projects with Shared Code
- Create a shared `fcm_service.py` module
- Import in both full and lite projects
- Use environment variables to differentiate

---

## 🎯 Summary Checklist

- [ ] Create Firebase project for lite version
- [ ] Download `google-services.json` for Flutter
- [ ] Get service account JSON for Django backend
- [ ] Add Firebase dependencies to Flutter app
- [ ] Create `FcmToken` model in Django
- [ ] Configure Firebase in `settings.py`
- [ ] Create `fcm_service.py` (copying from main app)
- [ ] Add FCM registration API endpoint
- [ ] Initialize Firebase in Flutter app
- [ ] Test notifications end-to-end
- [ ] Deploy with environment variables

---

## 🆘 Troubleshooting

### Issue: "Firebase already initialized"
**Solution**: Check if `firebase_admin._apps` exists before initializing

### Issue: "Invalid token"
**Solution**: Ensure token is sent from correct Firebase project

### Issue: "Notifications not received on Flutter"
**Solution**: 
- Check `google-services.json` is in `android/app/`
- Verify package name matches Firebase console
- Test with Firebase Console's "Cloud Messaging" test tool

---

## 📞 Need Help?

If you encounter issues:
1. Check Firebase Console logs
2. Enable verbose logging in Django
3. Test with Firebase's built-in messaging tester
4. Verify credentials are correctly set

---

**Next Steps**: Would you like me to create the complete `fcm_service.py` file for your lite version?
