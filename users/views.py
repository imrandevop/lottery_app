# users/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import UserRegistrationSerializer, UserLoginSerializer, LotteryPurchaseSerializer, LotteryStatisticsSerializer
from .models import User, LotteryPurchase
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
    

#<----------------------admin counter SECTION--------------------->

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


class LotteryPurchaseView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LotteryPurchaseSerializer(data=request.data)
        if serializer.is_valid():
            is_deleted = serializer.validated_data.get('is_deleted', False)
            record_id = serializer.validated_data.get('id')

            # Handle delete operation
            if is_deleted and record_id:
                try:
                    lottery_purchase = LotteryPurchase.objects.get(
                        id=record_id,
                        user_id=serializer.validated_data['user_id']
                    )
                    lottery_purchase.delete()
                    return Response({
                        'message': 'Lottery purchase deleted successfully'
                    }, status=status.HTTP_200_OK)
                except LotteryPurchase.DoesNotExist:
                    return Response({
                        'message': 'Record not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # Handle create operation (existing functionality)
            lottery_purchase = serializer.save()
            return Response({
                'id': lottery_purchase.id,
                'user_id': lottery_purchase.user_id,
                'lottery_number': lottery_purchase.lottery_number,
                'lottery_name': lottery_purchase.lottery_name,
                'ticket_price': lottery_purchase.ticket_price,
                'purchase_date': lottery_purchase.purchase_date,
                'message': 'Lottery purchase recorded successfully'
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Failed to record lottery purchase',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LotteryStatisticsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LotteryStatisticsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['user_id']

        # Get all lottery purchases for this user
        purchases = LotteryPurchase.objects.filter(user_id=user_id)

        # Update win status for all purchases
        for purchase in purchases:
            purchase.check_win_status()

        # Refresh purchases after status update
        purchases = LotteryPurchase.objects.filter(user_id=user_id)

        # Calculate statistics
        total_tickets = purchases.count()
        total_expense = sum(float(p.ticket_price) for p in purchases)

        winning_purchases = purchases.filter(is_winner=True)
        total_winnings = sum(float(p.winnings or 0) for p in winning_purchases)

        win_rate = (winning_purchases.count() / total_tickets * 100) if total_tickets > 0 else 0
        net_result = total_winnings - total_expense

        # Prepare lottery entries
        lottery_entries = []
        for idx, purchase in enumerate(purchases, 1):
            status_value = purchase.check_win_status()

            lottery_entries.append({
                "id": purchase.id,
                "lottery_unique_id": str(purchase.lottery_unique_id) if purchase.lottery_unique_id else None,
                "sl_no": idx,
                "lottery_number": purchase.lottery_number,
                "lottery_name": purchase.lottery_name,
                "price": float(purchase.ticket_price),
                "purchase_date": str(purchase.purchase_date),
                "winnings": float(purchase.winnings) if purchase.winnings else None,
                "status": status_value
            })

        response_data = {
            "user_id": user_id,
            "challenge_statistics": {
                "total_expense": total_expense,
                "total_winnings": total_winnings,
                "total_tickets": total_tickets,
                "win_rate": round(win_rate, 1),
                "net_result": net_result
            },
            "lottery_entries": lottery_entries
        }

        return Response(response_data, status=status.HTTP_200_OK)
