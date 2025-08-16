# users/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import UserRegistrationSerializer, UserLoginSerializer
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

@api_view(['GET'])
@permission_classes([AllowAny])
def user_count_view(request):
    """API endpoint to get the total user count with caching."""
    try:
        from .signals import get_user_count
        total_users = get_user_count()
        return Response({
            'count': total_users,
            'message': 'User count retrieved successfully',
            'cached': True
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting user count: {e}")
        return Response({
            'error': 'Failed to retrieve user count'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




