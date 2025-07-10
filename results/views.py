# views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date,time
from django.utils.timezone import now, localtime
import uuid
from .models import Lottery, LotteryResult, PrizeEntry, ImageUpdate, News, PredictionHistory
from .models import PrizeEntry, LiveVideo
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

    def calculate_prediction_accuracy(self, lottery_name, prize_type):
        """Calculate accuracy against the most recently published result"""
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
            
            # Get winning numbers from 4th-10th prizes (4-digit numbers)
            winning_numbers = list(PrizeEntry.objects.filter(
                lottery_result=latest_result,
                prize_type__in=['4th', '5th', '6th', '7th', '8th', '9th', '10th']
            ).values_list('ticket_number', flat=True))
            
            # Convert to last 4 digits for comparison
            winning_last_4 = []
            for num in winning_numbers:
                if num:
                    last_4 = str(num)[-4:] if len(str(num)) >= 4 else str(num).zfill(4)
                    if last_4.isdigit() and len(last_4) == 4:
                        winning_last_4.append(last_4)
            
            if not winning_last_4:
                return None
            
            # Compare predictions with winning numbers
            predicted_numbers = prediction.predicted_numbers
            if not predicted_numbers:
                return None
            
            accuracy_results = {
                "100%": [],
                "75%": [],
                "50%": [],
                "25%": []
            }
            
            perfect_matches = 0
            total_accuracy_points = 0
            
            for pred_num in predicted_numbers:
                pred_str = str(pred_num)
                
                # For 1st, 2nd, 3rd prizes, use last 4 digits
                if prize_type in ['1st', '2nd', '3rd']:
                    pred_last_4 = pred_str[-4:] if len(pred_str) >= 4 else pred_str.zfill(4)
                else:
                    pred_last_4 = pred_str
                
                # Find best match
                best_match_percentage = 0
                for winning_num in winning_last_4:
                    match_count = sum(1 for i, digit in enumerate(pred_last_4) 
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
                    accuracy_results["100%"].append(pred_last_4)
                    perfect_matches += 1
                    total_accuracy_points += 100
                elif best_match_percentage == 75:
                    accuracy_results["75%"].append(pred_last_4)
                    total_accuracy_points += 75
                elif best_match_percentage == 50:
                    accuracy_results["50%"].append(pred_last_4)
                    total_accuracy_points += 50
                elif best_match_percentage == 25:
                    accuracy_results["25%"].append(pred_last_4)
                    total_accuracy_points += 25
            
            # Calculate overall accuracy percentage
            total_predictions = len(predicted_numbers)
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

    def post(self, request):
        """
        Generate stable lottery predictions with accuracy tracking
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
            
            # Calculate accuracy for the most recent result
            accuracy_data = self.calculate_prediction_accuracy(lottery_name, prize_type)
            
            # Build response data (keeping existing structure)
            response_data = {
                'status': 'success',
                'lottery_name': lottery_name,
                'prize_type': prize_type,
                'predicted_numbers': result['predictions'],
            }
            
            # Add repeated numbers for all prize types EXCEPT consolation
            if prize_type != 'consolation':
                response_data['repeated_numbers'] = result.get('repeated_numbers', [])
            
            # Add new accuracy field
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