from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from .models import User

from django.conf import settings
import hashlib
import time

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
    
class CreateAdminView(APIView):
    """
    Temporary endpoint to create an admin user
    Will be disabled after initial setup
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Security check - this should match a pre-defined SECRET_KEY
        setup_key = request.data.get('setup_key')
        if not setup_key or setup_key != settings.ADMIN_SETUP_KEY:
            # Add time delay to prevent brute force
            time.sleep(3)
            return Response(
                {"error": "Invalid setup key"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get admin credentials
        username = request.data.get('username', 'admin')
        password = request.data.get('password')
        phone_number = request.data.get('phone_number', '9876543210')
        name = request.data.get('name', 'Admin User')
        
        if not password or len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters long"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists
        from django.db.models import Q
        from users.models import User
        
        if User.objects.filter(Q(username=username) | Q(phone_number=phone_number)).exists():
            user = User.objects.get(Q(username=username) | Q(phone_number=phone_number))
            user.username = username
            user.phone_number = phone_number
            user.name = name
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            message = f"Updated admin user: {username}"
        else:
            user = User.objects.create_user(
                phone_number=phone_number,
                name=name,
                password=password
            )
            user.username = username
            user.is_staff = True
            user.is_superuser = True
            user.save()
            message = f"Created new admin user: {username}"
        
        return Response({
            "success": True,
            "message": message,
            "username": username,
            "phone_number": phone_number,
            "important": "THIS ENDPOINT SHOULD BE DISABLED AFTER ADMIN CREATION"
        })