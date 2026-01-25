# 📋 Firebase Lite Version - Quick Checklist

## 🎯 COPY THIS - Your To-Do List

### Part 1: Firebase Console (10 min)
- [ ] Go to https://console.firebase.google.com/
- [ ] Create project: "lottery-lite-app"
- [ ] Add Android app (use your package name from Flutter)
- [ ] Download `google-services.json` → Save it
- [ ] Download Service Account Key → Save as `firebase-lite-key.json`

### Part 2: Django Backend (15 min)
- [ ] Copy `fcm_service_lite_version.py` to your lite app
- [ ] Add `FcmToken` model to `models.py`
- [ ] Run: `python manage.py makemigrations`
- [ ] Run: `python manage.py migrate`
- [ ] Add `register_fcm_token` view to `views.py`
- [ ] Add URL route in `urls.py`
- [ ] Put `firebase-lite-key.json` in project root
- [ ] Add Firebase initialization to `settings.py`

### Part 3: Flutter App (20 min)
- [ ] Add dependencies to `pubspec.yaml`:
  - `firebase_core`
  - `firebase_messaging`
  - `flutter_local_notifications`
  - `shared_preferences`
  - `http`
- [ ] Run: `flutter pub get`
- [ ] Copy `google-services.json` to `android/app/`
- [ ] Update `android/build.gradle` (add Google services)
- [ ] Update `android/app/build.gradle` (add Firebase dependencies)
- [ ] Copy `notification_service.dart` to `lib/services/`
- [ ] Update API_BASE_URL in `notification_service.dart`
- [ ] Update `main.dart` to initialize Firebase
- [ ] Call `NotificationService.updateUserInfo()` after login

### Part 4: Test (5 min)
- [ ] Run Flutter app
- [ ] Login with a test user
- [ ] Open Django shell
- [ ] Send test notification
- [ ] Check if notification appears on phone

### Part 5: Production (5 min)
- [ ] Add Firebase key to environment variables (production)
- [ ] Test on real device
- [ ] Test background notifications
- [ ] Test when app is closed

---

## 📝 Quick Copy-Paste Codes

### Django Model (copy to models.py)
```python
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
```

### Django View (copy to views.py)
```python
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
    
    return Response({'success': True})
```

### Django URL (copy to urls.py)
```python
path('api/fcm-token/register/', views.register_fcm_token),
```

### Flutter Dependencies (copy to pubspec.yaml)
```yaml
dependencies:
  firebase_core: ^2.24.2
  firebase_messaging: ^14.7.10
  flutter_local_notifications: ^16.3.0
  shared_preferences: ^2.2.2
  http: ^1.1.0
```

### Flutter Main (copy to main.dart)
```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  await NotificationService.initialize();
  runApp(MyApp());
}
```

### Send Notification (Django)
```python
from .services.fcm_service import FCMLiteService

FCMLiteService.send_new_result_notification(
    lottery_name="KARUNYA"
)
```

---

## ⏱️ Time Estimate
- **Total Time**: ~60 minutes
- **Backend**: 15 min
- **Flutter**: 25 min
- **Testing**: 10 min
- **Setup**: 10 min

---

## 🔥 You're Done When...
✅ Flutter app receives notification
✅ Backend can send notifications
✅ User tokens are stored in database
✅ Login flow registers FCM token

---

## 📂 Files You'll Have

**In Django Project:**
```
your_lite_app/
├── models.py (+ FcmToken)
├── views.py (+ register_fcm_token)
├── urls.py (+ fcm-token endpoint)
├── settings.py (+ Firebase init)
└── services/
    └── fcm_service.py (copy from fcm_service_lite_version.py)

Root:
└── firebase-lite-key.json (from Firebase Console)
```

**In Flutter Project:**
```
lib/
├── main.dart (updated)
└── services/
    └── notification_service.dart (new file)

android/
├── build.gradle (updated)
└── app/
    ├── build.gradle (updated)
    └── google-services.json (from Firebase Console)

pubspec.yaml (updated dependencies)
```

---

## 🎊 Success!
Once all checkboxes are ✅, your lite app will have the same notification system as your full app!
