# views.py
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
from .models import PrizeEntry, LiveVideo, NotificationLog
from django.db.models import Q
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
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json



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
            'total_points': 1250,
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
    Enhanced API endpoint to check Kerala lottery tickets with standardized response format
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



    def create_standard_response(self, status_code, status, result_status, message, data):
        """Create standardized response format"""
        return {
            "statusCode": status_code,
            "status": status,
            "resultStatus": result_status,
            "message": message,
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

    def post(self, request):
        serializer = TicketCheckSerializer(data=request.data)

        if not serializer.is_valid():
            error_data = self.create_data_structure(
                "", "", "", False, False, False
            )
            response = self.create_standard_response(
                400, "fail", "Validation Error", 
                "Invalid data provided", error_data
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        ticket_number = serializer.validated_data['ticket_number']
        phone_number = serializer.validated_data['phone_number']
        check_date = serializer.validated_data['date']

        if len(ticket_number) < 1:
            error_data = self.create_data_structure(
                ticket_number, "", str(check_date), False, False, False
            )
            response = self.create_standard_response(
                400, "fail", "Invalid Ticket", 
                "Invalid ticket number format", error_data
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        lottery_code = ticket_number[0].upper()

        # Validate lottery code exists
        if not self.get_expected_lottery_day(lottery_code):
            error_data = self.create_data_structure(
                ticket_number, "", str(check_date), False, False, False
            )
            response = self.create_standard_response(
                400, "fail", "Invalid Lottery Code", 
                f"Invalid lottery code: {lottery_code}", error_data
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            lottery = Lottery.objects.get(code=lottery_code)
        except Lottery.DoesNotExist:
            error_data = self.create_data_structure(
                ticket_number, "", str(check_date), False, False, False
            )
            response = self.create_standard_response(
                400, "fail", "Lottery Not Found", 
                f'Lottery with code "{lottery_code}" not found', error_data
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        # Time and date logic (India timezone - IST)
        india_tz = pytz.timezone('Asia/Kolkata')
        current_datetime = now().astimezone(india_tz)
        current_date = current_datetime.date()
        current_time = current_datetime.time()
        result_publish_time = time(15, 0)  # 3:00 PM IST

        # Check if the requested date matches the lottery's scheduled day
        requested_day = check_date.strftime('%A').lower()
        lottery_day = self.get_expected_lottery_day(lottery_code)
        is_lottery_day_match = (requested_day == lottery_day)
        
        # Check if requested date is today's date in India
        is_today = (check_date == current_date)
        
        # PRIORITY 1: Check if result exists for the exact requested date first
        try:
            lottery_result = LotteryResult.objects.get(
                lottery=lottery,
                date=check_date,
                is_published=True
            )
            
            # Result exists for requested date - show that result
            return self.handle_exact_date_result(lottery, ticket_number, check_date, lottery_result, is_today)
            
        except LotteryResult.DoesNotExist:
            # No result for requested date
            
            if is_lottery_day_match and is_today:
                # Special case: Today's lottery with no result yet
                if current_time < result_publish_time:
                    # Before 3 PM IST - result not published yet
                    return self.handle_result_not_published_same_day(lottery, ticket_number, check_date)
                else:
                    # After 3 PM IST but no result - still not published
                    return self.handle_result_not_published_same_day(lottery, ticket_number, check_date)
            else:
                # Show most recent result of this lottery type
                return self.handle_different_day_result(lottery, ticket_number, check_date)

    def handle_result_not_published_same_day(self, lottery, ticket_number, check_date):
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
            message, data
        )
        return Response(response, status=status.HTTP_200_OK)

    def handle_exact_date_result(self, lottery, ticket_number, check_date, lottery_result, is_today):
        """Handle case when result exists for the exact requested date"""
        # Check if ticket won
        prize_data = self.check_ticket_prizes(ticket_number, lottery_result)
        
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
                200, "success", result_status, message, data
            )
        else:
            # No prize on requested date
            if is_today:
                result_status = "No Price Today"
                message = "Better luck next time"
            else:
                result_status = "Previous Result no price"
                message = "Better luck next time"
            
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                False, True, False, lottery_result, None
            )
            response = self.create_standard_response(
                200, "success", result_status, message, data
            )
        
        return Response(response, status=status.HTTP_200_OK)

    def handle_different_day_result(self, lottery, ticket_number, check_date):
        """Handle checking lottery on wrong day - always show most recent result with isPreviousResult: true"""
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
                "No result data found on database", data
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        # Check if ticket won in the most recent result
        prize_data = self.check_ticket_prizes(ticket_number, previous_result)
        
        if prize_data:
            # Won in most recent result
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                True, False, True, previous_result, prize_data
            )
            message = f"Congratulations! You won ₹{prize_data['total_amount']:,.0f} in the latest {lottery.name} draw."
            response = self.create_standard_response(
                200, "success", "Previous Result", message, data
            )
        else:
            # No prize in most recent result
            data = self.create_data_structure(
                ticket_number, lottery.name, check_date, 
                False, False, True, previous_result, None
            )
            response = self.create_standard_response(
                200, "success", "Previous Result no price", 
                "Better luck next time", data
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
    
class LotteryWinningPercentageAPI(APIView):
    """
    API to calculate winning percentage for a given lottery number using advanced algorithms
    """
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.base_probability = 0.01  # 1% base probability for any 4-digit number
    
    def extract_number_features(self, number_str):
        """Extract mathematical features from a lottery number (format: AB123456)"""
        try:
            # Validate format: 2 alphabets + 6 digits
            number_str = str(number_str).upper().strip()
            if len(number_str) != 8:
                return None
            
            # Check format: first 2 chars are alphabets, last 6 are digits
            prefix = number_str[:2]
            numeric_part = number_str[2:]
            
            if not prefix.isalpha() or not numeric_part.isdigit():
                return None
                
            digits = [int(d) for d in numeric_part]
            
            features = {
                'full_number': number_str,
                'prefix': prefix,
                'numeric_part': numeric_part,
                'digits': digits,
                'sum': sum(digits),
                'product': np.prod(digits) if 0 not in digits else 0,
                'range': max(digits) - min(digits),
                'std_dev': np.std(digits),
                'unique_count': len(set(digits)),
                'is_ascending': all(digits[i] <= digits[i+1] for i in range(5)),
                'is_descending': all(digits[i] >= digits[i+1] for i in range(5)),
                'has_repeats': len(set(digits)) < 6,
                'even_count': sum(1 for d in digits if d % 2 == 0),
                'odd_count': sum(1 for d in digits if d % 2 == 1),
                'consecutive_pairs': sum(1 for i in range(5) if abs(digits[i] - digits[i+1]) == 1),
                # Additional features for 6-digit analysis
                'first_half_sum': sum(digits[:3]),
                'second_half_sum': sum(digits[3:]),
                'alternating_sum': sum(digits[::2]) - sum(digits[1::2]),
                'last_4_digits': digits[-4:],
                'first_2_digits': digits[:2],
                'middle_2_digits': digits[2:4]
            }
            
            return features
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def frequency_analysis(self, lottery_name, target_number, historical_data):
        """Analyze frequency patterns of the target number (format: AB123456)"""
        try:
            target_number = str(target_number).upper().strip()
            
            # Validate format
            if len(target_number) != 8 or not target_number[:2].isalpha() or not target_number[2:].isdigit():
                return 0.0
            
            target_prefix = target_number[:2]
            target_numeric = target_number[2:]
            target_last_4 = target_numeric[-4:]
            
            # Analysis counters
            exact_matches = 0
            prefix_matches = 0
            numeric_matches = 0
            last_4_matches = 0
            
            # Pattern matches
            digit_frequencies = Counter()
            position_frequencies = [Counter() for _ in range(6)]  # 6 digits
            prefix_frequencies = Counter()
            
            for entry in historical_data:
                ticket_num = str(entry['ticket_number']).upper().strip()
                
                # Skip invalid formats
                if len(ticket_num) != 8 or not ticket_num[:2].isalpha() or not ticket_num[2:].isdigit():
                    continue
                
                entry_prefix = ticket_num[:2]
                entry_numeric = ticket_num[2:]
                entry_last_4 = entry_numeric[-4:]
                
                # Exact match
                if ticket_num == target_number:
                    exact_matches += 1
                
                # Prefix match
                if entry_prefix == target_prefix:
                    prefix_matches += 1
                
                # Numeric part match
                if entry_numeric == target_numeric:
                    numeric_matches += 1
                
                # Last 4 digits match
                if entry_last_4 == target_last_4:
                    last_4_matches += 1
                
                # Frequency analysis
                prefix_frequencies[entry_prefix] += 1
                for i, digit in enumerate(entry_numeric):
                    digit_frequencies[digit] += 1
                    position_frequencies[i][digit] += 1
            
            total_entries = len(historical_data)
            if total_entries == 0:
                return 0.0
            
            # Calculate frequency score
            frequency_score = 0.0
            
            # Exact match frequency (highest weight)
            exact_freq = exact_matches / total_entries
            frequency_score += exact_freq * 35  # 35% weight
            
            # Prefix frequency
            prefix_freq = prefix_matches / total_entries
            frequency_score += prefix_freq * 15  # 15% weight
            
            # Last 4 digits frequency
            last_4_freq = last_4_matches / total_entries
            frequency_score += last_4_freq * 25  # 25% weight
            
            # Digit pattern frequency
            digit_pattern_score = 0.0
            for i, digit in enumerate(target_numeric):
                position_freq = position_frequencies[i].get(digit, 0) / total_entries
                digit_pattern_score += position_freq
            
            frequency_score += (digit_pattern_score / 6) * 25  # 25% weight
            
            return min(frequency_score * 100, 95.0)  # Cap at 95%
            
        except Exception as e:
            logger.error(f"Error in frequency analysis: {e}")
            return 0.0
    
    def pattern_analysis(self, target_number, historical_data):
        """Analyze mathematical patterns in historical data"""
        try:
            target_features = self.extract_number_features(target_number)
            if not target_features:
                return 0.0
            
            pattern_scores = []
            
            for entry in historical_data:
                entry_features = self.extract_number_features(entry['ticket_number'])
                if not entry_features:
                    continue
                
                # Calculate similarity score
                similarity = 0.0
                
                # Sum similarity (normalized for 6 digits)
                sum_diff = abs(target_features['sum'] - entry_features['sum'])
                sum_similarity = max(0, 1 - (sum_diff / 54))  # Max diff is 54 (999999 vs 000000)
                similarity += sum_similarity * 0.2
                
                # Range similarity
                range_diff = abs(target_features['range'] - entry_features['range'])
                range_similarity = max(0, 1 - (range_diff / 9))  # Max diff is 9
                similarity += range_similarity * 0.15
                
                # Unique count similarity
                unique_similarity = 1 if target_features['unique_count'] == entry_features['unique_count'] else 0
                similarity += unique_similarity * 0.15
                
                # Prefix similarity (new for 8-char format)
                prefix_similarity = 1 if target_features['prefix'] == entry_features['prefix'] else 0
                similarity += prefix_similarity * 0.25
                
                # Last 4 digits pattern similarity
                last_4_target = target_features['last_4_digits']
                last_4_entry = entry_features['last_4_digits']
                last_4_similarity = sum(1 for i, d in enumerate(last_4_target) if i < len(last_4_entry) and d == last_4_entry[i]) / 4
                similarity += last_4_similarity * 0.25
                
                # Pattern type similarity
                pattern_similarity = 0
                if target_features['is_ascending'] and entry_features['is_ascending']:
                    pattern_similarity = 1
                elif target_features['is_descending'] and entry_features['is_descending']:
                    pattern_similarity = 1
                elif target_features['has_repeats'] and entry_features['has_repeats']:
                    pattern_similarity = 0.7
                
                # Additional pattern checks for 6-digit numbers
                if target_features['first_half_sum'] == entry_features['first_half_sum']:
                    pattern_similarity += 0.3
                if target_features['second_half_sum'] == entry_features['second_half_sum']:
                    pattern_similarity += 0.3
                
                pattern_similarity = min(pattern_similarity, 1.0)  # Cap at 1.0
                
                # Pattern type similarity weight reduced due to new prefix weight
                # similarity += pattern_similarity * 0.35
                
                pattern_scores.append(similarity)
            
            if not pattern_scores:
                return 0.0
            
            # Calculate percentile rank
            target_pattern_score = sum(pattern_scores) / len(pattern_scores)
            return min(target_pattern_score * 85, 90.0)  # Cap at 90%
            
        except Exception as e:
            logger.error(f"Error in pattern analysis: {e}")
            return 0.0
    
    def chaos_theory_analysis(self, target_number, historical_data):
        """Apply chaos theory for hidden pattern detection (8-char format)"""
        try:
            if len(historical_data) < 10:
                return 0.0
            
            # Convert to numerical sequence (using numeric part only)
            sequence = []
            for entry in historical_data:
                try:
                    ticket_num = str(entry['ticket_number']).upper().strip()
                    if len(ticket_num) == 8 and ticket_num[:2].isalpha() and ticket_num[2:].isdigit():
                        num = int(ticket_num[2:])  # Use 6-digit numeric part
                        sequence.append(num)
                except:
                    continue
            
            if len(sequence) < 10:
                return 0.0
            
            target_str = str(target_number).upper().strip()
            if len(target_str) != 8 or not target_str[:2].isalpha() or not target_str[2:].isdigit():
                return 0.0
            
            target_num = int(target_str[2:])  # Use 6-digit numeric part
            
            # Phase space reconstruction
            embedding_dim = 3
            delay = 1
            
            embedded = []
            for i in range(len(sequence) - (embedding_dim - 1) * delay):
                point = [sequence[i + j * delay] for j in range(embedding_dim)]
                embedded.append(point)
            
            if len(embedded) < 5:
                return 0.0
            
            # Find attractors and calculate distance to target
            embedded = np.array(embedded)
            
            # Calculate distances from target in phase space
            target_point = np.array([target_num] * embedding_dim)
            distances = [np.linalg.norm(point - target_point) for point in embedded]
            
            # Find proximity score
            min_distance = min(distances)
            max_distance = max(distances)
            
            if max_distance == min_distance:
                return 0.0
            
            # Normalize and invert (closer = higher score)
            proximity_score = 1 - (min_distance / max_distance)
            
            return min(proximity_score * 75, 85.0)  # Cap at 85%
            
        except Exception as e:
            logger.error(f"Error in chaos analysis: {e}")
            return 0.0
    
    def quantum_inspired_analysis(self, target_number, historical_data):
        """Quantum-inspired probability analysis (8-char format)"""
        try:
            target_str = str(target_number).upper().strip()
            if len(target_str) != 8 or not target_str[:2].isalpha() or not target_str[2:].isdigit():
                return 0.0
            
            target_digits = [int(d) for d in target_str[2:]]  # Use 6-digit numeric part
            
            # Create quantum-like state vectors
            quantum_states = []
            for entry in historical_data:
                ticket_num = str(entry['ticket_number']).upper().strip()
                if len(ticket_num) == 8 and ticket_num[:2].isalpha() and ticket_num[2:].isdigit():
                    digits = [int(d) for d in ticket_num[2:]]  # Use 6-digit numeric part
                    # Convert to probability amplitudes
                    if sum(digits) > 0:
                        amplitudes = np.array(digits) / np.linalg.norm(digits)
                        quantum_states.append(amplitudes)
            
            if not quantum_states:
                return 0.0
            
            # Target quantum state
            target_amplitudes = np.array(target_digits) / np.linalg.norm(target_digits)
            
            # Calculate quantum entanglement-like correlations
            correlations = []
            for state in quantum_states:
                # Quantum overlap (inner product)
                overlap = np.abs(np.dot(target_amplitudes, state)) ** 2
                correlations.append(overlap)
            
            # Calculate quantum interference patterns
            mean_correlation = np.mean(correlations)
            
            return min(mean_correlation * 80, 88.0)  # Cap at 88%
            
        except Exception as e:
            logger.error(f"Error in quantum analysis: {e}")
            return 0.0
    
    def fractal_analysis(self, target_number, historical_data):
        """Fractal dimension analysis for self-similarity (8-char format)"""
        try:
            if len(historical_data) < 20:
                return 0.0
            
            # Extract digit sequences (6-digit numeric parts)
            all_digits = []
            for entry in historical_data:
                ticket_num = str(entry['ticket_number']).upper().strip()
                if len(ticket_num) == 8 and ticket_num[:2].isalpha() and ticket_num[2:].isdigit():
                    digits = [int(d) for d in ticket_num[2:]]  # Use 6-digit numeric part
                    all_digits.extend(digits)
            
            target_str = str(target_number).upper().strip()
            if len(target_str) != 8 or not target_str[:2].isalpha() or not target_str[2:].isdigit():
                return 0.0
            
            target_digits = [int(d) for d in target_str[2:]]  # Use 6-digit numeric part
            
            # Box counting for fractal dimension (updated for 6 digits)
            def box_counting_similarity(target_seq, data_seq, scales=[1, 2, 3, 6]):
                similarities = []
                
                for scale in scales:
                    # Create boxes at different scales
                    target_boxes = set()
                    data_boxes = set()
                    
                    for i in range(0, len(target_seq), scale):
                        box = tuple(target_seq[i:i+scale])
                        if len(box) == scale:
                            target_boxes.add(box)
                    
                    for i in range(0, len(data_seq), scale):
                        box = tuple(data_seq[i:i+scale])
                        if len(box) == scale:
                            data_boxes.add(box)
                    
                    # Calculate Jaccard similarity
                    if len(target_boxes) > 0 and len(data_boxes) > 0:
                        intersection = len(target_boxes.intersection(data_boxes))
                        union = len(target_boxes.union(data_boxes))
                        similarity = intersection / union if union > 0 else 0
                        similarities.append(similarity)
                
                return np.mean(similarities) if similarities else 0
            
            fractal_similarity = box_counting_similarity(target_digits, all_digits)
            
            return min(fractal_similarity * 70, 82.0)  # Cap at 82%
            
        except Exception as e:
            logger.error(f"Error in fractal analysis: {e}")
            return 0.0
    
    def calculate_ensemble_percentage(self, lottery_name, lottery_number, historical_data):
        """Combine all analysis methods for final percentage"""
        try:
            if not historical_data:
                return self.base_probability
            
            # Run all analysis methods
            frequency_score = self.frequency_analysis(lottery_name, lottery_number, historical_data)
            pattern_score = self.pattern_analysis(lottery_number, historical_data)
            chaos_score = self.chaos_theory_analysis(lottery_number, historical_data)
            quantum_score = self.quantum_inspired_analysis(lottery_number, historical_data)
            fractal_score = self.fractal_analysis(lottery_number, historical_data)
            
            # Weighted ensemble
            weights = {
                'frequency': 0.35,
                'pattern': 0.25,
                'chaos': 0.15,
                'quantum': 0.15,
                'fractal': 0.10
            }
            
            ensemble_score = (
                frequency_score * weights['frequency'] +
                pattern_score * weights['pattern'] +
                chaos_score * weights['chaos'] +
                quantum_score * weights['quantum'] +
                fractal_score * weights['fractal']
            )
            
            # Apply confidence scaling based on data size
            data_confidence = min(len(historical_data) / 1000, 1.0)  # Full confidence at 1000+ samples
            
            # Final percentage with base probability floor
            final_percentage = max(
                self.base_probability,
                ensemble_score * data_confidence
            )
            
            return min(final_percentage, 95.0)  # Never exceed 95%
            
        except Exception as e:
            logger.error(f"Error in ensemble calculation: {e}")
            return self.base_probability
    
    def get_historical_data(self, lottery_name):
        """Fetch historical lottery data"""
        try:
            # Get lottery object
            lottery = Lottery.objects.filter(
                Q(name__icontains=lottery_name) | Q(code__icontains=lottery_name)
            ).first()
            
            if not lottery:
                return []
            
            # Get recent results (last 2 years for better analysis)
            two_years_ago = timezone.now().date() - timedelta(days=730)
            
            historical_entries = PrizeEntry.objects.filter(
                lottery_result__lottery=lottery,
                lottery_result__is_published=True,
                lottery_result__date__gte=two_years_ago,
                # Include all prize types since format is consistent
                prize_type__in=['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', 'consolation']
            ).values('ticket_number', 'prize_type', 'lottery_result__date').order_by('-lottery_result__date')
            
            return list(historical_entries)
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []
    
    def generate_message(self, percentage, lottery_number):
        """Generate appropriate message based on percentage"""
        if percentage >= 80:
            return f"Excellent! Number {lottery_number} shows very strong winning patterns with high probability."
        elif percentage >= 60:
            return f"Good! Number {lottery_number} demonstrates favorable winning patterns."
        elif percentage >= 40:
            return f"Moderate chance. Number {lottery_number} shows some positive indicators."
        elif percentage >= 20:
            return f"Low probability. Number {lottery_number} has minimal favorable patterns."
        else:
            return f"Very low chance. Number {lottery_number} shows limited winning potential."
    
    def post(self, request):
        """
        Main API endpoint
        Expected body: {
            "lottery_name": "Karunya",
            "lottery_number": "1234"
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
            
            # Validate number format (should be 2 alphabets + 6 digits)
            lottery_number = str(lottery_number).upper().strip()
            if len(lottery_number) != 8 or not lottery_number[:2].isalpha() or not lottery_number[2:].isdigit():
                return Response({
                    'lottery_number': lottery_number,
                    'lottery_name': lottery_name,
                    'percentage': 0.0,
                    'message': 'Invalid lottery number format. Please provide format: AB123456 (2 alphabets + 6 digits).',
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
                    'message': f'Lottery "{lottery_name}" not found in database',
                    'status': 'error'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get historical data
            historical_data = self.get_historical_data(lottery_name)
            
            if not historical_data:
                return Response({
                    'lottery_number': lottery_number,
                    'lottery_name': lottery.name,
                    'percentage': self.base_probability,
                    'message': f'No historical data available for {lottery.name}. Showing base probability.',
                    'status': 'success'
                })
            
            # Calculate winning percentage
            percentage = self.calculate_ensemble_percentage(
                lottery_name, lottery_number, historical_data
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
            logger.error(f"Unexpected error in LotteryWinningPercentageAPI: {e}")
            return Response({
                'lottery_number': request.data.get('lottery_number', ''),
                'lottery_name': request.data.get('lottery_name', ''),
                'percentage': 0.0,
                'message': 'Internal server error occurred while calculating percentage',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

#<--------------NOTIFICATION SECTION ---------------->


@api_view(['POST'])
def send_result_started_notification(request):
    """
    Manually trigger "result addition started" notification
    
    Body:
    {
        "lottery_name": "Karunya"
    }
    """
    lottery_name = request.data.get('lottery_name', 'Kerala Lottery')
    
    try:
        # Send notification
        result = FCMService.send_lottery_result_started(lottery_name)
        
        # Log notification
        NotificationLog.objects.create(
            notification_type='result_started',
            title="🎯 Kerala Lottery Results Loading...",
            body=f"We're adding the latest {lottery_name} results. Stay tuned!",
            lottery_name=lottery_name,
            success_count=result['success_count'],
            failure_count=result['failure_count'],
            total_tokens=result['success_count'] + result['failure_count']
        )
        
        return Response({
            'status': 'success',
            'message': 'Result started notification sent',
            'lottery_name': lottery_name,
            'statistics': result
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to send notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_result_completed_notification(request):
    """
    Manually trigger "result addition completed" notification
    
    Body:
    {
        "lottery_name": "Karunya",
        "draw_number": "KR-123"
    }
    """
    lottery_name = request.data.get('lottery_name', 'Kerala Lottery')
    draw_number = request.data.get('draw_number', 'Latest')
    
    try:
        # Send notification
        result = FCMService.send_lottery_result_completed(lottery_name, draw_number)
        
        # Log notification
        NotificationLog.objects.create(
            notification_type='result_completed',
            title="🎉 Kerala Lottery Results Ready!",
            body=f"{lottery_name} Draw {draw_number} results are now available. Check if you won!",
            lottery_name=lottery_name,
            draw_number=draw_number,
            success_count=result['success_count'],
            failure_count=result['failure_count'],
            total_tokens=result['success_count'] + result['failure_count']
        )
        
        return Response({
            'status': 'success',
            'message': 'Result completed notification sent',
            'lottery_name': lottery_name,
            'draw_number': draw_number,
            'statistics': result
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to send notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def send_test_notification(request):
    """
    Send test notification to all users
    """
    try:
        result = FCMService.test_notification()
        
        # Log notification
        NotificationLog.objects.create(
            notification_type='test',
            title="🧪 Test Notification",
            body="This is a test notification from Kerala Lottery App!",
            success_count=result['success_count'],
            failure_count=result['failure_count'],
            total_tokens=result['success_count'] + result['failure_count']
        )
        
        return Response({
            'status': 'success',
            'message': 'Test notification sent',
            'statistics': result
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to send test notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@staff_member_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def custom_lottery_admin_view(request, result_id=None):
    """
    Custom admin view for adding/editing lottery results with notification support
    """
    is_edit_mode = result_id is not None
    lottery_result = None
    prize_entries_json = '{}'
    
    if is_edit_mode:
        lottery_result = get_object_or_404(LotteryResult, id=result_id)
        # Get existing prize entries for edit mode
        prize_entries = {}
        for prize_type in ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th']:
            entries = PrizeEntry.objects.filter(
                lottery_result=lottery_result,
                prize_type=prize_type
            ).values('prize_amount', 'ticket_number', 'place')
            if entries:
                prize_entries[prize_type] = list(entries)
        
        prize_entries_json = json.dumps(prize_entries)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                lottery_id = request.POST.get('lottery')
                draw_number = request.POST.get('draw_number')
                date = request.POST.get('date')
                is_published = request.POST.get('is_published') == 'on'
                is_bumper = request.POST.get('is_bumper') == 'on'
                results_ready_notification = request.POST.get('results_ready_notification') == 'on'
                
                # Validate required fields
                if not all([lottery_id, draw_number, date]):
                    messages.error(request, 'Please fill in all required fields.')
                    return render(request, 'admin/lottery_result_form.html', {
                        'is_edit_mode': is_edit_mode,
                        'lottery_result': lottery_result,
                        'lotteries': Lottery.objects.all(),
                        'prize_types': [
                            ('1st', '1st Prize'), ('2nd', '2nd Prize'), ('3rd', '3rd Prize'),
                            ('consolation', 'Consolation Prize'), ('4th', '4th Prize'),
                            ('5th', '5th Prize'), ('6th', '6th Prize'), ('7th', '7th Prize'),
                            ('8th', '8th Prize'), ('9th', '9th Prize'), ('10th', '10th Prize')
                        ],
                        'prize_entries_json': prize_entries_json
                    })
                
                lottery = Lottery.objects.get(id=lottery_id)
                
                # Create or update lottery result
                if is_edit_mode:
                    # Check if notification should be sent (only if checkbox is newly checked)
                    should_send_notification = (
                        results_ready_notification and 
                        not lottery_result.results_ready_notification
                    )
                    
                    # Update existing result
                    lottery_result.lottery = lottery
                    lottery_result.draw_number = draw_number
                    lottery_result.date = date
                    lottery_result.is_published = is_published
                    lottery_result.is_bumper = is_bumper
                    lottery_result.results_ready_notification = results_ready_notification
                    lottery_result.save()
                    
                    action = 'updated'
                    
                else:
                    # Create new result
                    lottery_result = LotteryResult.objects.create(
                        lottery=lottery,
                        draw_number=draw_number,
                        date=date,
                        is_published=is_published,
                        is_bumper=is_bumper,
                        results_ready_notification=results_ready_notification
                    )
                    
                    # Send first notification automatically for new results
                    try:
                        fcm_result = FCMService.send_lottery_result_started(lottery.name)
                        
                        # Log the notification
                        NotificationLog.objects.create(
                            notification_type='result_started',
                            title="🎯 Kerala Lottery Results Loading...",
                            body=f"We're adding the latest {lottery.name} results. Stay tuned!",
                            lottery_name=lottery.name,
                            draw_number=draw_number,
                            success_count=fcm_result['success_count'],
                            failure_count=fcm_result['failure_count'],
                            total_tokens=fcm_result['success_count'] + fcm_result['failure_count']
                        )
                        
                        logger.info(f"📱 Started notification sent for new result: {lottery.name} - {draw_number}")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to send started notification: {e}")
                    
                    should_send_notification = results_ready_notification
                    action = 'created'
                
                # Process prize entries (your existing prize entry logic)
                # Clear existing entries if editing
                if is_edit_mode:
                    PrizeEntry.objects.filter(lottery_result=lottery_result).delete()
                
                # Process each prize type
                for prize_type in ['1st', '2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th']:
                    amounts = request.POST.getlist(f'{prize_type}_prize_amount[]')
                    ticket_numbers = request.POST.getlist(f'{prize_type}_ticket_number[]')
                    places = request.POST.getlist(f'{prize_type}_place[]')
                    
                    # Create prize entries
                    for i, (amount, ticket_number) in enumerate(zip(amounts, ticket_numbers)):
                        if amount and ticket_number:
                            place = places[i] if i < len(places) else ''
                            
                            PrizeEntry.objects.create(
                                lottery_result=lottery_result,
                                prize_type=prize_type,
                                prize_amount=amount,
                                ticket_number=ticket_number,
                                place=place if place else None
                            )
                
                # Send completion notification if requested
                if should_send_notification:
                    try:
                        fcm_result = FCMService.send_lottery_result_completed(
                            lottery_result.lottery.name, 
                            lottery_result.draw_number
                        )
                        
                        # Log the notification
                        NotificationLog.objects.create(
                            notification_type='result_completed',
                            title="🎉 Kerala Lottery Results Ready!",
                            body=f"{lottery_result.lottery.name} Draw {lottery_result.draw_number} results are now available. Check if you won!",
                            lottery_name=lottery_result.lottery.name,
                            draw_number=lottery_result.draw_number,
                            success_count=fcm_result['success_count'],
                            failure_count=fcm_result['failure_count'],
                            total_tokens=fcm_result['success_count'] + fcm_result['failure_count']
                        )
                        
                        logger.info(f"📱 Completed notification sent: {lottery_result.lottery.name} - {lottery_result.draw_number}")
                        
                        # Auto-publish when notification is sent
                        if not lottery_result.is_published:
                            lottery_result.is_published = True
                            lottery_result.save()
                        
                        messages.success(request, f'Lottery result {action} successfully and users have been notified! 📱')
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to send completion notification: {e}")
                        messages.warning(request, f'Lottery result {action} successfully but notification failed to send.')
                else:
                    messages.success(request, f'Lottery result {action} successfully!')
                
                # Redirect based on action
                if not is_edit_mode:
                    return redirect('custom_lottery_admin_edit', result_id=lottery_result.id)
                else:
                    return redirect('custom_lottery_admin_edit', result_id=lottery_result.id)
                    
        except Exception as e:
            logger.error(f"❌ Error in custom lottery admin: {e}")
            messages.error(request, f'Error {action if "action" in locals() else "processing"} lottery result: {str(e)}')
    
    # GET request - show form
    context = {
        'is_edit_mode': is_edit_mode,
        'lottery_result': lottery_result,
        'lotteries': Lottery.objects.all(),
        'prize_types': [
            ('1st', '1st Prize'), ('2nd', '2nd Prize'), ('3rd', '3rd Prize'),
            ('consolation', 'Consolation Prize'), ('4th', '4th Prize'),
            ('5th', '5th Prize'), ('6th', '6th Prize'), ('7th', '7th Prize'),
            ('8th', '8th Prize'), ('9th', '9th Prize'), ('10th', '10th Prize')
        ],
        'prize_entries_json': prize_entries_json
    }
    
    return render(request, 'admin/lottery_result_form.html', context)




#<----------------DEBUG AREA---------------->
# Add these views to your Django views.py

# Fixed Django views.py - Replace the problematic views with these

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth import get_user_model
from results.services.fcm_service import FCMService
import firebase_admin
from firebase_admin import messaging
from datetime import datetime

User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_firebase_status(request):
    """
    Debug Firebase configuration and user token status
    """
    try:
        # Check Firebase initialization
        firebase_status = {
            'initialized': bool(firebase_admin._apps),
            'project_id': getattr(settings, 'FIREBASE_SETTINGS', {}).get('PROJECT_ID', 'Not set'),
            'fcm_enabled': getattr(settings, 'FIREBASE_SETTINGS', {}).get('ENABLE_FCM', False),
        }
        
        # Get user token statistics
        user_stats = FCMService.get_user_token_stats()
        
        # Get sample tokens for testing
        sample_tokens = list(User.objects.filter(
            fcm_token__isnull=False,
            notifications_enabled=True
        ).exclude(fcm_token='').values_list('fcm_token', flat=True)[:3])
        
        # Recent users with tokens - using date_joined instead of created_at
        recent_users = User.objects.filter(
            fcm_token__isnull=False
        ).exclude(fcm_token='').order_by('-id')[:5].values(
            'id', 'name', 'phone_number', 'notifications_enabled', 
            'date_joined'  # Changed from created_at
        )
        
        return Response({
            'firebase_status': firebase_status,
            'user_stats': user_stats,
            'sample_tokens': [token[:20] + '...' for token in sample_tokens],
            'recent_users_with_tokens': list(recent_users),
            'debug_info': {
                'total_firebase_apps': len(firebase_admin._apps),
                'settings_configured': hasattr(settings, 'FIREBASE_SETTINGS'),
            }
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'firebase_initialized': bool(firebase_admin._apps) if 'firebase_admin' in globals() else False
        })

@api_view(['POST'])
@permission_classes([AllowAny])
def debug_send_to_specific_token(request):
    """
    Send test notification to a specific token for debugging
    
    Body:
    {
        "fcm_token": "your_token_here",
        "title": "Test Title",
        "body": "Test Body"
    }
    """
    fcm_token = request.data.get('fcm_token')
    title = request.data.get('title', '🧪 Debug Test')
    body = request.data.get('body', 'Direct token test from Django backend')
    
    if not fcm_token:
        return Response({
            'status': 'error',
            'message': 'fcm_token is required'
        })
    
    try:
        # Validate token format
        if not FCMService.validate_fcm_token(fcm_token):
            return Response({
                'status': 'error',
                'message': 'Invalid FCM token format',
                'token_preview': fcm_token[:20] + '...'
            })
        
        # Send notification
        success = FCMService.send_to_token(
            token=fcm_token,
            title=title,
            body=body,
            data={
                'type': 'debug_test',
                'timestamp': str(int(datetime.now().timestamp()))
            }
        )
        
        return Response({
            'status': 'success' if success else 'failed',
            'message': f'Notification {"sent successfully" if success else "failed to send"}',
            'token_preview': fcm_token[:20] + '...',
            'title': title,
            'body': body
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Failed to send notification: {str(e)}',
            'token_preview': fcm_token[:20] + '...'
        })

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_list_user_tokens(request):
    """
    List all users with FCM tokens for debugging
    """
    try:
        users_with_tokens = User.objects.filter(
            fcm_token__isnull=False
        ).exclude(fcm_token='').order_by('-id')[:10]
        
        user_list = []
        for user in users_with_tokens:
            user_list.append({
                'id': user.id,
                'name': user.name,
                'phone_number': user.phone_number,
                'notifications_enabled': user.notifications_enabled,
                'token_preview': user.fcm_token[:20] + '...' if user.fcm_token else None,
                'token_valid_format': FCMService.validate_fcm_token(user.fcm_token) if user.fcm_token else False,
                'date_joined': user.date_joined,  # Changed from created_at
                'fcm_token_updated_at': getattr(user, 'fcm_token_updated_at', None)  # Added this field since it exists
            })
        
        return Response({
            'total_users_with_tokens': User.objects.filter(
                fcm_token__isnull=False
            ).exclude(fcm_token='').count(),
            'users': user_list
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        })

# Bonus: Add a simple model inspection endpoint to see available fields
@api_view(['GET'])
@permission_classes([AllowAny])
def debug_user_model_fields(request):
    """
    Show available fields in the User model for debugging
    """
    try:
        # Get all field names from the User model
        field_names = [field.name for field in User._meta.get_fields()]
        
        # Get a sample user to show field types
        sample_user = User.objects.first()
        sample_data = {}
        
        if sample_user:
            for field_name in field_names:
                try:
                    value = getattr(sample_user, field_name, 'N/A')
                    # Don't show sensitive data
                    if field_name in ['password', 'fcm_token']:
                        sample_data[field_name] = f"<{type(value).__name__}>"
                    else:
                        sample_data[field_name] = str(value)[:50] + ('...' if len(str(value)) > 50 else '')
                except Exception as e:
                    sample_data[field_name] = f"Error: {str(e)}"
        
        return Response({
            'available_fields': field_names,
            'sample_user_data': sample_data,
            'total_users': User.objects.count()
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        })
    



# Add this to your views.py to test production methods

from datetime import datetime

@api_view(['POST'])
@permission_classes([AllowAny])
def debug_test_production_methods(request):
    """
    Test the actual production FCM methods used in admin_views.py
    """
    test_type = request.data.get('test_type', 'result_completed')
    
    try:
        if test_type == 'result_started':
            # Test lottery result started notification (automatic on new result)
            lottery_name = request.data.get('lottery_name', 'KARUNYA PLUS')
            
            print(f"🧪 Testing send_lottery_result_started with: {lottery_name}")
            result = FCMService.send_lottery_result_started(lottery_name)
            print(f"📱 FCM Result: {result}")
            
            return Response({
                'status': 'success',
                'test_type': test_type,
                'lottery_name': lottery_name,
                'fcm_result': result,
                'message': f'send_lottery_result_started("{lottery_name}") executed'
            })
            
        elif test_type == 'result_completed':
            # Test lottery result completed notification (checkbox trigger)
            lottery_name = request.data.get('lottery_name', 'KARUNYA PLUS')
            draw_number = request.data.get('draw_number', 'KN-123')
            result_unique_id = request.data.get('result_unique_id', 'test-result-456')
            
            print(f"🧪 Testing send_lottery_result_completed with: {lottery_name}, {draw_number}, {result_unique_id}")
            result = FCMService.send_lottery_result_completed(
                lottery_name=lottery_name,
                draw_number=draw_number,
                result_unique_id=result_unique_id
            )
            print(f"📱 FCM Result: {result}")
            
            return Response({
                'status': 'success',
                'test_type': test_type,
                'lottery_name': lottery_name,
                'draw_number': draw_number,
                'result_unique_id': result_unique_id,
                'fcm_result': result,
                'message': f'send_lottery_result_completed executed'
            })
            
        elif test_type == 'test_notification':
            # Test the general test notification
            print(f"🧪 Testing FCMService.test_notification()")
            result = FCMService.test_notification()
            print(f"📱 FCM Result: {result}")
            
            return Response({
                'status': 'success',
                'test_type': test_type,
                'fcm_result': result,
                'message': 'FCMService.test_notification() executed'
            })
            
        elif test_type == 'send_to_all_users':
            # Test sending to all users directly
            title = request.data.get('title', '🧪 Direct All Users Test')
            body = request.data.get('body', 'Testing send_to_all_users method directly')
            
            print(f"🧪 Testing send_to_all_users with: {title}, {body}")
            result = FCMService.send_to_all_users(
                title=title,
                body=body,
                data={
                    'type': 'debug_all_users_test',
                    'timestamp': str(int(datetime.now().timestamp()))
                }
            )
            print(f"📱 FCM Result: {result}")
            
            return Response({
                'status': 'success',
                'test_type': test_type,
                'title': title,
                'body': body,
                'fcm_result': result,
                'message': 'send_to_all_users executed directly'
            })
            
        else:
            return Response({
                'error': 'Invalid test_type. Options: result_started, result_completed, test_notification, send_to_all_users'
            })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error in debug_test_production_methods: {e}")
        print(f"📜 Full traceback: {error_details}")
        
        return Response({
            'status': 'error',
            'test_type': test_type,
            'error': str(e),
            'error_details': error_details,
            'message': f'Production method {test_type} failed with exception'
        })


