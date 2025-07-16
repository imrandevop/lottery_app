# users/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import UserRegistrationSerializer, UserLoginSerializer, FCMTokenSerializer, UserNotificationPreferencesSerializer
from .models import User
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
import logging
logger = logging.getLogger('lottery_app')




class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'phone_number': user.phone_number,
                'name': user.name,
                'message': 'Registration successful'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            user = User.objects.get(phone_number=phone_number)
            return Response({
                'phone_number': user.phone_number,
                'name': user.name,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

#<----------------------NOTIFICATION SECTION--------------------->





@api_view(['POST'])
@permission_classes([AllowAny])
def register_fcm_token(request):
    """
    Register or update FCM token for a user/device
    
    Body:
    {
        "fcm_token": "your_fcm_token_here",
        "phone_number": "9876543210",  # Optional - for existing users
        "name": "User Name",            # Optional - for new users
        "notifications_enabled": true
    }
    """
    serializer = FCMTokenSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'status': 'error',
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    fcm_token = serializer.validated_data['fcm_token']
    phone_number = request.data.get('phone_number', '').strip()
    name = request.data.get('name', '').strip()
    notifications_enabled = serializer.validated_data.get('notifications_enabled', True)
    
    try:
        if request.user.is_authenticated:
            # Update existing authenticated user
            user = request.user
            user.fcm_token = fcm_token
            user.notifications_enabled = notifications_enabled
            user.save()
            
            logger.info(f"✅ FCM token updated for user: {user.name} ({user.phone_number})")
            
            return Response({
                'status': 'success',
                'message': 'FCM token registered successfully',
                'user_id': user.id,
                'username': user.username,
                'name': user.name,
                'phone_number': user.phone_number,
                'notifications_enabled': user.notifications_enabled
            })
        
        elif phone_number:
            # Try to find existing user by phone number
            try:
                user = User.objects.get(phone_number=phone_number)
                user.fcm_token = fcm_token
                user.notifications_enabled = notifications_enabled
                user.save()
                
                logger.info(f"✅ FCM token updated for existing user: {user.name} ({user.phone_number})")
                
                return Response({
                    'status': 'success',
                    'message': 'FCM token updated for existing user',
                    'user_id': user.id,
                    'username': user.username,
                    'name': user.name,
                    'phone_number': user.phone_number,
                    'notifications_enabled': user.notifications_enabled
                })
                
            except User.DoesNotExist:
                # Create new user with phone number
                if not name:
                    name = f"User {phone_number}"
                
                user = User.objects.create_user(
                    phone_number=phone_number,
                    name=name,
                    fcm_token=fcm_token,
                    notifications_enabled=notifications_enabled
                )
                
                logger.info(f"✅ FCM token registered for new user: {user.name} ({user.phone_number})")
                
                return Response({
                    'status': 'success',
                    'message': 'FCM token registered for new user',
                    'user_id': user.id,
                    'username': user.username,
                    'name': user.name,
                    'phone_number': user.phone_number,
                    'notifications_enabled': user.notifications_enabled
                })
        
        else:
            # Create anonymous user without phone number
            anonymous_phone = f"anonymous_{uuid.uuid4().hex[:8]}"
            anonymous_name = name or f"Anonymous User"
            
            user = User.objects.create_user(
                phone_number=anonymous_phone,
                name=anonymous_name,
                fcm_token=fcm_token,
                notifications_enabled=notifications_enabled
            )
            
            logger.info(f"✅ FCM token registered for anonymous user: {user.username}")
            
            return Response({
                'status': 'success',
                'message': 'FCM token registered for anonymous user',
                'user_id': user.id,
                'username': user.username,
                'name': user.name,
                'notifications_enabled': user.notifications_enabled
            })
            
    except Exception as e:
        logger.error(f"❌ Failed to register FCM token: {e}")
        return Response({
            'status': 'error',
            'message': 'Failed to register FCM token'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def update_notification_preferences(request):
    """
    Update notification preferences
    
    Body:
    {
        "phone_number": "9876543210",     # Required if not authenticated
        "notifications_enabled": true
    }
    """
    phone_number = request.data.get('phone_number', '').strip()
    notifications_enabled = request.data.get('notifications_enabled', True)
    
    try:
        if request.user.is_authenticated:
            user = request.user
        elif phone_number:
            user = User.objects.get(phone_number=phone_number)
        else:
            return Response({
                'status': 'error',
                'message': 'Phone number required for unauthenticated users'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.notifications_enabled = notifications_enabled
        user.save()
        
        return Response({
            'status': 'success',
            'message': 'Notification preferences updated',
            'notifications_enabled': user.notifications_enabled
        })
        
    except User.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ Failed to update preferences: {e}")
        return Response({
            'status': 'error',
            'message': 'Failed to update notification preferences'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def unregister_fcm_token(request):
    """
    Remove FCM token (disable notifications)
    
    Body:
    {
        "phone_number": "9876543210"  # Required if not authenticated
    }
    """
    phone_number = request.data.get('phone_number', '').strip()
    
    try:
        if request.user.is_authenticated:
            user = request.user
        elif phone_number:
            user = User.objects.get(phone_number=phone_number)
        else:
            return Response({
                'status': 'error',
                'message': 'Phone number required for unauthenticated users'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.fcm_token = None
        user.notifications_enabled = False
        user.save()
        
        logger.info(f"✅ FCM token removed for user: {user.name} ({user.phone_number})")
        
        return Response({
            'status': 'success',
            'message': 'FCM token removed successfully'
        })
        
    except User.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ Failed to remove FCM token: {e}")
        return Response({
            'status': 'error',
            'message': 'Failed to remove FCM token'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)