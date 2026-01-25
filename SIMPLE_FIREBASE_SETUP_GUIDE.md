# 🚀 Simple Firebase Setup for Lite Version - Step by Step

## ✅ What You Need to Do (5 Easy Steps)

---

### **STEP 1: Firebase Console Setup (10 minutes)**

#### 1.1 Create Firebase Project
1. Go to: https://console.firebase.google.com/
2. Click **"Add project"** or **"Create a project"**
3. Enter name: `lottery-lite-app` (or anything you want)
4. Click Continue → Continue → Create Project

#### 1.2 Add Android App
1. Click **Android icon** (🤖)
2. **Package name**: Use your Flutter app's package name
   - Find it in: `android/app/build.gradle` 
   - Look for: `applicationId "com.yourcompany.lottery_lite"`
   - Copy and paste it
3. Click **"Register app"**
4. **Download** `google-services.json`
5. Save it (we'll use it in Step 3)

#### 1.3 Get Service Account Key (For Backend)
1. Click **⚙️ Settings** (top left) → **Project settings**
2. Go to **"Service accounts"** tab
3. Click **"Generate new private key"**
4. Click **"Generate key"** → A JSON file downloads
5. Rename it to: `firebase-lite-key.json`
6. **Keep it safe!** (Don't share publicly)

✅ **Step 1 Done!** You now have:
- `google-services.json` (for Flutter)
- `firebase-lite-key.json` (for Django backend)

---

### **STEP 2: Django Backend Setup (15 minutes)**

#### 2.1 Copy the FCM Service File
```bash
# Copy the fcm_service_lite_version.py file to your lite app
cp fcm_service_lite_version.py /path/to/your/lite_app/services/fcm_service.py
```

#### 2.2 Add the Model to Your Django App
Add this to your `models.py`:

```python
from django.db import models
from django.utils import timezone

class FcmToken(models.Model):
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

#### 2.3 Create the Database Table
```bash
python manage.py makemigrations
python manage.py migrate
```

#### 2.4 Add API Endpoint for Token Registration
Add this to your `views.py`:

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import FcmToken

@api_view(['POST'])
def register_fcm_token(request):
    phone = request.data.get('phone_number')
    name = request.data.get('name')
    token = request.data.get('fcm_token')
    
    if not all([phone, name, token]):
        return Response({'error': 'Missing fields'}, status=400)
    
    FcmToken.objects.update_or_create(
        fcm_token=token,
        defaults={'phone_number': phone, 'name': name, 'is_active': True}
    )
    
    return Response({'success': True, 'message': 'Token registered'})
```

Add to `urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path('api/fcm-token/register/', views.register_fcm_token),
    # ... your other URLs
]
```

#### 2.5 Setup Firebase in Settings
Add this to your `settings.py`:

```python
import firebase_admin
from firebase_admin import credentials
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Put your firebase-lite-key.json in the project root
FIREBASE_KEY_PATH = BASE_DIR / 'firebase-lite-key.json'

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(str(FIREBASE_KEY_PATH))
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized")
```

✅ **Step 2 Done!** Backend is ready to send notifications!

---

### **STEP 3: Flutter App Setup (20 minutes)**

#### 3.1 Add Dependencies
Open `pubspec.yaml` and add:

```yaml
dependencies:
  firebase_core: ^2.24.2
  firebase_messaging: ^14.7.10
  flutter_local_notifications: ^16.3.0
  shared_preferences: ^2.2.2
  http: ^1.1.0
```

Run:
```bash
flutter pub get
```

#### 3.2 Add google-services.json
1. Copy the `google-services.json` (from Step 1.2)
2. Paste it in: `android/app/google-services.json`

#### 3.3 Update Android Files

**File 1: `android/build.gradle`**
Add this inside `dependencies`:
```gradle
dependencies {
    classpath 'com.google.gms:google-services:4.4.0'  // ADD THIS LINE
    // ... other dependencies
}
```

**File 2: `android/app/build.gradle`**
Add at the **bottom** of the file:
```gradle
apply plugin: 'com.google.gms.google-services'  // ADD THIS LINE
```

Also add inside `dependencies`:
```gradle
dependencies {
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging'
}
```

#### 3.4 Copy the Notification Service
1. Copy `flutter_notification_service_lite.dart`
2. Put it in your Flutter project: `lib/services/notification_service.dart`
3. **Update line 16** with your backend URL:
   ```dart
   static const String API_BASE_URL = 'https://your-backend-url.com';
   ```

#### 3.5 Update main.dart
Replace your `main.dart` with this:

```dart
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase
  await Firebase.initializeApp();
  
  // Initialize Notifications
  await NotificationService.initialize();
  
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lottery Lite',
      home: HomeScreen(),
    );
  }
}

class HomeScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Lottery Lite')),
      body: Center(
        child: Text('App is ready to receive notifications!'),
      ),
    );
  }
}
```

#### 3.6 After User Login, Register Token
When user logs in, call:

```dart
import 'services/notification_service.dart';

// After successful login:
await NotificationService.updateUserInfo(
  phoneNumber,  // User's phone number
  userName,     // User's name
);
```

✅ **Step 3 Done!** Flutter app can now receive notifications!

---

### **STEP 4: Test Everything (5 minutes)**

#### 4.1 Test from Django Shell
```bash
python manage.py shell
```

Then run:
```python
from your_app.services.fcm_service import FCMLiteService

# Send test notification
result = FCMLiteService.send_custom_notification(
    title="🎉 Test Notification",
    body="If you see this, it works!"
)

print(result)
```

#### 4.2 Check Flutter App
- Open your Flutter app
- You should see the notification!

✅ **Step 4 Done!** Notifications are working!

---

### **STEP 5: Send Notifications in Your App (2 minutes)**

#### Example 1: Send When New Result is Added
In your Django views:

```python
from .services.fcm_service import FCMLiteService

# When you publish a new lottery result:
def publish_result(request):
    # ... your code to save result ...
    
    # Send notification
    FCMLiteService.send_new_result_notification(
        lottery_name="KARUNYA"
    )
    
    return Response({'success': True})
```

#### Example 2: Send Custom Notification
```python
FCMLiteService.send_custom_notification(
    title="🎊 Special Offer!",
    body="New prediction available now!"
)
```

✅ **Step 5 Done!** You're all set!

---

## 🎯 Quick Summary

**What you did:**
1. ✅ Created Firebase project + downloaded 2 files
2. ✅ Added model + API endpoint in Django
3. ✅ Added Firebase to Flutter app
4. ✅ Tested notifications
5. ✅ Send notifications when needed

**Files you created/modified:**
- Django: `models.py`, `views.py`, `urls.py`, `settings.py`
- Flutter: `pubspec.yaml`, `main.dart`, added `notification_service.dart`
- Android: `build.gradle` (2 files), added `google-services.json`

---

## 🆘 Common Issues

### Issue 1: "Firebase not initialized"
**Fix:** Make sure `firebase-lite-key.json` is in your Django project root

### Issue 2: "No notifications received in Flutter"
**Fix:** 
- Check if `google-services.json` is in `android/app/`
- Check if package name matches Firebase console
- Rebuild the app: `flutter clean && flutter run`

### Issue 3: "Token not registered"
**Fix:** Make sure user is logged in and `updateUserInfo()` was called

---

## 📞 Need Help?

If stuck, check:
1. Django logs: `python manage.py runserver` (look for errors)
2. Flutter logs: `flutter run` (look for FCM token)
3. Firebase Console → Cloud Messaging → Send test message

---

## 🎉 That's It!

You now have Firebase notifications working in both:
- ✅ Your **full version** app (already working)
- ✅ Your **lite version** app (just set up)

Both can send notifications independently!
