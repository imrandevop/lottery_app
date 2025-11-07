# views.py
import os
import random, hashlib
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from datetime import date,time
from django.utils.timezone import now, localtime
import uuid
from .models import Lottery, LotteryResult, PrizeEntry, ImageUpdate, News, PeoplesPrediction
from .models import PrizeEntry, LiveVideo
from django.db.models import Q, Sum
from .serializers import LotteryResultSerializer, LotteryResultDetailSerializer
from django.contrib.auth import get_user_model
from .serializers import TicketCheckSerializer, NewsSerializer
from .serializers import LiveVideoSerializer
from datetime import timedelta
import pytz
from rest_framework.permissions import AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
import logging
import numpy as np
from collections import Counter
from .services.fcm_service import FCMService
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction, IntegrityError
import json
from results.models import FcmToken
from functools import lru_cache
import re




logger = logging.getLogger('lottery_app')


class LotteryResultListView(generics.ListAPIView):
    """
    API endpoint to get all published lottery results
    """
    serializer_class = LotteryResultSerializer
    pagination_class = None  # Disable pagination for this view
    
    def get_queryset(self):
        queryset = LotteryResult.objects.filter(is_published=True).select_related('lottery').prefetch_related('prizes')
        
        # Filter by lottery code if provided
        lottery_code = self.request.query_params.get('lottery_code', None)
        if lottery_code:
            queryset = queryset.filter(lottery__code=lottery_code)
        
        # Filter by date if provided
        result_date = self.request.query_params.get('date', None)
        if result_date:
            queryset = queryset.filter(date=result_date)

        # Get results from last 30 days
        from datetime import timedelta
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        queryset = queryset.filter(date__gte=thirty_days_ago)

        return queryset.order_by('-date', '-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Get image settings from database
        image_settings = ImageUpdate.get_images()
        
        return Response({
            'status': 'success',
            'count': queryset.count(),
            'total_points': 1250,  # Static value since points system removed
            'updates': {
                "image1": {
                    "image_url": image_settings.update_image1,
                    "redirect_link": image_settings.redirect_link1
                },
                "image2": {
                    "image_url": image_settings.update_image2,
                    "redirect_link": image_settings.redirect_link2
                },
                "image3": {
                    "image_url": image_settings.update_image3,
                    "redirect_link": image_settings.redirect_link3
                }
            },
            'results': serializer.data
        })
    
    def get_total_points(self, request):
        """
        Calculate or retrieve total points for the user
        Replace this method with your actual business logic
        """
        # Example implementations (choose one based on your needs):
        
        # Option 1: If you have a user profile with points
        # if request.user.is_authenticated:
        #     return getattr(request.user.profile, 'total_points', 0)
        # return 0
        
        # Option 2: If you have a separate Points model
        # if request.user.is_authenticated:
        #     from django.db.models import Sum
        #     total = Points.objects.filter(user=request.user).aggregate(
        #         total=Sum('points')
        #     )['total']
        #     return total or 0
        # return 0
        
        # Option 3: Static value or calculation based on lottery data
        # return queryset.count() * 10  # Example: 10 points per lottery result
        
        # Placeholder - replace with your actual logic
        return 1250

# class LotteryResultDetailView(generics.RetrieveAPIView):
#     """
#     API endpoint to get detailed lottery result by ID
#     """
#     queryset = LotteryResult.objects.filter(is_published=True).select_related('lottery').prefetch_related('prizes')
#     serializer_class = LotteryResultDetailSerializer
    
#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
#         return Response({
#             'status': 'success',
#             'result': serializer.data
#         })

class LotteryResultByUniqueIdView(APIView):
    """
    API endpoint to retrieve lottery result by unique_id passed in request body
    """

    def post(self, request):
        unique_id = request.data.get('unique_id')

        if not unique_id:
            return Response(
                {'error': 'unique_id is required in request body'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate UUID format
        try:
            uuid.UUID(unique_id)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid unique ID format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the lottery result with related data
            lottery_result = LotteryResult.objects.select_related('lottery').prefetch_related('prizes').get(
                unique_id=unique_id,
                is_published=True
            )

            # Check if all ticket_numbers are 4-digit numbers only
            def is_grid_format(prizes):
                for prize in prizes:
                    num = prize.ticket_number.strip()
                    if len(num) != 4 or not num.isdigit():
                        return False
                return True

            is_grid = is_grid_format(lottery_result.prizes.all())

            # Serialize the data
            serializer = LotteryResultDetailSerializer(lottery_result)

            return Response({
                'status': 'success',
                'result': serializer.data,
            }, status=status.HTTP_200_OK)

        except LotteryResult.DoesNotExist:
            return Response(
                {'error': 'Lottery result not found'},
                status=status.HTTP_404_NOT_FOUND
            )

@api_view(['GET'])
def today_results(request):
    """
    API endpoint to get today's lottery results
    """
    today = date.today()
    results = LotteryResult.objects.filter(
        date=today, 
        is_published=True
    ).select_related('lottery').prefetch_related('prizes')
    
    serializer = LotteryResultSerializer(results, many=True)
    return Response({
        'status': 'success',
        'date': today,
        'count': results.count(),
        'results': serializer.data
    })

@api_view(['GET'])
def results_by_date(request, date_str):
    """
    API endpoint to get lottery results for a specific date
    Format: YYYY-MM-DD
    """
    try:
        from datetime import datetime, timedelta
        result_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        results = LotteryResult.objects.filter(
            date=result_date, 
            is_published=True
        ).select_related('lottery').prefetch_related('prizes')
        
        # Determine day label
        today = date.today()
        if result_date == today:
            day_label = 'Today Result'
        else:
            day_label = f'Result for {result_date.strftime("%B %d, %Y")}'
        
        serializer = LotteryResultSerializer(results, many=True)
        return Response({
            'status': 'success',
            'date': result_date,
            'count': results.count(),
            'results': serializer.data
        })
        
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
def latest_result(request, lottery_code):
    """
    API endpoint to get the latest result for a specific lottery
    """
    try:
        lottery = Lottery.objects.get(code=lottery_code)
        latest_result = LotteryResult.objects.filter(
            lottery=lottery,
            is_published=True
        ).select_related('lottery').prefetch_related('prizes').order_by('-date', '-created_at').first()
        
        if not latest_result:
            return Response(
                {'error': f'No published results found for lottery {lottery_code}'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = LotteryResultSerializer(latest_result)
        return Response({
            'status': 'success',
            'result': serializer.data
        })
        
    except Lottery.DoesNotExist:
        return Response(
            {'error': f'Lottery with code {lottery_code} not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
def lottery_results_by_code(request, lottery_code):
    """
    API endpoint to get all results for a specific lottery
    """
    try:
        lottery = Lottery.objects.get(code=lottery_code)
        results = LotteryResult.objects.filter(
            lottery=lottery,
            is_published=True
        ).select_related('lottery').prefetch_related('prizes').order_by('-date', '-created_at')
        
        # Manual pagination (without DRF pagination wrapper)
        page = request.query_params.get('page', 1)
        limit = min(int(request.query_params.get('limit', 10)), 100)  # Max 100 results per page
        
        try:
            page = int(page)
            start = (page - 1) * limit
            end = start + limit
            paginated_results = results[start:end]
            
            serializer = LotteryResultSerializer(paginated_results, many=True)
            
            return Response({
                'status': 'success',
                'lottery': {
                    'name': lottery.name,
                    'code': lottery.code
                },
                'page': page,
                'limit': limit,
                'total_count': results.count(),
                'count': len(paginated_results),
                'results': serializer.data
            })
            
        except ValueError:
            return Response(
                {'error': 'Invalid page number'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
    except Lottery.DoesNotExist:
        return Response(
            {'error': f'Lottery with code {lottery_code} not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    





# ---------------BAR CODE SCAN SECTION -------------


class TicketCheckView(APIView):
    """
    Enhanced API endpoint to check Kerala lottery tickets with points and cash back system
    """
    
    # Kerala Lottery day mapping
    LOTTERY_DAYS = {
        'M': 'sunday',     # Samrudhi
        'B': 'monday',     # Bhagyathara  
        'S': 'tuesday',    # Sthree Sakthi
        'D': 'wednesday',  # Dhanalekshmi
        'P': 'thursday',   # Karunya Plus
        'R': 'friday',     # Suvarna Keralam
        'K': 'saturday',   # Karunya
    }

    def get_expected_lottery_day(self, lottery_code):
        """Get expected day for lottery code"""
        return self.LOTTERY_DAYS.get(lottery_code.upper())

    def normalize_phone_number(self, phone_number):
        """Normalize phone number to consistent format (+91XXXXXXXXXX)"""
        import re
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', str(phone_number))
        
        # If it starts with +91, keep as is
        if cleaned.startswith('+91'):
            return cleaned
        
        # If it starts with 91, add +
        if cleaned.startswith('91') and len(cleaned) == 12:
            return '+' + cleaned
        
        # If it's 10 digits, assume Indian number and add +91
        if len(cleaned) == 10 and cleaned.isdigit():
            return '+91' + cleaned
        
        # Return as is if we can't normalize
        return cleaned

    def create_standard_response(self, status_code, status, result_status, message, points, cash_back, data):
        """Create standardized response format with points and cash back"""
        return {
            "statusCode": status_code,
            "status": status,
            "resultStatus": result_status,
            "message": message,
            "points": points,  # null if no points awarded
            "cashBack": cash_back,  # null if no cash back awarded
            "data": data
        }

    def create_prize_details(self, prize_entry=None):
        """Create prize details structure"""
        if not prize_entry:
            return {
                "prizeType": "",
                "prizeAmount": 0,
                "matchType": "no match",
                "winningTicketNumber": ""
            }
        
        return {
            "prizeType": prize_entry.get('prize_type', ''),
            "prizeAmount": prize_entry.get('prize_amount', 0),
            "matchType": prize_entry.get('match_type', ''),
            "winningTicketNumber": prize_entry.get('winning_ticket_number', '')
        }

    def create_previous_result(self, lottery_result=None, prize_data=None):
        """Create previous result structure"""
        if not lottery_result:
            return {
                "date": "",
                "drawNumber": "",
                "uniqueId": "",
                "totalPrizeAmount": 0,
                "prizeDetails": {}
            }
        
        total_amount = 0
        prize_details = {}
        
        if prize_data and prize_data.get('prize_details'):
            # Get the first/main prize for the response
            main_prize = prize_data['prize_details'][0]
            prize_details = self.create_prize_details(main_prize)
            total_amount = prize_data.get('total_amount', 0)
        else:
            prize_details = self.create_prize_details()
        
        return {
            "date": str(lottery_result.date) if lottery_result.date else "",
            "drawNumber": lottery_result.draw_number if lottery_result.draw_number else "",
            "uniqueId": str(lottery_result.unique_id) if lottery_result.unique_id else "",
            "totalPrizeAmount": total_amount,
            "prizeDetails": prize_details
        }

    def create_data_structure(self, ticket_number, lottery_name, requested_date, 
                            won_prize, result_published, is_previous_result, 
                            lottery_result=None, prize_data=None):
        """Create the data structure for response"""
        return {
            "ticketNumber": ticket_number,
            "lotteryName": lottery_name,
            "requestedDate": str(requested_date),
            "wonPrize": won_prize,
            "resultPublished": result_published,
            "isPreviousResult": is_previous_result,
            "previousResult": self.create_previous_result(lottery_result, prize_data)
        }

    def check_ticket_prizes(self, ticket_number, lottery_result):
        """Check if ticket won any prizes in the given result"""
        from .models import PrizeEntry
        
        last_4_digits = ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number

        # Get full ticket matches
        winning_tickets = PrizeEntry.objects.filter(
            ticket_number=ticket_number,
            lottery_result=lottery_result
        )

        # Get last 4 digits matches (excluding full matches)
        small_prize_tickets = PrizeEntry.objects.filter(
            ticket_number=last_4_digits,
            lottery_result=lottery_result
        ).exclude(ticket_number=ticket_number)

        all_wins = list(winning_tickets) + list(small_prize_tickets)
        
        if not all_wins:
            return None
        
        # Process prize data
        prize_details = []
        total_amount = 0
        
        for prize in all_wins:
            prize_amount = float(prize.prize_amount)
            total_amount += prize_amount
            is_small_prize = prize.ticket_number == last_4_digits and prize.ticket_number != ticket_number
            
            prize_details.append({
                'prize_type': prize.get_prize_type_display(),
                'prize_amount': prize_amount,
                'match_type': 'Last 4 digits match' if is_small_prize else 'Full ticket match',
                'winning_ticket_number': prize.ticket_number,
                'place': prize.place if prize.place else None
            })
        
        return {
            'total_amount': total_amount,
            'total_prizes': len(prize_details),
            'prize_details': prize_details
        }

    def check_reward_eligibility(self, ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist):
        """
        Check if user is eligible for rewards (cash back or points)
        Returns: (is_eligible, reason) tuple
        """
        from .models import DailyPointsAwarded, DailyCashAwarded
        
        # Normalize phone number for consistency
        normalized_phone = self.normalize_phone_number(phone_number)
        
        # Rule 1: Non-Winners Only
        if won_prize:
            return (False, "Rewards only given to non-winning tickets")
        
        # Rule 2: Today's Lottery Only
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        if check_date != today_ist:
            return (False, "Rewards only given for today's lottery check")
        
        # Rule 3: Time Restriction (After 3:00 PM IST)
        result_publish_time = time(15, 0)  # 3:00 PM
        if current_time_ist < result_publish_time:
            return (False, "Rewards given only after 3:00 PM IST")
        
        # Rule 4: One Award Per User Per Day (check both cash and points)
        if DailyCashAwarded.has_received_cash_today(normalized_phone):
            return (False, "Cash back already received today for this phone number")
        
        if DailyPointsAwarded.has_received_points_today(normalized_phone):
            return (False, "Points already awarded today for this phone number")
        
        return (True, "Eligible for rewards")

    def calculate_cash_back_award(self, ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist):
        """
        Try to award cash back first (₹1-₹10 random for first 30 eligible users)
        Returns: (cash_awarded, reason) tuple
        """
        from .models import DailyCashPool
        import random
        
        # Check basic eligibility first
        is_eligible, reason = self.check_reward_eligibility(
            ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist
        )
        
        if not is_eligible:
            return (None, reason)
        
        # Rule 5: Daily Cash Pool Control (30 users max, ₹100 budget)
        daily_cash_pool = DailyCashPool.get_today_pool()
        
        # Check if cash back is still available
        if daily_cash_pool.users_awarded >= daily_cash_pool.max_users:
            return (None, "Cash back limit reached (30 users per day)")
        
        if daily_cash_pool.remaining_amount <= 0:
            return (None, "Daily cash pool exhausted")
        
        # Rule 6: Random Cash Generation (₹1-₹10)
        random_cash = random.randint(1, 10)
        
        # Cap to available pool budget (but should always have enough for 30 users)
        actual_cash = min(random_cash, int(daily_cash_pool.remaining_amount))
        
        if actual_cash <= 0:
            return (None, "No cash available in daily pool")
        
        return (actual_cash, "Cash back awarded successfully")

    def calculate_points_award(self, ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist):
        """
        Calculate points award (fallback when cash back not available)
        Returns: (points_awarded, reason) tuple
        """
        from .models import DailyPointsPool
        import random
        
        # Check basic eligibility first
        is_eligible, reason = self.check_reward_eligibility(
            ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist
        )
        
        if not is_eligible:
            return (None, reason)
        
        # Rule 5: Daily Points Pool Budget Control
        daily_pool = DailyPointsPool.get_today_pool()
        if daily_pool.remaining_points <= 0:
            return (None, "Daily points pool exhausted")
        
        # Rule 6: Random Point Generation (1-50)
        random_points = random.randint(1, 50)
        
        # Cap to available pool budget
        actual_points = min(random_points, daily_pool.remaining_points)
        
        if actual_points <= 0:
            return (None, "No points available in daily pool")
        
        return (actual_points, "Points awarded successfully")

    def award_cash_back_to_user(self, phone_number, cash_amount, ticket_number, lottery_name, check_date):
        """
        Award cash back to user with full transaction tracking
        Returns: (success, message) tuple
        """
        from .models import DailyCashPool, DailyCashAwarded, UserCashBalance, CashTransaction
        
        try:
            with transaction.atomic():
                normalized_phone = self.normalize_phone_number(phone_number)
                
                # Get today's cash pool with row lock
                daily_cash_pool = DailyCashPool.get_today_pool()
                
                # Double-check pool can award cash
                if not daily_cash_pool.can_award_cash(cash_amount):
                    return (False, "Daily cash pool insufficient or user limit reached")
                
                # Award cash from pool
                if not daily_cash_pool.award_cash(cash_amount):
                    return (False, "Failed to deduct from cash pool")
                
                # Get or create user cash balance
                user_cash_balance = UserCashBalance.get_or_create_user(normalized_phone)
                balance_before = user_cash_balance.total_cash
                
                # Add cash to user
                user_cash_balance.add_cash(cash_amount)
                balance_after = user_cash_balance.total_cash
                
                # Record daily cash award (prevents duplicate awards)
                DailyCashAwarded.record_cash_award(
                    normalized_phone, cash_amount, ticket_number, lottery_name
                )
                
                # Create cash transaction record
                CashTransaction.objects.create(
                    phone_number=normalized_phone,
                    transaction_type='lottery_check',
                    cash_amount=cash_amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    ticket_number=ticket_number,
                    lottery_name=lottery_name,
                    check_date=check_date,
                    daily_cash_pool_date=daily_cash_pool.date,
                    description=f"Lottery check cash back: {ticket_number} ({lottery_name})"
                )
                
                logger.info(f"✅ Cash back awarded: {normalized_phone} +₹{cash_amount} (Pool: {daily_cash_pool.users_awarded}/{daily_cash_pool.max_users} users, ₹{daily_cash_pool.remaining_amount} remaining)")
                return (True, f"Successfully awarded ₹{cash_amount} cash back")
                
        except Exception as e:
            logger.error(f"❌ Cash back award failed: {e}")
            return (False, f"Cash back award failed: {str(e)}")

    def award_points_to_user(self, phone_number, points_amount, ticket_number, lottery_name, check_date):
        """
        Award points to user with full transaction tracking
        Returns: (success, message) tuple
        """
        from .models import DailyPointsPool, DailyPointsAwarded, UserPointsBalance, PointsTransaction
        
        try:
            with transaction.atomic():
                normalized_phone = self.normalize_phone_number(phone_number)
                
                # Get today's pool with row lock
                daily_pool = DailyPointsPool.get_today_pool()
                
                # Double-check pool has enough points
                if not daily_pool.can_award_points(points_amount):
                    return (False, "Daily pool insufficient")
                
                # Award points from pool
                if not daily_pool.award_points(points_amount):
                    return (False, "Failed to deduct from pool")
                
                # Get or create user balance
                user_balance = UserPointsBalance.get_or_create_user(normalized_phone)
                balance_before = user_balance.total_points
                
                # Add points to user
                user_balance.add_points(points_amount)
                balance_after = user_balance.total_points
                
                # Record daily award (prevents duplicate awards)
                DailyPointsAwarded.record_points_award(
                    normalized_phone, points_amount, ticket_number, lottery_name
                )
                
                # Create transaction record
                PointsTransaction.objects.create(
                    phone_number=normalized_phone,
                    transaction_type='lottery_check',
                    points_amount=points_amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    ticket_number=ticket_number,
                    lottery_name=lottery_name,
                    check_date=check_date,
                    daily_pool_date=daily_pool.date,
                    description=f"Lottery check reward: {ticket_number} ({lottery_name})"
                )
                
                logger.info(f"✅ Points awarded: {normalized_phone} +{points_amount} pts (Pool: {daily_pool.remaining_points} remaining)")
                return (True, f"Successfully awarded {points_amount} points")
                
        except Exception as e:
            logger.error(f"❌ Points award failed: {e}")
            return (False, f"Points award failed: {str(e)}")

    def post(self, request):
        """Enhanced post method with cash back and points system integration"""
        from .serializers import TicketCheckSerializer
        from .models import Lottery, LotteryResult
        
        try:
            serializer = TicketCheckSerializer(data=request.data)

            if not serializer.is_valid():
                error_data = self.create_data_structure("", "", "", False, False, False)
                response = self.create_standard_response(
                    400, "fail", "Validation Error", 
                    f"Invalid data: {serializer.errors}", None, None, error_data
                )
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            # Get validated data
            ticket_number = serializer.validated_data['ticket_number']
            phone_number = serializer.validated_data['phone_number']
            check_date = serializer.validated_data['date']

            if len(ticket_number) < 1:
                error_data = self.create_data_structure(ticket_number, "", str(check_date), False, False, False)
                response = self.create_standard_response(
                    400, "fail", "Invalid Ticket", 
                    "Invalid ticket number format", None, None, error_data
                )
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            lottery_code = ticket_number[0].upper()

            # Validate lottery code
            if not self.get_expected_lottery_day(lottery_code):
                error_data = self.create_data_structure(ticket_number, "", str(check_date), False, False, False)
                response = self.create_standard_response(
                    400, "fail", "Invalid Lottery Code", 
                    f"Invalid lottery code: {lottery_code}", None, None, error_data
                )
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            try:
                lottery = Lottery.objects.get(code=lottery_code)
            except Lottery.DoesNotExist:
                error_data = self.create_data_structure(ticket_number, "", str(check_date), False, False, False)
                response = self.create_standard_response(
                    400, "fail", "Lottery Not Found", 
                    f'Lottery with code "{lottery_code}" not found', None, None, error_data
                )
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            # Use IST timezone for accurate time checking
            ist = pytz.timezone('Asia/Kolkata')
            current_datetime_ist = timezone.now().astimezone(ist)
            current_date_ist = current_datetime_ist.date()
            current_time_ist = current_datetime_ist.time()
            result_publish_time = time(15, 0)  # 3:00 PM

            # Check if requested date matches lottery's scheduled day
            requested_day = check_date.strftime('%A').lower()
            lottery_day = self.get_expected_lottery_day(lottery_code)
            is_lottery_day_match = (requested_day == lottery_day)
            is_today = (check_date == current_date_ist)

            # Look for exact date result first
            exact_result = LotteryResult.objects.filter(
                lottery=lottery,
                date=check_date,
                is_published=True
            ).first()

            if exact_result:
                # Result exists for the exact requested date
                return self.handle_exact_date_result(
                    lottery, ticket_number, phone_number, check_date, 
                    exact_result, is_today, current_time_ist
                )
            
            elif is_lottery_day_match and is_today and current_time_ist < result_publish_time:
                # Correct lottery day but before 3 PM - result not published yet
                return self.handle_result_not_published_same_day(
                    lottery, ticket_number, phone_number, check_date
                )
            
            else:
                # Different day or no result for requested date - show most recent result
                return self.handle_different_day_result(
                    lottery, ticket_number, phone_number, check_date
                )

        except Exception as e:
            # PROPER ERROR HANDLING: Return 500 for unexpected errors
            logger.error(f"❌ Unexpected error in TicketCheckView: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            error_data = self.create_data_structure("", "", "", False, False, False)
            response = self.create_standard_response(
                500, "error", "Internal Server Error", 
                "An unexpected error occurred. Please try again later.", None, None, error_data
            )
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def handle_result_not_published_same_day(self, lottery, ticket_number, phone_number, check_date):
        """Handle case when result is not published yet (before 3 PM on correct lottery day)"""
        # Get the correct day name for the lottery
        lottery_day = self.get_expected_lottery_day(ticket_number[0].upper())
        
        data = self.create_data_structure(
            ticket_number, lottery.name, check_date, 
            False, False, False
        )
        
        message = f"Result not published yet. Please check on {lottery_day.title()} after 3:00 PM"
        
        response = self.create_standard_response(
            200, "success", "Result is not published", 
            message, None, None, data  # No rewards when result not published
        )
        return Response(response, status=status.HTTP_200_OK)

    def handle_exact_date_result(self, lottery, ticket_number, phone_number, check_date, lottery_result, is_today, current_time_ist):
        """Handle case when result exists for the exact requested date"""
        # Check if ticket won
        prize_data = self.check_ticket_prizes(ticket_number, lottery_result)
        won_prize = bool(prize_data)
        
        # Initialize reward variables
        cash_back_awarded = None
        points_awarded = None
        
        # Try to award rewards (only for today's non-winning tickets after 3 PM)
        if is_today:
            # Priority 1: Try cash back first
            calculated_cash, cash_reason = self.calculate_cash_back_award(
                ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist
            )
            
            if calculated_cash:
                # Award cash back to user
                cash_award_success, cash_award_message = self.award_cash_back_to_user(
                    phone_number, calculated_cash, ticket_number, lottery.name, check_date
                )
                
                if cash_award_success:
                    cash_back_awarded = calculated_cash
                    logger.info(f"✅ Cash back awarded: {phone_number} +₹{calculated_cash}")
                else:
                    logger.warning(f"⚠️ Cash back calculation passed but award failed: {cash_award_message}")
                    
            else:
                # Priority 2: Try points as fallback
                logger.info(f"ℹ️ No cash back available: {cash_reason}")
                
                calculated_points, points_reason = self.calculate_points_award(
                    ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist
                )
                
                if calculated_points:
                    # Award points to user
                    points_award_success, points_award_message = self.award_points_to_user(
                        phone_number, calculated_points, ticket_number, lottery.name, check_date
                    )
                    
                    if points_award_success:
                        points_awarded = calculated_points
                        logger.info(f"✅ Points awarded: {phone_number} +{calculated_points} pts")
                    else:
                        logger.warning(f"⚠️ Points calculation passed but award failed: {points_award_message}")
                else:
                    logger.info(f"ℹ️ No points awarded: {points_reason}")
        
        if prize_data:
            # Won prize on requested date
            if is_today:
                result_status = "won price today"
                message = f"Congratulations! You won ₹{prize_data['total_amount']:,.0f} in {lottery.name} draw."
            else:
                result_status = "Previous Result"
                message = f"Congratulations! You won ₹{prize_data['total_amount']:,.0f} in the {lottery.name} draw."
            
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                True, True, False, lottery_result, prize_data
            )
            response = self.create_standard_response(
                200, "success", result_status, message, points_awarded, cash_back_awarded, data
            )
        else:
            # No prize on requested date
            if is_today:
                result_status = "No Price Today"
                base_message = "Better luck next time"
                
                # Customize message based on rewards
                if cash_back_awarded:
                    message = f"{base_message}. You earned ₹{cash_back_awarded} cash back!"
                elif points_awarded:
                    message = f"{base_message}. You earned {points_awarded} points!"
                else:
                    message = base_message
            else:
                result_status = "Previous Result no price"
                message = "Better luck next time"
            
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                False, True, False, lottery_result, None
            )
            response = self.create_standard_response(
                200, "success", result_status, message, points_awarded, cash_back_awarded, data
            )
        
        return Response(response, status=status.HTTP_200_OK)

    def handle_different_day_result(self, lottery, ticket_number, phone_number, check_date):
        """Handle checking lottery on wrong day - always show most recent result with isPreviousResult: true"""
        from .models import LotteryResult
        
        # Find the most recent published result for this lottery
        previous_result = LotteryResult.objects.filter(
            lottery=lottery,
            is_published=True
        ).order_by('-date').first()

        if not previous_result:
            # No previous data available at all
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                False, False, True
            )
            response = self.create_standard_response(
                400, "fail", "No Previous data", 
                "No result data found on database", None, None, data  # No rewards for previous results
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        # Check if ticket won in the most recent result
        prize_data = self.check_ticket_prizes(ticket_number, previous_result)
        
        # No rewards for previous results (Rule 2: Today's Lottery Only)
        
        if prize_data:
            # Won in most recent result
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                True, False, True, previous_result, prize_data
            )
            message = f"Congratulations! You won ₹{prize_data['total_amount']:,.0f} in the latest {lottery.name} draw."
            response = self.create_standard_response(
                200, "success", "Previous Result", message, None, None, data  # No rewards for previous results
            )
        else:
            # No prize in most recent result
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                False, False, True, previous_result, None
            )
            response = self.create_standard_response(
                200, "success", "Previous Result no price", 
                "Better luck next time", None, None, data  # No rewards for previous results
            )
        
        return Response(response, status=status.HTTP_200_OK)
            

# <--------------NEWS SECTION---------------->
class NewsListAPIView(generics.ListAPIView):
    """
    API endpoint to list latest 20 active news articles
    """
    queryset = News.objects.filter(is_active=True)[:20]  # Limit to 20 latest
    serializer_class = NewsSerializer
    pagination_class = None  # Disable pagination since we want exactly 20

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            "status": "success",
            "code": 200,
            "message": f"Latest {len(serializer.data)} news fetched successfully",
            "data": serializer.data
        })
    
    
@api_view(['GET'])
def latest_news(request):
    """
    API endpoint to get the latest news article
    """
    try:
        news = News.objects.filter(is_active=True).first()
        if not news:
            return Response({
                "status": "error",
                "code": 404,
                "message": "No news found",
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = NewsSerializer(news)
        return Response({
            "status": "success",
            "code": 200,
            "message": "Latest news fetched successfully",
            "data": serializer.data
        })
    except Exception as e:
        return Response({
            "status": "error",
            "code": 500,
            "message": "Internal server error",
            "data": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


#<---------------PREDICTION SECTION ---------------->

class LotteryPredictionAPIView(APIView):
    """
    API View for lottery repeated numbers from last 30 days
    """





    def get_repeated_numbers_last_30_days(self):
        """
        Get repeated last 4 digits from all lotteries and all 4th-10th prize types from last 30 days
        """
        from datetime import datetime, timedelta
        from collections import Counter
        
        # Calculate 30 days ago
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        
        # Get all 4-digit numbers from 4th-10th prizes across all lotteries from last 30 days
        prize_entries = PrizeEntry.objects.filter(
            lottery_result__date__gte=thirty_days_ago,
            lottery_result__is_published=True,
            prize_type__in=['4th', '5th', '6th', '7th', '8th', '9th', '10th']
        ).values_list('ticket_number', flat=True)
        
        # Extract last 4 digits and count frequencies
        last_4_digits = []
        for ticket_number in prize_entries:
            if ticket_number:
                ticket_str = str(ticket_number).strip()
                if len(ticket_str) >= 4:
                    last_4 = ticket_str[-4:]
                    if last_4.isdigit():
                        last_4_digits.append(last_4.zfill(4))
        
        # Count frequencies
        frequency_counter = Counter(last_4_digits)
        
        # Convert to required format and sort by count (highest first), limit to 9 numbers
        repeated_numbers = [
            {"number": number, "count": count} 
            for number, count in frequency_counter.most_common()
            if count > 1  # Only include numbers that appeared more than once
        ][:9]  # Limit to maximum 9 numbers
        
        return repeated_numbers

    def get_repeated_single_digits_last_7_days(self):
        """
        Get repeated single digits (last digit of ticket numbers) from all lotteries 
        and all 4th-10th prize types from last 7 days
        """
        from datetime import datetime, timedelta
        from collections import Counter
        
        # Calculate 7 days ago
        seven_days_ago = datetime.now().date() - timedelta(days=7)
        
        # Get all ticket numbers from 4th-10th prizes across all lotteries from last 7 days
        prize_entries = PrizeEntry.objects.filter(
            lottery_result__date__gte=seven_days_ago,
            lottery_result__is_published=True,
            prize_type__in=['4th', '5th', '6th', '7th', '8th', '9th', '10th']
        ).values_list('ticket_number', flat=True)
        
        # Extract last digit and count frequencies
        last_digits = []
        for ticket_number in prize_entries:
            if ticket_number:
                ticket_str = str(ticket_number).strip()
                if ticket_str and ticket_str[-1].isdigit():
                    last_digits.append(ticket_str[-1])
        
        # Count frequencies
        frequency_counter = Counter(last_digits)
        
        # Convert to required format and sort by count (highest first), limit to top 4
        repeated_single_digits = [
            {"digit": digit, "count": count} 
            for digit, count in frequency_counter.most_common(4)
        ]
        
        return repeated_single_digits

    def get_peoples_predictions(self):
        """
        Get top 4 most repeated peoples predictions from current day cycle (3:00 PM to next day 3:00 PM)
        """
        from collections import Counter
        
        # Clean up old predictions first
        PeoplesPrediction.cleanup_old_predictions()
        
        # Get all current predictions
        predictions = PeoplesPrediction.objects.all().values_list('peoples_prediction', flat=True)
        
        # Count frequencies
        frequency_counter = Counter(predictions)
        
        # Convert to required format and sort by count (highest first), limit to top 4
        peoples_predictions = [
            {"digit": digit, "count": count} 
            for digit, count in frequency_counter.most_common(4)
        ]
        
        return peoples_predictions

    def get(self, request):
        """
        Get repeated numbers from last 30 days and repeated single digits from last 7 days across all lotteries
        """
        try:
            # Get repeated numbers from last 30 days
            repeated_numbers = self.get_repeated_numbers_last_30_days()
            
            # Get repeated single digits from last 7 days
            repeated_single_digits = self.get_repeated_single_digits_last_7_days()
            
            # Get peoples predictions
            peoples_predictions = self.get_peoples_predictions()
            
            # Build response data
            response_data = {
                'status': 'success',
                'repeated_numbers': repeated_numbers,
                'repeated_single_digits': repeated_single_digits,
                'peoples_predictions': peoples_predictions
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': f'Failed to get repeated numbers: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Store people's single digit prediction
        Expected body: {"peoples_prediction": "5"}
        """
        try:
            # Get prediction from request
            peoples_prediction = request.data.get('peoples_prediction')
            
            # Get user IP for tracking
            user_ip = self.get_client_ip(request)
            
            # Store the prediction
            PeoplesPrediction.objects.create(
                peoples_prediction=str(peoples_prediction),
                user_ip=user_ip
            )
            
            return Response({
                'status': 'success'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Handle any unexpected errors
            return Response({
                'status': 'error',
                'message': f'Failed to store prediction: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip




# <--------------LIVE SECTION ---------------->

class LiveVideoListView(generics.ListAPIView):
    """
    Single API endpoint to get all live videos with filtering
    """
    queryset = LiveVideo.objects.all()
    serializer_class = LiveVideoSerializer
    permission_classes = [AllowAny]  # No authentication required
    pagination_class = None  # Disable pagination
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = LiveVideo.objects.filter(is_active=True)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(lottery_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-date')
    
    def list(self, request, *args, **kwargs):
        """Custom list method to add success message"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message': 'success',
            'count': len(serializer.data),
            'data': serializer.data,            
        })
    


class LotteryWinningPercentageAPI(APIView):
    """
    Daily reset lottery API - percentages change after 3 PM each day
    """
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.number_pattern = re.compile(r'^[A-Z]{2}\d{6}$')
    
    def get_daily_seed(self, lottery_number):
        """Generate seed that changes daily at 3 PM"""
        try:
            now = timezone.now()
            
            # Get current date
            current_date = now.date()
            
            # If time is before 3 PM, use current date
            # If time is after 3 PM, use current date (same day until next 3 PM)
            if now.hour < 15:  # Before 3 PM (15:00)
                # Use previous date (so it changes at 3 PM today)
                seed_date = current_date - timedelta(days=1)
            else:
                # Use current date (will change tomorrow at 3 PM)
                seed_date = current_date
            
            # Create seed string with lottery number and date
            seed_string = f"{lottery_number}_{seed_date}"
            
            # Generate consistent hash
            return int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
            
        except Exception as e:
            logger.error(f"Error generating daily seed: {e}")
            # Fallback seed
            fallback = f"{lottery_number}_{timezone.now().date()}"
            return int(hashlib.md5(fallback.encode()).hexdigest()[:8], 16)
    
    def analyze_pattern_category(self, four_digit_number):
        """
        Analyze 4-digit number and categorize based on fancy patterns
        Returns list of pattern categories the number belongs to
        """
        patterns = []
        digits = [int(d) for d in four_digit_number]
        digit_str = four_digit_number

        # 1. Repeating Patterns (ABAB, AABB, ABBA, AAAB, BAAA)
        if (digits[0] == digits[2] and digits[1] == digits[3]):  # ABAB
            patterns.append("Repeating_ABAB")
        elif (digits[0] == digits[1] and digits[2] == digits[3]):  # AABB
            patterns.append("Repeating_AABB")
        elif (digits[0] == digits[3] and digits[1] == digits[2]):  # ABBA
            patterns.append("Repeating_ABBA")
        elif (digits[0] == digits[1] == digits[2] and digits[3] != digits[0]):  # AAAB
            patterns.append("Repeating_AAAB")
        elif (digits[1] == digits[2] == digits[3] and digits[0] != digits[1]):  # BAAA
            patterns.append("Repeating_BAAA")

        # 2. Round Numbers (X000, X00Y, XX00)
        if digit_str.endswith('000'):  # X000
            patterns.append("Round_X000")
        elif digit_str[1:3] == '00':  # X00Y
            patterns.append("Round_X00Y")
        elif digit_str.endswith('00'):  # XX00
            patterns.append("Round_XX00")

        # 3. Sequential Patterns
        # Ascending (1234, 2345, etc.)
        is_ascending = all(digits[i] + 1 == digits[i + 1] for i in range(3))
        # Descending (4321, 5432, etc.)
        is_descending = all(digits[i] - 1 == digits[i + 1] for i in range(3))
        # Mixed sequential (1324, 2143, etc.) - contains consecutive digits but not in order
        sorted_digits = sorted(digits)
        is_mixed_sequential = (not is_ascending and not is_descending and
                             all(sorted_digits[i] + 1 == sorted_digits[i + 1] for i in range(3)))

        if is_ascending:
            patterns.append("Sequential_Ascending")
        elif is_descending:
            patterns.append("Sequential_Descending")
        elif is_mixed_sequential:
            patterns.append("Sequential_Mixed")

        # 4. Leading Zero Patterns (000X, 00XY, 0XXX)
        if digit_str.startswith('000'):  # 000X
            patterns.append("LeadingZero_000X")
        elif digit_str.startswith('00'):  # 00XY
            patterns.append("LeadingZero_00XY")
        elif digit_str.startswith('0'):  # 0XXX
            patterns.append("LeadingZero_0XXX")

        # 5. Double Digit Patterns (AABB, BBAA) - already covered in repeating but separate category
        if (digits[0] == digits[1] and digits[2] == digits[3]):  # AABB
            patterns.append("DoubleDigit_AABB")
        elif (digits[2] == digits[3] and digits[0] == digits[1]):  # BBAA (same as AABB)
            patterns.append("DoubleDigit_BBAA")

        # 6. Mirror/Palindrome Patterns (ABBA, BAAB)
        if digits[0] == digits[3] and digits[1] == digits[2]:
            patterns.append("Mirror_Palindrome")

        # 7. Triple Digits (AAAB, BAAA, ABAA, AABA)
        digit_counts = {str(i): digit_str.count(str(i)) for i in range(10)}
        if 3 in digit_counts.values():
            patterns.append("Triple_Digits")

        # 8. Regular Random Numbers (if no fancy patterns detected)
        if not patterns:
            patterns.append("Regular_Random")

        return patterns

    def calculate_pattern_based_percentage(self, lottery_number):
        """
        Calculate percentage based on fancy pattern analysis
        Fancy patterns get VERY HIGH chance to win (75-90% range)
        Regular random numbers get lower chance (15-35% range)
        """
        try:
            if not self.number_pattern.match(lottery_number):
                return 25.0

            # Extract last 4 digits
            four_digits = lottery_number[-4:]

            # Get daily seed for consistency
            seed = self.get_daily_seed(lottery_number)
            import random
            random.seed(seed)

            # Analyze pattern categories
            patterns = self.analyze_pattern_category(four_digits)

            if "Regular_Random" in patterns:
                # Regular random numbers get LOW chance (15-35%)
                base_percentage = random.uniform(15, 35)
                # Add small variation (-3 to +3)
                variation = random.uniform(-3, 3)
                final_percentage = base_percentage + variation
            else:
                # Fancy pattern numbers get VERY HIGH chance (75-90%)
                # Base range for single pattern
                base_percentage = random.uniform(75, 85)

                # Bonus for multiple patterns (up to +10%)
                if len(patterns) > 1:
                    multi_pattern_bonus = min(10, len(patterns) * 2)
                    base_percentage += multi_pattern_bonus

                # Special high bonus for rare patterns
                rare_patterns = [
                    "Round_X000", "LeadingZero_000X", "Sequential_Ascending",
                    "Sequential_Descending", "Triple_Digits"
                ]
                rare_count = sum(1 for p in patterns if any(rare in p for rare in rare_patterns))
                if rare_count > 0:
                    base_percentage += rare_count * 2  # +2% per rare pattern

                # Add small variation (-1 to +1)
                variation = random.uniform(-1, 1)
                final_percentage = base_percentage + variation

            # Ensure stays within range (10-90%)
            final_percentage = max(10, min(final_percentage, 90))

            return float(final_percentage)

        except Exception as e:
            logger.error(f"Error calculating pattern-based percentage: {e}")
            # Fallback calculation
            seed = hash(f"{lottery_number}_{timezone.now().date()}") % 1000000
            import random
            random.seed(seed)
            return float(random.randint(15, 70))
    
    def generate_message(self, percentage, lottery_number):
        """Generate entertaining messages based on pattern analysis"""
        last_4 = lottery_number[-4:]

        # Analyze patterns for better message context
        patterns = self.analyze_pattern_category(last_4)
        is_fancy = "Regular_Random" not in patterns

        if percentage >= 85:
            if is_fancy:
                messages = [
                    f"🎯 EXCELLENT! {last_4} has PREMIUM fancy patterns - HIGH CHANCE TO WIN!",
                    f"🔥 SUPER HOT! {last_4} shows EXCEPTIONAL pattern strength - VERY LUCKY!",
                    f"⭐ AMAZING! {last_4} has RARE patterns with MAXIMUM potential today!"
                ]
            else:
                messages = [
                    f"🎯 Excellent! {last_4} shows high winning potential today!",
                    f"🔥 Hot number! {last_4} has strong indicators for today!",
                    f"⭐ Great choice! {last_4} looks very promising today!"
                ]
        elif percentage >= 75:
            if is_fancy:
                messages = [
                    f"🚀 FANTASTIC! {last_4} has STRONG fancy patterns - HIGH WIN CHANCE!",
                    f"💎 PREMIUM! {last_4} shows POWERFUL pattern indicators!",
                    f"🌟 WONDERFUL! {last_4} has GREAT pattern strength for winning!"
                ]
            else:
                messages = [
                    f"👍 Good! {last_4} shows favorable signs for today!",
                    f"✨ Nice pick! {last_4} has decent potential today!",
                    f"🎯 Solid choice! {last_4} demonstrates good indicators!"
                ]
        elif percentage >= 60:
            if is_fancy:
                messages = [
                    f"✨ GOOD! {last_4} has NICE fancy patterns - GOOD WIN POTENTIAL!",
                    f"🎲 LUCKY! {last_4} shows FAVORABLE pattern signs!",
                    f"👍 SOLID! {last_4} demonstrates DECENT pattern strength!"
                ]
            else:
                messages = [
                    f"⚖️ Moderate potential! {last_4} shows average indicators today.",
                    f"📊 Fair chance! {last_4} has mixed signals for today.",
                    f"🤔 Average choice! {last_4} shows moderate patterns today."
                ]
        elif percentage >= 35:
            messages = [
                f"⚖️ Moderate potential! {last_4} shows average indicators today.",
                f"📊 Fair chance! {last_4} has mixed signals for today.",
                f"🤔 Average choice! {last_4} shows moderate patterns today."
            ]
        elif percentage >= 25:
            messages = [
                f"📉 Below average! {last_4} has limited potential today.",
                f"⚠️ Low-moderate! {last_4} shows weak patterns for today.",
                f"🔍 Consider other options! {last_4} has minimal indicators today."
            ]
        else:
            messages = [
                f"❌ Low potential! {last_4} shows poor indicators today.",
                f"🚫 Weak choice! {last_4} has unfavorable patterns today.",
                f"💭 Try different number! {last_4} shows limited promise today."
            ]

        # Use consistent message selection based on percentage
        seed = hash(f"{percentage}{lottery_number}") % len(messages)
        return messages[seed]
    
    def post(self, request):
        """
        Main API endpoint
        Expected body: {
            "lottery_name": "Karunya",
            "lottery_number": "AB123456"
        }
        """
        try:
            # Validate input
            lottery_name = request.data.get('lottery_name', '').strip()
            lottery_number = request.data.get('lottery_number', '').strip()
            
            if not lottery_name:
                return Response({
                    'lottery_number': lottery_number,
                    'lottery_name': lottery_name,
                    'percentage': 0.0,
                    'message': 'Lottery name is required',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not lottery_number:
                return Response({
                    'lottery_number': lottery_number,
                    'lottery_name': lottery_name,
                    'percentage': 0.0,
                    'message': 'Lottery number is required',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate and format number
            lottery_number = str(lottery_number).upper().strip()
            if not self.number_pattern.match(lottery_number):
                return Response({
                    'lottery_number': lottery_number,
                    'lottery_name': lottery_name,
                    'percentage': 0.0,
                    'message': 'Invalid format. Use: AB123456 (2 letters + 6 digits)',
                    'status': 'error'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if lottery exists
            lottery = Lottery.objects.filter(
                Q(name__icontains=lottery_name) | Q(code__icontains=lottery_name)
            ).first()
            
            if not lottery:
                return Response({
                    'lottery_number': lottery_number,
                    'lottery_name': lottery_name,
                    'percentage': 0.0,
                    'message': f'Lottery "{lottery_name}" not found',
                    'status': 'error'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate pattern-based percentage (changes daily at 3 PM)
            percentage = self.calculate_pattern_based_percentage(lottery_number)
            
            # Generate message
            message = self.generate_message(percentage, lottery_number)
            
            # Success response
            return Response({
                'status': 'success',
                'lottery_number': lottery_number,
                'lottery_name': lottery.name,
                'percentage': round(percentage, 2),
                'message': message
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in LotteryWinningPercentageAPI: {e}")
            return Response({
                'lottery_number': request.data.get('lottery_number', ''),
                'lottery_name': request.data.get('lottery_name', ''),
                'percentage': 0.0,
                'message': 'Service temporarily unavailable',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

#<--------------NOTIFICATION SECTION ---------------->

@csrf_exempt
@require_http_methods(["POST"])
def register_fcm_token(request):
    """Single API endpoint to register/update FCM tokens"""
    try:
        data = json.loads(request.body)
        
        # Extract required fields
        fcm_token = data.get('fcm_token')
        phone_number = data.get('phone_number')
        name = data.get('name')
        notifications_enabled = data.get('notifications_enabled', True)
        
        # Validate required fields
        if not all([fcm_token, phone_number, name]):
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields: fcm_token, phone_number, name'
            }, status=400)
        
        # Check if token already exists
        existing_token = FcmToken.objects.filter(fcm_token=fcm_token).first()
        
        if existing_token:
            # Update existing token
            existing_token.phone_number = phone_number
            existing_token.name = name
            existing_token.notifications_enabled = notifications_enabled
            existing_token.is_active = True
            existing_token.last_used = timezone.now()
            existing_token.save()
            
            logger.info(f"📱 FCM token updated: {phone_number}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'FCM token updated successfully',
                'user_id': existing_token.id,
                'username': existing_token.phone_number,
                'name': existing_token.name,
                'phone_number': existing_token.phone_number,
                'notifications_enabled': existing_token.notifications_enabled,
            })
        
        else:
            # Check if user with this phone number exists with different token
            existing_user = FcmToken.objects.filter(phone_number=phone_number).first()
            
            if existing_user:
                # Deactivate old token
                existing_user.is_active = False
                existing_user.save()
                logger.info(f"📱 Deactivated old token for: {phone_number}")
            
            # Create new token
            new_token = FcmToken.objects.create(
                fcm_token=fcm_token,
                phone_number=phone_number,
                name=name,
                notifications_enabled=notifications_enabled,
                is_active=True,
                last_used=timezone.now()
            )
            
            logger.info(f"📱 New FCM token registered: {phone_number}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'FCM token registered successfully',
                'user_id': new_token.id,
                'username': new_token.phone_number,
                'name': new_token.name,
                'phone_number': new_token.phone_number,
                'notifications_enabled': new_token.notifications_enabled,
            }, status=201)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        logger.error(f"❌ Error registering FCM token: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)


#!<--------------POINT HISTORY SECTION--------->
# User points and transaction history

class UserPointsHistoryView(APIView):
    """
    API endpoint to get user's points balance and transaction history
    """
    
    def normalize_phone_number(self, phone_number):
        """Normalize phone number to consistent format (+91XXXXXXXXXX)"""
        import re
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', str(phone_number))
        
        # If it starts with +91, keep as is
        if cleaned.startswith('+91'):
            return cleaned
        
        # If it starts with 91, add +
        if cleaned.startswith('91') and len(cleaned) == 12:
            return '+' + cleaned
        
        # If it's 10 digits, assume Indian number and add +91
        if len(cleaned) == 10 and cleaned.isdigit():
            return '+91' + cleaned
        
        # Return as is if we can't normalize
        return cleaned

    def create_success_response(self, user_id, total_points, history, cashback_history):
        """Create standardized success response"""
        # Remove +91 prefix from user_id for display
        display_user_id = user_id.replace('+91', '') if user_id.startswith('+91') else user_id
        
        return {
            "status": "success",  # Changed from True to "success"
            "message": "Points and cashback history fetched successfully",
            "data": {
                "user_id": display_user_id,  # Phone number without +91
                "total_points": total_points,
                "history": history,
                "cashback_history": cashback_history
            }
        }

    def create_error_response(self, message, status_code=400):
        """Create standardized error response"""
        return {
            "status": "error",  # Changed from False to "error" for consistency
            "message": message,
            "data": None
        }

    def get_enhanced_lottery_name(self, transaction):
        """Get enhanced lottery name with draw number like 'Akshaya AK 620'"""
        from .models import LotteryResult
        
        try:
            # Try to find the lottery result for this transaction
            if transaction.check_date and transaction.lottery_name:
                # Look for lottery result on the check date
                lottery_result = LotteryResult.objects.filter(
                    lottery__name=transaction.lottery_name,
                    date=transaction.check_date,
                    is_published=True
                ).first()
                
                if lottery_result and lottery_result.draw_number:
                    # Create enhanced name: "Lottery Name DRAW_NUMBER"
                    return f"{transaction.lottery_name} {lottery_result.draw_number}"
            
            # Fallback to original lottery name if no draw number found
            return transaction.lottery_name
            
        except Exception as e:
            # Fallback to original name if any error occurs
            logger.warning(f"⚠️ Could not enhance lottery name: {e}")
            return transaction.lottery_name

    def post(self, request):
        """Get user points and history"""
        from .serializers import UserPointsHistorySerializer
        from .models import UserPointsBalance, PointsTransaction, DailyCashAwarded
        
        try:
            # Validate request data
            serializer = UserPointsHistorySerializer(data=request.data)
            
            if not serializer.is_valid():
                error_response = self.create_error_response(
                    f"Invalid data: {serializer.errors}"
                )
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
            
            # Get validated data
            phone_number = serializer.validated_data['phone_number']
            limit = serializer.validated_data.get('limit', 50)
            
            # Normalize phone number
            normalized_phone = self.normalize_phone_number(phone_number)
            
            # Get user points balance
            try:
                user_balance = UserPointsBalance.objects.get(phone_number=normalized_phone)
                total_points = user_balance.total_points
                user_id = normalized_phone  # Using phone as user_id as per your example
            except UserPointsBalance.DoesNotExist:
                # User doesn't have points balance, but might have cashback - set points to 0
                total_points = 0
                user_id = normalized_phone
            
            # Get transaction history (only lottery check rewards)
            transactions = PointsTransaction.objects.filter(
                phone_number=normalized_phone,
                transaction_type='lottery_check',  # Only lottery check rewards
                points_amount__gt=0  # Only positive point earnings
            ).order_by('-created_at')[:limit]
            
            # Format history with enhanced lottery names
            history = []
            for transaction in transactions:
                # Get enhanced lottery name with draw number
                enhanced_lottery_name = self.get_enhanced_lottery_name(transaction)
                
                history_item = {
                    "lottery_name": enhanced_lottery_name,
                    "date": str(transaction.check_date) if transaction.check_date else str(transaction.created_at.date()),
                    "points_earned": transaction.points_amount
                }
                history.append(history_item)
            
            # Get cashback history for this user
            cashback_records = DailyCashAwarded.objects.filter(
                phone_number=normalized_phone
            ).order_by('-award_date')[:limit]
            
            # Format cashback history
            cashback_history = []
            for cashback in cashback_records:
                cashback_item = {
                    "cashback_id": cashback.cashback_id or f"CB{cashback.id:06d}",  # Fallback for existing records
                    "date": str(cashback.award_date),
                    "amount": float(cashback.cash_awarded),
                    "isClaimed": cashback.is_claimed
                }
                cashback_history.append(cashback_item)
            
            # Create success response
            response_data = self.create_success_response(
                user_id=user_id,
                total_points=total_points,
                history=history,
                cashback_history=cashback_history
            )
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Log the error for debugging
            logger.error(f"❌ Error in UserPointsHistoryView: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            error_response = self.create_error_response(
                "An unexpected error occurred. Please try again later."
            )
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)