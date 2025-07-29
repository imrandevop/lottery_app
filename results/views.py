# views.py
import os
import random
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from datetime import date,time
from django.utils.timezone import now, localtime
import uuid
from .models import Lottery, LotteryResult, PrizeEntry, ImageUpdate, News, PredictionHistory
from .models import PrizeEntry, LiveVideo
from django.db.models import Q, Sum
from .serializers import LotteryResultSerializer, LotteryResultDetailSerializer
from django.contrib.auth import get_user_model
from .serializers import TicketCheckSerializer, NewsSerializer
from .prediction_engine import LotteryPredictionEngine
from .serializers import LotteryPredictionRequestSerializer, LiveVideoSerializer
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
    Enhanced API endpoint to check Kerala lottery tickets with points system
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

    def create_standard_response(self, status_code, status, result_status, message, points, data):
        """Create standardized response format with points"""
        return {
            "statusCode": status_code,
            "status": status,
            "resultStatus": result_status,
            "message": message,
            "points": points,  # Now includes actual points or None
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

    def calculate_points_award(self, ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist):
        """
        Calculate points based on 6 strict rules - ALL must be met
        Returns: (points_awarded, reason) tuple
        """
        from .models import DailyPointsPool, DailyPointsAwarded, UserPointsBalance, PointsTransaction
        
        # Normalize phone number for consistency
        normalized_phone = self.normalize_phone_number(phone_number)
        
        # Rule 1: Non-Winners Only
        if won_prize:
            return (None, "Points only awarded to non-winning tickets")
        
        # Rule 2: Today's Lottery Only
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        if check_date != today_ist:
            return (None, "Points only awarded for today's lottery check")
        
        # Rule 3: Time Restriction (After 3:00 PM IST)
        result_publish_time = time(15, 0)  # 3:00 PM
        if current_time_ist < result_publish_time:
            return (None, "Points awarded only after 3:00 PM IST")
        
        # Rule 4: One Award Per User Per Day
        if DailyPointsAwarded.has_received_points_today(normalized_phone):
            return (None, "Points already awarded today for this phone number")
        
        # Rule 5: Daily Pool Budget Control
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
        """Enhanced post method with points system integration"""
        from .serializers import TicketCheckSerializer
        from .models import Lottery, LotteryResult
        
        try:
            serializer = TicketCheckSerializer(data=request.data)

            if not serializer.is_valid():
                error_data = self.create_data_structure("", "", "", False, False, False)
                response = self.create_standard_response(
                    400, "fail", "Validation Error", 
                    f"Invalid data: {serializer.errors}", None, error_data
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
                    "Invalid ticket number format", None, error_data
                )
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            lottery_code = ticket_number[0].upper()

            # Validate lottery code
            if not self.get_expected_lottery_day(lottery_code):
                error_data = self.create_data_structure(ticket_number, "", str(check_date), False, False, False)
                response = self.create_standard_response(
                    400, "fail", "Invalid Lottery Code", 
                    f"Invalid lottery code: {lottery_code}", None, error_data
                )
                return Response(response, status=status.HTTP_400_BAD_REQUEST)

            try:
                lottery = Lottery.objects.get(code=lottery_code)
            except Lottery.DoesNotExist:
                error_data = self.create_data_structure(ticket_number, "", str(check_date), False, False, False)
                response = self.create_standard_response(
                    400, "fail", "Lottery Not Found", 
                    f'Lottery with code "{lottery_code}" not found', None, error_data
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
                "An unexpected error occurred. Please try again later.", None, error_data
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
            message, None, data  # No points when result not published
        )
        return Response(response, status=status.HTTP_200_OK)

    def handle_exact_date_result(self, lottery, ticket_number, phone_number, check_date, lottery_result, is_today, current_time_ist):
        """Handle case when result exists for the exact requested date"""
        # Check if ticket won
        prize_data = self.check_ticket_prizes(ticket_number, lottery_result)
        won_prize = bool(prize_data)
        
        # Calculate points (only for today's non-winning tickets after 3 PM)
        points_awarded = None
        if is_today:
            calculated_points, points_reason = self.calculate_points_award(
                ticket_number, phone_number, check_date, won_prize, is_today, current_time_ist
            )
            
            if calculated_points:
                # Award points to user
                award_success, award_message = self.award_points_to_user(
                    phone_number, calculated_points, ticket_number, lottery.name, check_date
                )
                
                if award_success:
                    points_awarded = calculated_points
                    logger.info(f"✅ Points awarded: {phone_number} +{calculated_points} pts")
                else:
                    logger.warning(f"⚠️ Points calculation passed but award failed: {award_message}")
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
                200, "success", result_status, message, points_awarded, data
            )
        else:
            # No prize on requested date
            if is_today:
                result_status = "No Price Today"
                base_message = "Better luck next time"
                if points_awarded:
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
                200, "success", result_status, message, points_awarded, data
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
                "No result data found on database", None, data  # No points for previous results
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        # Check if ticket won in the most recent result
        prize_data = self.check_ticket_prizes(ticket_number, previous_result)
        
        # No points for previous results (Rule 2: Today's Lottery Only)
        
        if prize_data:
            # Won in most recent result
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                True, False, True, previous_result, prize_data
            )
            message = f"Congratulations! You won ₹{prize_data['total_amount']:,.0f} in the latest {lottery.name} draw."
            response = self.create_standard_response(
                200, "success", "Previous Result", message, None, data  # No points for previous results
            )
        else:
            # No prize in most recent result
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                False, False, True, previous_result, None
            )
            response = self.create_standard_response(
                200, "success", "Previous Result no price", 
                "Better luck next time", None, data  # No points for previous results
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
class PredictionRateThrottle(AnonRateThrottle):
    scope = 'prediction'

class LotteryPredictionAPIView(APIView):
    """
    API View for lottery number prediction with stable predictions and accuracy tracking
    """
    throttle_classes = [PredictionRateThrottle]
    throttle_scope = 'prediction'
    
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

    def get_lottery_day(self, lottery_name):
        """Get the scheduled day for a lottery based on its code"""
        try:
            lottery = Lottery.objects.get(name__iexact=lottery_name)
            lottery_code = lottery.code.upper() if lottery.code else None
            return self.LOTTERY_DAYS.get(lottery_code) if lottery_code else None
        except Lottery.DoesNotExist:
            return None

    def should_generate_new_prediction(self, lottery_name, prize_type):
        """
        Determine if we need to generate new predictions based on:
        1. New result published since last prediction
        2. 3:00 PM IST on lottery's scheduled day has passed
        """
        india_tz = pytz.timezone('Asia/Kolkata')
        current_datetime = timezone.now().astimezone(india_tz)
        current_date = current_datetime.date()
        current_time = current_datetime.time()
        result_publish_time = time(15, 0)  # 3:00 PM IST
        
        # Get the most recent prediction for this lottery and prize type
        latest_prediction = PredictionHistory.objects.filter(
            lottery_name__iexact=lottery_name,
            prize_type=prize_type
        ).order_by('-prediction_date').first()
        
        if not latest_prediction:
            return True  # No previous prediction exists
        
        # Get the lottery day
        lottery_day = self.get_lottery_day(lottery_name)
        if not lottery_day:
            return True  # Unknown lottery, generate new prediction
        
        # Check if there's a new published result since the last prediction
        try:
            lottery = Lottery.objects.get(name__iexact=lottery_name)
            latest_result = LotteryResult.objects.filter(
                lottery=lottery,
                is_published=True,
                date__gte=latest_prediction.prediction_date.date()
            ).order_by('-date', '-updated_at').first()
            
            if latest_result and latest_result.updated_at > latest_prediction.prediction_date:
                return True  # New result published since last prediction
        except Lottery.DoesNotExist:
            return True
        
        # Check if we've passed 3:00 PM on the lottery's scheduled day
        prediction_date = latest_prediction.prediction_date.astimezone(india_tz).date()
        
        # Find the next lottery day after the prediction was made
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        lottery_day_index = days_of_week.index(lottery_day)
        
        # Calculate days since prediction
        days_since_prediction = (current_date - prediction_date).days
        
        if days_since_prediction >= 7:
            return True  # More than a week has passed
        
        # Check if it's the lottery day and past 3:00 PM
        current_day = current_date.strftime('%A').lower()
        if current_day == lottery_day and current_time >= result_publish_time:
            # Check if we haven't generated a prediction for this cycle yet
            if prediction_date < current_date:
                return True
        
        return False

    def get_stable_prediction(self, lottery_name, prize_type):
        """Get stable prediction with caching - MUCH FASTER"""
        if self.should_generate_new_prediction(lottery_name, prize_type):
            # Generate new prediction
            try:
                engine = LotteryPredictionEngine()
                # Use the new cached method
                result = engine.predict_with_cache(lottery_name, prize_type, method='ensemble')
                
                # Store new prediction
                PredictionHistory.objects.create(
                    lottery_name=lottery_name,
                    prize_type=prize_type,
                    predicted_numbers=result['predictions'],
                    prediction_date=timezone.now()
                )
                
                return result
            except Exception as e:
                raise e
        else:
            # Check cache first before database
            from results.utils.cache_utils import get_cached_prediction
            cached_result = get_cached_prediction(lottery_name, prize_type)
            
            if cached_result:
                return cached_result
            
            # Return existing stable prediction from database
            latest_prediction = PredictionHistory.objects.filter(
                lottery_name__iexact=lottery_name,
                prize_type=prize_type
            ).order_by('-prediction_date').first()
            
            if latest_prediction:
                # Recreate the result format and cache it
                engine = LotteryPredictionEngine()
                repeated_numbers = []
                if prize_type != 'consolation':
                    repeated_numbers = engine.get_repeated_numbers(lottery_name, prize_type, 12)
                
                result = {
                    'predictions': latest_prediction.predicted_numbers,
                    'repeated_numbers': repeated_numbers,
                    'confidence': 0.65,
                    'method': 'ensemble',
                    'historical_data_count': 0,
                    'lottery_code': None
                }
                
                # Cache this result
                from results.utils.cache_utils import cache_prediction
                cache_prediction(lottery_name, prize_type, result, timeout=3600)
                
                return result
            else:
                # Fallback - generate new
                engine = LotteryPredictionEngine()
                result = engine.predict_with_cache(lottery_name, prize_type, method='ensemble')
                
                PredictionHistory.objects.create(
                    lottery_name=lottery_name,
                    prize_type=prize_type,
                    predicted_numbers=result['predictions'],
                    prediction_date=timezone.now()
                )
                
                return result

    # Fixed accuracy calculation method - replace the existing one


    def calculate_prediction_accuracy(self, lottery_name, prize_type):
        """
        FIXED: Calculate accuracy with proper format handling
        """
        try:
            lottery = Lottery.objects.get(name__iexact=lottery_name)
            
            # Get the most recently published result
            latest_result = LotteryResult.objects.filter(
                lottery=lottery,
                is_published=True
            ).order_by('-date', '-updated_at').first()
            
            if not latest_result:
                return None
            
            # Get the most recent prediction before this result
            prediction = PredictionHistory.objects.filter(
                lottery_name__iexact=lottery_name,
                prize_type=prize_type,
                prediction_date__lte=latest_result.updated_at
            ).order_by('-prediction_date').first()
            
            if not prediction:
                return None
            
            # FIXED: Get winning numbers for the EXACT prize type only
            winning_numbers = list(PrizeEntry.objects.filter(
                lottery_result=latest_result,
                prize_type=prize_type  # Exact match only
            ).values_list('ticket_number', flat=True))
            
            if not winning_numbers:
                return None
            
            # FIXED: Format winning numbers based on prize type
            winning_formatted = []
            for num in winning_numbers:
                if num:
                    num_str = str(num).strip().upper()
                    
                    if prize_type in ['1st', '2nd', '3rd']:
                        # For 1st-3rd prizes: use full format (e.g., "DU350667")
                        if len(num_str) >= 6:  # Valid full format
                            winning_formatted.append(num_str)
                    else:
                        # For 4th-10th prizes: ensure 4-digit format with leading zeros
                        if len(num_str) <= 4 and num_str.isdigit():
                            winning_formatted.append(num_str.zfill(4))
            
            if not winning_formatted:
                return None
            
            # FIXED: Format predicted numbers to match winning number format
            predicted_numbers = prediction.predicted_numbers
            if not predicted_numbers:
                return None
            
            predicted_formatted = []
            for pred_num in predicted_numbers:
                pred_str = str(pred_num).strip().upper()
                
                if prize_type in ['1st', '2nd', '3rd']:
                    # For 1st-3rd prizes: use full format as is
                    predicted_formatted.append(pred_str)
                else:
                    # For 4th-10th prizes: extract last 4 digits and zero-pad
                    pred_last_4 = pred_str[-4:] if len(pred_str) >= 4 else pred_str
                    if pred_last_4.isdigit():
                        predicted_formatted.append(pred_last_4.zfill(4))
            
            # Compare predictions with winning numbers
            accuracy_results = {
                "100%": [],
                "75%": [],
                "50%": [],
                "25%": []
            }
            
            perfect_matches = 0
            total_accuracy_points = 0
            
            for pred_num in predicted_formatted:
                best_match_percentage = 0
                
                for winning_num in winning_formatted:
                    if prize_type in ['1st', '2nd', '3rd']:
                        # Full format comparison for 1st-3rd prizes
                        if pred_num == winning_num:
                            match_percentage = 100
                        elif len(pred_num) >= 6 and len(winning_num) >= 6:
                            # Partial matching: check how many positions match
                            min_len = min(len(pred_num), len(winning_num))
                            match_count = sum(1 for i in range(min_len) 
                                            if pred_num[i] == winning_num[i])
                            
                            if match_count == min_len:
                                match_percentage = 100
                            elif match_count >= min_len * 0.75:
                                match_percentage = 75
                            elif match_count >= min_len * 0.5:
                                match_percentage = 50
                            elif match_count >= min_len * 0.25:
                                match_percentage = 25
                            else:
                                match_percentage = 0
                        else:
                            match_percentage = 0
                    else:
                        # 4-digit comparison for 4th-10th prizes
                        match_count = sum(1 for i, digit in enumerate(pred_num) 
                                        if i < len(winning_num) and digit == winning_num[i])
                        
                        if match_count == 4:
                            match_percentage = 100
                        elif match_count == 3:
                            match_percentage = 75
                        elif match_count == 2:
                            match_percentage = 50
                        elif match_count == 1:
                            match_percentage = 25
                        else:
                            match_percentage = 0
                    
                    best_match_percentage = max(best_match_percentage, match_percentage)
                
                # Categorize the prediction
                if best_match_percentage == 100:
                    accuracy_results["100%"].append(pred_num)
                    perfect_matches += 1
                    total_accuracy_points += 100
                elif best_match_percentage == 75:
                    accuracy_results["75%"].append(pred_num)
                    total_accuracy_points += 75
                elif best_match_percentage == 50:
                    accuracy_results["50%"].append(pred_num)
                    total_accuracy_points += 50
                elif best_match_percentage == 25:
                    accuracy_results["25%"].append(pred_num)
                    total_accuracy_points += 25
            
            # Calculate overall accuracy percentage
            total_predictions = len(predicted_formatted)
            overall_accuracy = (total_accuracy_points / (total_predictions * 100)) * 100 if total_predictions > 0 else 0
            
            return {
                "date": str(latest_result.date),
                "summary": {
                    "perfect_match_count": perfect_matches,
                    "overall_accuracy_percent": round(overall_accuracy, 2)
                },
                "digit_accuracy": accuracy_results
            }
            
        except Lottery.DoesNotExist:
            return None
        except Exception as e:
            return None
    
    def calculate_comprehensive_accuracy(self, lottery_name, prize_type):
        """
        BONUS: Calculate accuracy showing ALL matches, not just best matches
        This gives a more complete picture of prediction performance
        """
        try:
            lottery = Lottery.objects.get(name__iexact=lottery_name)
            
            # Get the most recently published result
            latest_result = LotteryResult.objects.filter(
                lottery=lottery,
                is_published=True
            ).order_by('-date', '-updated_at').first()
            
            if not latest_result:
                return None
            
            # Get all predictions for this lottery/prize type in the last 30 days
            from datetime import timedelta
            cutoff_date = latest_result.date - timedelta(days=30)
            
            predictions = PredictionHistory.objects.filter(
                lottery_name__iexact=lottery_name,
                prize_type=prize_type,
                prediction_date__gte=cutoff_date,
                prediction_date__lte=latest_result.updated_at
            ).order_by('-prediction_date')
            
            if not predictions:
                return None
            
            # Get winning numbers
            winning_entries = PrizeEntry.objects.filter(
                lottery_result=latest_result,
                prize_type=prize_type
            ).values_list('ticket_number', flat=True)
            
            winning_numbers = [str(num).strip() for num in winning_entries if num]
            
            comprehensive_results = {
                "all_matches": {
                    "100%": [],
                    "75%": [],
                    "50%": [],
                    "25%": [],
                    "0%": []
                },
                "prediction_history": []
            }
            
            # Analyze each prediction
            for prediction in predictions:
                prediction_analysis = {
                    "prediction_date": prediction.prediction_date.isoformat(),
                    "predicted_numbers": prediction.predicted_numbers,
                    "matches": []
                }
                
                for pred_num in prediction.predicted_numbers:
                    pred_str = str(pred_num).strip().upper()
                    
                    # Format based on prize type
                    if prize_type in ['1st', '2nd', '3rd']:
                        pred_compare = pred_str
                    else:
                        pred_compare = pred_str[-4:] if len(pred_str) >= 4 else pred_str.zfill(4)
                    
                    # Check against all winning numbers
                    all_matches_for_this_pred = []
                    
                    for winning_num in winning_numbers:
                        winning_str = str(winning_num).strip().upper()
                        
                        if prize_type in ['1st', '2nd', '3rd']:
                            winning_compare = winning_str
                            max_len = max(len(pred_compare), len(winning_compare))
                            pred_padded = pred_compare.ljust(max_len, '0')[:max_len]
                            winning_padded = winning_compare.ljust(max_len, '0')[:max_len]
                            match_count = sum(1 for p, w in zip(pred_padded, winning_padded) if p == w)
                            total_positions = max_len
                        else:
                            winning_compare = winning_str[-4:] if len(winning_str) >= 4 else winning_str.zfill(4)
                            match_count = sum(1 for p, w in zip(pred_compare, winning_compare) if p == w)
                            total_positions = 4
                        
                        if total_positions > 0:
                            match_ratio = match_count / total_positions
                            
                            if match_ratio == 1.0:
                                match_percentage = 100
                            elif match_ratio >= 0.75:
                                match_percentage = 75
                            elif match_ratio >= 0.5:
                                match_percentage = 50
                            elif match_ratio >= 0.25:
                                match_percentage = 25
                            else:
                                match_percentage = 0
                            
                            if match_percentage > 0:
                                all_matches_for_this_pred.append({
                                    "winning_number": winning_compare,
                                    "match_percentage": match_percentage,
                                    "matches": match_count,
                                    "total_positions": total_positions
                                })
                    
                    # Record ALL matches for this prediction
                    for match in all_matches_for_this_pred:
                        percentage_key = f"{match['match_percentage']}%"
                        comprehensive_results["all_matches"][percentage_key].append({
                            "predicted": pred_compare,
                            "winning": match["winning_number"],
                            "match_count": match["matches"],
                            "total_positions": match["total_positions"]
                        })
                    
                    # If no matches found, record as 0%
                    if not all_matches_for_this_pred:
                        comprehensive_results["all_matches"]["0%"].append({
                            "predicted": pred_compare,
                            "no_matches": True
                        })
                    
                    prediction_analysis["matches"] = all_matches_for_this_pred
                
                comprehensive_results["prediction_history"].append(prediction_analysis)
            
            # Calculate comprehensive statistics
            total_matches = sum(len(matches) for matches in comprehensive_results["all_matches"].values())
            
            comprehensive_stats = {
                "total_comparisons": total_matches,
                "match_distribution": {
                    percentage: len(matches) for percentage, matches in comprehensive_results["all_matches"].items()
                }
            }
            
            return {
                "date": str(latest_result.date),
                "prize_type": prize_type,
                "winning_numbers": winning_numbers,
                "comprehensive_stats": comprehensive_stats,
                "all_matches": comprehensive_results["all_matches"],
                "recent_predictions": comprehensive_results["prediction_history"][:3]  # Last 3 predictions
            }
            
        except Exception as e:
            return {
                "error": f"Comprehensive accuracy calculation failed: {str(e)}"
            }
        
    def get_accuracy_explanation(self, prize_type, comparison_method):
        """
        Provide clear explanation of how accuracy is calculated
        """
        explanations = {
            'full_format': {
                '1st': 'Compares full ticket format (e.g., "KR123456") against 1st prize winner',
                '2nd': 'Compares full ticket format (e.g., "KA789012") against 2nd prize winner', 
                '3rd': 'Compares full ticket format (e.g., "KN345678") against 3rd prize winner'
            },
            'last_4_digits': {
                '4th': 'Compares last 4 digits against 4th prize winners',
                '5th': 'Compares last 4 digits against 5th prize winners',
                '6th': 'Compares last 4 digits against 6th prize winners',
                '7th': 'Compares last 4 digits against 7th prize winners',
                '8th': 'Compares last 4 digits against 8th prize winners',
                '9th': 'Compares last 4 digits against 9th prize winners',
                '10th': 'Compares last 4 digits against 10th prize winners'
            }
        }
        
        method_explanations = explanations.get(comparison_method, {})
        return method_explanations.get(prize_type, f'Compares predicted numbers against {prize_type} prize winners using {comparison_method} method')




    def post(self, request):
        """
        Generate stable lottery predictions with accuracy tracking
        KEEPS EXACT SAME RESPONSE FORMAT
        """
        # Validate input
        serializer = LotteryPredictionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid input data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        lottery_name = serializer.validated_data['lottery_name']
        prize_type = serializer.validated_data['prize_type']
        
        try:
            # Get stable prediction
            result = self.get_stable_prediction(lottery_name, prize_type)
            
            # Calculate accuracy for the most recent result (FIXED INTERNALLY)
            accuracy_data = self.calculate_prediction_accuracy(lottery_name, prize_type)
            
            # Build response data (KEEPING EXISTING STRUCTURE)
            response_data = {
                'status': 'success',
                'lottery_name': lottery_name,
                'prize_type': prize_type,
                'predicted_numbers': result['predictions'],
            }
            
            # Add repeated numbers for all prize types EXCEPT consolation
            if prize_type != 'consolation':
                response_data['repeated_numbers'] = result.get('repeated_numbers', [])
            
            # Add accuracy field (SAME NAME AND STRUCTURE)
            if accuracy_data:
                response_data['yesterday_prediction_accuracy'] = accuracy_data
            
            # Add note at the end
            response_data['note'] = 'Predictions are based on statistical analysis of historical data. Lottery outcomes are random and these predictions are for entertainment purposes only.'
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            # Handle lottery not found error
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Handle any other unexpected errors
            return Response({
                'status': 'error',
                'message': f'Prediction generation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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
    
import hashlib
import re
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)

class LotteryWinningPercentageAPI(APIView):
    """
    Simple frequency-based lottery percentage API
    """
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.number_pattern = re.compile(r'^[A-Z]{2}\d{6}$')
        self.base_percentage = 10.0  # Base percentage for any number
    
    def get_consistency_seed(self, lottery_name, lottery_number):
        """Generate consistent seed that changes only when new results are published"""
        try:
            # Get the latest result date across ALL lotteries for consistency
            latest_result = LotteryResult.objects.filter(
                is_published=True
            ).order_by('-date').first()
            
            if latest_result:
                seed_string = f"{lottery_number}_{latest_result.date}"
            else:
                # Fallback to current week
                current_week = timezone.now().strftime("%Y-%U")
                seed_string = f"{lottery_number}_{current_week}"
            
            # Generate consistent hash
            return int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
            
        except Exception as e:
            logger.error(f"Error generating consistency seed: {e}")
            # Fallback seed
            fallback = f"{lottery_number}_{timezone.now().strftime('%Y-%U')}"
            return int(hashlib.md5(fallback.encode()).hexdigest()[:8], 16)
    
    def get_all_winning_numbers(self):
        """Get ALL winning numbers from ALL lotteries"""
        try:
            # Get all winning numbers from all lotteries (last 2 years for performance)
            two_years_ago = timezone.now().date() - timedelta(days=730)
            
            all_winners = PrizeEntry.objects.filter(
                lottery_result__is_published=True,
                lottery_result__date__gte=two_years_ago,
                prize_type__in=['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', 'consolation']
            ).values('ticket_number')
            
            return list(all_winners)
            
        except Exception as e:
            logger.error(f"Error fetching all winning numbers: {e}")
            return []
    
    def calculate_frequency_percentage(self, lottery_name, lottery_number, all_winning_numbers):
        """Calculate percentage based on last 4 digits frequency"""
        try:
            if not self.number_pattern.match(lottery_number):
                return self.base_percentage
            
            # Get last 4 digits of target number
            target_last_4 = lottery_number[4:]  # Last 4 digits (positions 4,5,6,7)
            
            # Count how many times these last 4 digits appeared
            frequency_count = 0
            total_valid_numbers = 0
            
            for entry in all_winning_numbers:
                ticket_num = str(entry['ticket_number']).upper().strip()
                
                # Check if it's valid 8-character format
                if self.number_pattern.match(ticket_num):
                    total_valid_numbers += 1
                    
                    # Check if last 4 digits match
                    if ticket_num[4:] == target_last_4:
                        frequency_count += 1
            
            if total_valid_numbers == 0:
                return self.base_percentage
            
            # Calculate frequency percentage
            frequency_rate = frequency_count / total_valid_numbers
            
            # Convert to percentage with boost
            # Base percentage + frequency boost (scaled appropriately)
            frequency_boost = frequency_rate * 1000  # Scale up the frequency
            
            final_percentage = self.base_percentage + frequency_boost
            
            # Apply consistency seed for same results
            seed = self.get_consistency_seed(lottery_name, lottery_number)
            import random
            random.seed(seed)
            
            # Add small consistent variation (±5%) to avoid identical percentages
            variation = random.uniform(-5, 5)
            final_percentage += variation
            
            # Ensure reasonable range (1-95%)
            final_percentage = max(1.0, min(final_percentage, 95.0))
            
            return final_percentage
            
        except Exception as e:
            logger.error(f"Error calculating frequency percentage: {e}")
            return self.base_percentage
    
    def generate_message(self, percentage, lottery_number):
        """Generate message based on percentage"""
        last_4 = lottery_number[4:]
        
        if percentage >= 80:
            messages = [
                f"🎯 Excellent! Last 4 digits '{last_4}' have appeared frequently in winners!",
                f"🔥 Hot digits! '{last_4}' shows high winning frequency!",
                f"⭐ Great choice! '{last_4}' has strong historical performance!"
            ]
        elif percentage >= 60:
            messages = [
                f"👍 Good! Last 4 digits '{last_4}' have good winning history!",
                f"✨ Nice! '{last_4}' shows decent frequency in winners!",
                f"🎯 Promising! '{last_4}' has appeared multiple times!"
            ]
        elif percentage >= 40:
            messages = [
                f"⚖️ Moderate! '{last_4}' has average appearance frequency.",
                f"📊 Fair chance! '{last_4}' shows moderate winning history.",
                f"🤔 Average! '{last_4}' has appeared occasionally in winners."
            ]
        elif percentage >= 20:
            messages = [
                f"📉 Below average! '{last_4}' has low frequency in winners.",
                f"⚠️ Limited! '{last_4}' rarely appears in winning numbers.",
                f"🔍 Low frequency! '{last_4}' has minimal winning history."
            ]
        else:
            messages = [
                f"❌ Very low! '{last_4}' rarely appears in winning numbers.",
                f"🚫 Poor frequency! '{last_4}' has very limited winning history.",
                f"💭 Consider other options! '{last_4}' shows low frequency."
            ]
        
        # Use consistent message selection
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
            
            # Check if lottery exists (for response, but we check ALL lotteries for data)
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
            
            # Get ALL winning numbers from ALL lotteries
            all_winning_numbers = self.get_all_winning_numbers()
            
            if not all_winning_numbers:
                return Response({
                    'lottery_number': lottery_number,
                    'lottery_name': lottery.name,
                    'percentage': self.base_percentage,
                    'message': f'No historical data available. Showing base probability.',
                    'status': 'success'
                })
            
            # Calculate frequency-based percentage
            percentage = self.calculate_frequency_percentage(
                lottery_name, lottery_number, all_winning_numbers
            )
            
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


@csrf_exempt
@require_http_methods(["POST"])
def debug_fcm_register(request):
    """Debug version of FCM registration"""
    try:
        # Log the request
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request body: {request.body}")
        logger.info(f"Content type: {request.content_type}")
        
        # Try to parse JSON
        try:
            data = json.loads(request.body)
            logger.info(f"Parsed data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid JSON: {str(e)}'
            }, status=400)
        
        # Check required fields
        fcm_token = data.get('fcm_token')
        phone_number = data.get('phone_number')
        name = data.get('name')
        
        logger.info(f"Fields - token: {bool(fcm_token)}, phone: {bool(phone_number)}, name: {bool(name)}")
        
        if not all([fcm_token, phone_number, name]):
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields: fcm_token, phone_number, name'
            }, status=400)
        
        # Try to import model
        try:
            from .models import FcmToken
            logger.info("FcmToken model imported successfully")
        except ImportError as e:
            logger.error(f"Model import error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Model import error: {str(e)}'
            }, status=500)
        
        # Try simple database operation
        try:
            token_count = FcmToken.objects.count()
            logger.info(f"Current token count: {token_count}")
        except Exception as e:
            logger.error(f"Database error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Database error: {str(e)}'
            }, status=500)
        
        # If we get here, everything is working
        return JsonResponse({
            'status': 'success',
            'message': 'Debug successful - all systems working',
            'data_received': data,
            'current_tokens': token_count
        })
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def test_send_notification(request):
    """Test sending notifications using working direct method"""
    try:
        from firebase_admin import messaging
        from .models import FcmToken
        
        data = json.loads(request.body)
        title = data.get('title', 'Test Notification')
        body = data.get('body', 'This is a test notification from your lottery app!')
        
        # Get active tokens
        tokens = list(FcmToken.objects.filter(
            is_active=True,
            notifications_enabled=True
        ).values_list('fcm_token', flat=True))
        
        if not tokens:
            return JsonResponse({
                'status': 'error',
                'message': 'No active tokens found'
            })
        
        # Send using proven working method
        success_count = 0
        failure_count = 0
        
        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data={
                        'type': 'test_notification',
                        'timestamp': str(timezone.now())
                    },
                    token=token,
                )
                
                response = messaging.send(message)
                success_count += 1
                logger.info(f"✅ Notification sent successfully: {response}")
                
            except Exception as e:
                failure_count += 1
                logger.error(f"❌ Notification failed for token: {e}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Test notification sent',
            'result': {
                'success_count': success_count,
                'failure_count': failure_count,
                'message': f'Sent to {success_count}/{len(tokens)} devices'
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
def firebase_status(request):
    """Check Firebase initialization status"""
    try:
        import firebase_admin
        
        return JsonResponse({
            'firebase_apps': len(firebase_admin._apps),
            'firebase_initialized': bool(firebase_admin._apps),
            'environment_vars': {
                'FIREBASE_PROJECT_ID': bool(os.environ.get('FIREBASE_PROJECT_ID')),
                'FIREBASE_PRIVATE_KEY_ID': bool(os.environ.get('FIREBASE_PRIVATE_KEY_ID')),
                'FIREBASE_CLIENT_EMAIL': bool(os.environ.get('FIREBASE_CLIENT_EMAIL')),
                'FIREBASE_PRIVATE_KEY': bool(os.environ.get('FIREBASE_PRIVATE_KEY')),
            },
            'firebase_service_test_mode': getattr(FCMService, '_test_mode', 'Unknown')
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@csrf_exempt
def list_fcm_tokens(request):
    """List all FCM tokens in database"""
    try:
        from .models import FcmToken
        
        tokens = FcmToken.objects.filter(is_active=True).values(
            'id', 'name', 'phone_number', 'fcm_token', 'notifications_enabled', 'created_at'
        )
        
        # Mask the tokens for security (show first 20 chars only)
        masked_tokens = []
        for token in tokens:
            masked_token = dict(token)
            if masked_token['fcm_token']:
                masked_token['fcm_token'] = masked_token['fcm_token'][:20] + '...'
            masked_tokens.append(masked_token)
        
        return JsonResponse({
            'status': 'success',
            'count': len(masked_tokens),
            'tokens': masked_tokens
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@csrf_exempt
@require_http_methods(["POST"])
def test_send_with_details(request):
    """Test sending with detailed error reporting"""
    try:
        from firebase_admin import messaging
        from .models import FcmToken
        
        data = json.loads(request.body)
        title = data.get('title', 'Test Notification')
        body = data.get('body', 'Testing detailed FCM sending')
        
        # Get all active tokens
        tokens = list(FcmToken.objects.filter(
            is_active=True,
            notifications_enabled=True
        ).values_list('fcm_token', flat=True))
        
        if not tokens:
            return JsonResponse({
                'status': 'error',
                'message': 'No active tokens found'
            })
        
        # Test each token individually to see specific errors
        results = []
        for i, token in enumerate(tokens):
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=token,
                )
                
                response = messaging.send(message)
                results.append({
                    'token_index': i,
                    'token_preview': token[:20] + '...',
                    'status': 'success',
                    'message_id': response
                })
                
            except Exception as e:
                results.append({
                    'token_index': i,
                    'token_preview': token[:20] + '...',
                    'status': 'error',
                    'error': str(e)
                })
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        failure_count = len(results) - success_count
        
        return JsonResponse({
            'status': 'success',
            'message': 'Detailed test completed',
            'summary': {
                'total_tokens': len(tokens),
                'success_count': success_count,
                'failure_count': failure_count
            },
            'detailed_results': results
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@csrf_exempt
def clear_test_tokens(request):
    """Clear all test/fake FCM tokens"""
    try:
        from .models import FcmToken
        
        # Delete tokens that look like test tokens
        test_patterns = ['fake_', 'test_', 'sample_', 'demo_']
        
        deleted_count = 0
        deleted_details = []
        
        for pattern in test_patterns:
            tokens_to_delete = FcmToken.objects.filter(fcm_token__startswith=pattern)
            
            # Log what we're deleting
            for token in tokens_to_delete:
                deleted_details.append({
                    'id': token.id,
                    'name': token.name,
                    'phone_number': token.phone_number,
                    'token_preview': token.fcm_token[:20] + '...',
                    'pattern_matched': pattern
                })
            
            # Delete tokens matching this pattern
            deleted = tokens_to_delete.delete()
            deleted_count += deleted[0]
        
        # Get remaining token count
        remaining_count = FcmToken.objects.filter(is_active=True).count()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully cleared {deleted_count} test tokens',
            'deleted_count': deleted_count,
            'remaining_tokens': remaining_count,
            'deleted_details': deleted_details,
            'patterns_searched': test_patterns
        })
        
    except Exception as e:
        logger.error(f"Error clearing test tokens: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def test_send_direct(request):
    """Test sending using direct Firebase messaging (like the working detailed test)"""
    try:
        from firebase_admin import messaging
        from .models import FcmToken
        
        data = json.loads(request.body)
        title = data.get('title', 'Direct Test Notification')
        body = data.get('body', 'Testing direct Firebase messaging!')
        
        # Get active tokens (same as detailed test)
        tokens = list(FcmToken.objects.filter(
            is_active=True,
            notifications_enabled=True
        ).values_list('fcm_token', flat=True))
        
        if not tokens:
            return JsonResponse({
                'status': 'error',
                'message': 'No active tokens found'
            })
        
        # Use the same logic as the working detailed test
        success_count = 0
        failure_count = 0
        
        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=token,
                )
                
                response = messaging.send(message)
                success_count += 1
                logger.info(f"✅ Notification sent: {response}")
                
            except Exception as e:
                failure_count += 1
                logger.error(f"❌ Notification failed: {e}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Direct test notification sent',
            'result': {
                'success_count': success_count,
                'failure_count': failure_count,
                'message': f'Sent to {success_count}/{len(tokens)} devices'
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })



#!<--------------POINT HISTORY SECTION--------->
# Add this to your views.py file

# Add this to your views.py file

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

    def create_success_response(self, user_id, total_points, history):
        """Create standardized success response"""
        # Remove +91 prefix from user_id for display
        display_user_id = user_id.replace('+91', '') if user_id.startswith('+91') else user_id
        
        return {
            "status": "success",  # Changed from True to "success"
            "message": "Points history fetched successfully",
            "data": {
                "user_id": display_user_id,  # Phone number without +91
                "total_points": total_points,
                "history": history
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
        from .models import UserPointsBalance, PointsTransaction
        
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
                # User not found - return empty but valid response
                empty_response = self.create_success_response(
                    user_id=normalized_phone,
                    total_points=0,
                    history=[]
                )
                return Response(empty_response, status=status.HTTP_200_OK)
            
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
            
            # Create success response
            response_data = self.create_success_response(
                user_id=user_id,
                total_points=total_points,
                history=history
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