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
from .models import Lottery, LotteryResult, PrizeEntry, ImageUpdate, News
from .serializers import LotteryResultSerializer, LotteryResultDetailSerializer
from django.contrib.auth import get_user_model
from .serializers import TicketCheckSerializer, NewsSerializer





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
                "image1": image_settings.update_image1,
                "image2": image_settings.update_image2,
                "image3": image_settings.update_image3
            },
             # Keep this hardcoded or add your custom logic
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

class LotteryResultDetailView(generics.RetrieveAPIView):
    """
    API endpoint to get detailed lottery result by ID
    """
    queryset = LotteryResult.objects.filter(is_published=True).select_related('lottery').prefetch_related('prizes')
    serializer_class = LotteryResultDetailSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'result': serializer.data
        })

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
    API endpoint to check if a ticket won any prize with enhanced functionality
    """

    def is_previous_result(self, requested_date, result_date):
        return requested_date != result_date

    def post(self, request):
        serializer = TicketCheckSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket_number = serializer.validated_data['ticket_number']
        phone_number = serializer.validated_data['phone_number']
        check_date = serializer.validated_data['date']

        if len(ticket_number) < 1:
            return Response(
                {'error': 'Invalid ticket number format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        lottery_code = ticket_number[0].upper()

        try:
            lottery = Lottery.objects.get(code=lottery_code)
        except Lottery.DoesNotExist:
            return Response(
                {'error': f'Lottery with code "{lottery_code}" not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        current_datetime = localtime(now())
        current_date = current_datetime.date()
        result_publish_time = time(15, 0)  # 3:00 PM IST

        if check_date > current_date or (
            check_date == current_date and current_datetime.time() < result_publish_time
        ):
            last_4_digits = ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number

            previous_result = LotteryResult.objects.filter(
                lottery=lottery,
                date__lt=check_date,
                is_published=True
            ).select_related('lottery').order_by('-date').first()

            response_data = {
                'message': 'Result not published yet. Please check after 3:00 PM.',
                'result_published': False,
                'lottery_name': lottery.name,
                'lottery_code': lottery.code,
                'requested_date': check_date,
                'publish_time': '3:00 PM',
                'ticket_number': ticket_number,
                'last_4_digits': last_4_digits,
            }

            if previous_result:
                recent_winning_tickets = PrizeEntry.objects.filter(
                    ticket_number=ticket_number,
                    lottery_result=previous_result
                )

                recent_small_prizes = PrizeEntry.objects.filter(
                    ticket_number=last_4_digits,
                    lottery_result=previous_result
                ).exclude(ticket_number=ticket_number)

                all_recent_wins = list(recent_winning_tickets) + list(recent_small_prizes)

                if all_recent_wins:
                    recent_wins = []
                    total_recent_prize = 0

                    for prize in all_recent_wins:
                        prize_amount = float(prize.prize_amount)
                        total_recent_prize += prize_amount
                        is_small_prize = prize.ticket_number == last_4_digits and prize.ticket_number != ticket_number

                        recent_wins.append({
                            'prize_type': prize.get_prize_type_display(),
                            'prize_amount': prize_amount,
                            'match_type': 'Last 4 digits match' if is_small_prize else 'Full ticket match',
                            'winning_ticket_number': prize.ticket_number,
                            'place': prize.place if prize.place else None
                        })

                    response_data['recent_win'] = {
                        'message': f'Great news! You won ₹{total_recent_prize:,.0f} in the most recent draw!',
                        'date': previous_result.date,
                        'draw_number': previous_result.draw_number,
                        'unique_id': str(previous_result.unique_id),
                        'total_prize_amount': total_recent_prize,
                        'total_prizes': len(recent_wins),
                        'prize_details': recent_wins
                    }

                response_data['isPrevious_result'] = self.is_previous_result(check_date, previous_result.date)
            else:
                response_data['isPrevious_result'] = False

            return Response(response_data, status=status.HTTP_200_OK)

        try:
            lottery_result = LotteryResult.objects.get(
                lottery=lottery,
                date=check_date,
                is_published=True
            )

            last_4_digits = ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number

            winning_tickets = PrizeEntry.objects.filter(
                ticket_number=ticket_number,
                lottery_result=lottery_result
            )

            small_prize_tickets = PrizeEntry.objects.filter(
                ticket_number=last_4_digits,
                lottery_result=lottery_result
            ).exclude(ticket_number=ticket_number)

            all_winning_tickets = list(winning_tickets) + list(small_prize_tickets)

            if all_winning_tickets:
                results = []
                total_prize_amount = 0

                for prize in all_winning_tickets:
                    prize_amount = float(prize.prize_amount)
                    total_prize_amount += prize_amount
                    is_small_prize = prize.ticket_number == last_4_digits and prize.ticket_number != ticket_number

                    result = {
                        'prize_type': prize.get_prize_type_display(),
                        'prize_amount': prize_amount,
                        'lottery_name': prize.lottery_result.lottery.name,
                        'lottery_code': prize.lottery_result.lottery.code,
                        'draw_number': prize.lottery_result.draw_number,
                        'date': prize.lottery_result.date,
                        'unique_id': str(prize.lottery_result.unique_id),
                        'winning_ticket_number': prize.ticket_number,
                        'your_ticket_number': ticket_number,
                        'match_type': 'Last 4 digits match' if is_small_prize else 'Full ticket match'
                    }

                    if prize.place:
                        result['place'] = prize.place

                    results.append(result)

                return Response({
                    'message': f'Congratulations! You won ₹{total_prize_amount:,.0f}',
                    'won_prize': True,
                    'result_published': True,
                    'isPrevious_result': False,
                    'prize_details': results[0] if len(results) == 1 else results,
                    'total_prizes': len(results) if len(results) > 1 else 1,
                    'total_prize_amount': total_prize_amount
                }, status=status.HTTP_200_OK)

            return Response({
                'message': 'Better luck next time! Your ticket did not win any prize.',
                'won_prize': False,
                'result_published': True,
                'isPrevious_result': False,
                'ticket_number': ticket_number,
                'last_4_digits': last_4_digits,
                'lottery_info': {
                    'name': lottery_result.lottery.name,
                    'code': lottery_result.lottery.code,
                    'date': lottery_result.date,
                    'draw_number': lottery_result.draw_number,
                    'unique_id': str(lottery_result.unique_id)
                }
            }, status=status.HTTP_200_OK)

        except LotteryResult.DoesNotExist:
            latest_result = LotteryResult.objects.filter(
                lottery=lottery,
                date__lt=check_date,
                is_published=True
            ).select_related('lottery').order_by('-date').first()

            if not latest_result:
                return Response({
                    'message': 'No published result found for this lottery',
                    'ticket_number': ticket_number,
                    'lottery_name': lottery.name,
                    'lottery_code': lottery.code,
                    'date': check_date,
                    'result_published': False,
                    'isPrevious_result': False
                }, status=status.HTTP_200_OK)

            last_4_digits = ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number

            latest_winning_tickets = PrizeEntry.objects.filter(
                ticket_number=ticket_number,
                lottery_result=latest_result
            )

            latest_small_prizes = PrizeEntry.objects.filter(
                ticket_number=last_4_digits,
                lottery_result=latest_result
            ).exclude(ticket_number=ticket_number)

            all_latest_wins = list(latest_winning_tickets) + list(latest_small_prizes)
            is_prev = self.is_previous_result(check_date, latest_result.date)

            if all_latest_wins:
                latest_wins = []
                total_latest_prize = 0

                for prize in all_latest_wins:
                    prize_amount = float(prize.prize_amount)
                    total_latest_prize += prize_amount
                    is_small_prize = prize.ticket_number == last_4_digits and prize.ticket_number != ticket_number

                    latest_wins.append({
                        'prize_type': prize.get_prize_type_display(),
                        'prize_amount': prize_amount,
                        'match_type': 'Last 4 digits match' if is_small_prize else 'Full ticket match',
                        'winning_ticket_number': prize.ticket_number
                    })

                return Response({
                    'message': f'Congratulations! You won ₹{total_latest_prize:,.0f} in the latest {lottery.name} draw!',
                    'won_prize': True,
                    'result_published': False,
                    'isPrevious_result': is_prev,
                    'ticket_number': ticket_number,
                    'requested_date': check_date,
                    'lottery_name': lottery.name,
                    'latest_result': {
                        'date': latest_result.date,
                        'draw_number': latest_result.draw_number,
                        'unique_id': str(latest_result.unique_id),
                        'total_prize_amount': total_latest_prize,
                        'prize_details': latest_wins[0] if len(latest_wins) == 1 else latest_wins
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': f'No result published for {check_date}. Your ticket did not win in the latest available result.',
                    'won_prize': False,
                    'result_published': False,
                    'isPrevious_result': is_prev,
                    'ticket_number': ticket_number,
                    'requested_date': check_date,
                    'lottery_name': lottery.name,
                    'latest_result': {
                        'date': latest_result.date,
                        'draw_number': latest_result.draw_number,
                        'unique_id': str(latest_result.unique_id)
                    }
                }, status=status.HTTP_200_OK)
            

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