# Firebase Notifications - Flutter Developer Guide
## Lite Version Setup

---

## 📦 What Backend Has Done

✅ **Firebase Project Created**: `lotto-lite` (separate from full version)
✅ **Database Ready**: Backend stores FCM tokens with `app_version` field
✅ **API Endpoint Ready**: `/api/fcm/register/` accepts token registration
✅ **Notification Service**: Backend can send notifications to lite app users

---

## 📥 Files You Need from Backend Team

### 1. **google-services.json** 
- Download from Firebase Console: https://console.firebase.google.com/
- Project: **lotto-lite**
- Go to: Project Settings → Your Apps → Android → Download `google-services.json`
- Put in: `android/app/google-services.json`

**OR** Backend team can provide this file directly.

---

## ⚙️ Flutter Configuration Needed

### 1. **Add to `pubspec.yaml`**
```yaml
dependencies:
  firebase_core: ^2.24.2
  firebase_messaging: ^14.7.10
```

### 2. **Update `android/build.gradle`**
```gradle
dependencies {
    classpath 'com.google.gms:google-services:4.4.0'
}
```

### 3. **Update `android/app/build.gradle`**
Add at bottom:
```gradle
apply plugin: 'com.google.gms.google-services'
```

### 4. **Initialize Firebase in `main.dart`**
```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(MyApp());
}
```

---

## 🔌 API Integration

### **Register FCM Token**

**Endpoint:** `POST /api/fcm/register/`

**Request Body:**
```json
{
  "fcm_token": "user_fcm_token_from_firebase",
  "phone_number": "9876543210",
  "name": "User Name",
  "app_version": "lite"
}
```

⚠️ **IMPORTANT**: Must send `"app_version": "lite"` - this identifies lite app users

**Success Response:**
```json
{
  "status": "success",
  "message": "FCM token registered successfully",
  "user_id": 123,
  "phone_number": "9876543210"
}
```

---

## 🎯 Essential Implementation Steps

### **Step 1: Get FCM Token**
After Firebase initialization, get the device token:
```dart
final fcmToken = await FirebaseMessaging.instance.getToken();
```

### **Step 2: Register with Backend**
Send token to backend immediately after user login/signup:
```dart
// After user logs in successfully
final response = await http.post(
  Uri.parse('https://your-backend-url/api/fcm/register/'),
  body: {
    'fcm_token': fcmToken,
    'phone_number': userPhone,
    'name': userName,
    'app_version': 'lite',  // ← MUST INCLUDE THIS
  },
);
```

### **Step 3: Handle Notifications**
Set up listeners for incoming notifications:
```dart
// Foreground
FirebaseMessaging.onMessage.listen((message) {
  // Show notification
});

// Background
FirebaseMessaging.onBackgroundMessage(handler);
```

---

## ✅ Verification Checklist

Before testing, ensure:

- [ ] `google-services.json` is in `android/app/`
- [ ] Firebase initialized in `main.dart`
- [ ] FCM token obtained after initialization
- [ ] Token sent to backend with `app_version: "lite"`
- [ ] Package name in `google-services.json` matches your app
- [ ] Background message handler configured

---

## 🧪 Testing

### **Test 1: Token Registration**
1. Run app, login
2. Check backend database - should see your token with `app_version='lite'`

### **Test 2: Receive Notification**
Ask backend team to send test notification:
```python
# Backend sends this
FCMService.send_custom_notification(
    title="Test",
    body="Lite version notification test"
)
```

Should receive notification on device.

---

## 🔑 Key Points

1. **app_version is REQUIRED**: Must be `"lite"` for lite app
2. **Separate Firebase Project**: Lite uses different Firebase than full version
3. **google-services.json**: Must be from `lotto-lite` project, not main project
4. **Package Name**: Must match what's in Firebase Console

---

## 📞 Backend API Base URL

**Development:** `http://localhost:8000`
**Production:** `https://your-production-url.com`

Update as needed.

---

## ❓ Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| No notifications received | Check if token registered in backend DB |
| Wrong Firebase project | Verify `google-services.json` is from `lotto-lite` |
| Token registration fails | Check API endpoint URL and request format |
| Notifications go to full app | Ensure sending `app_version: "lite"` |

---

**That's it!** Backend is ready. Just configure Firebase in Flutter and register tokens with `app_version: "lite"`.
