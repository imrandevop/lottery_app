# views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date,time
from django.utils.timezone import now
import uuid
from .models import Lottery, LotteryResult, PrizeEntry
from .serializers import LotteryResultSerializer, LotteryResultDetailSerializer
from django.contrib.auth import get_user_model
from .serializers import TicketCheckSerializer




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
        return Response({
            'status': 'success',
            'count': queryset.count(),
            'results': serializer.data
        })

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
            
            # Serialize the data
            serializer = LotteryResultDetailSerializer(lottery_result)
            
            return Response({
                'status': 'success',
                'result': serializer.data
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
    API endpoint to check if a ticket won any prize
    """
    
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

        # Step 1: Check if result is published yet
        current_datetime = now()
        current_date = current_datetime.date()
        result_publish_time = time(15, 30)  # 3:30 PM

        if check_date > current_date or (
            check_date == current_date and current_datetime.time() < result_publish_time
        ):
            return Response(
                {'message': 'Result is not published yet.'},
                status=status.HTTP_200_OK
            )

        # Step 2: Check for winning entries
        winning_tickets = PrizeEntry.objects.filter(
            ticket_number=ticket_number,
            lottery_result__date=check_date,
            lottery_result__is_published=True
        ).select_related('lottery_result__lottery')

        if winning_tickets.exists():
            results = []
            for prize in winning_tickets:
                result = {
                    'message': f'Congratulations! You won ₹{prize.prize_amount}',
                    'prize': str(prize.prize_amount),
                    'matched_with': prize.get_prize_type_display(),
                    'lottery_name': prize.lottery_result.lottery.name,
                    'lottery_code': prize.lottery_result.lottery.code,
                    'draw_number': prize.lottery_result.draw_number,
                    'date': prize.lottery_result.date,
                    'unique_id': str(prize.lottery_result.unique_id),
                    'ticket_number': prize.ticket_number,
                }
                if prize.place:
                    result['place'] = prize.place
                results.append(result)

            if len(results) == 1:
                return Response(results[0], status=status.HTTP_200_OK)

            return Response({
                'message': 'Congratulations! You won multiple prizes!',
                'total_matches': len(results),
                'results': results
            }, status=status.HTTP_200_OK)

        # Step 3: Better luck next time with result context
        # Try to get result info even if no prize was won
        lottery_result = LotteryResult.objects.filter(
            date=check_date,
            is_published=True
        ).select_related('lottery').first()

        if lottery_result:
            return Response({
                'message': 'Better luck next time',
                'ticket_number': ticket_number,
                'lottery_name': lottery_result.lottery.name,
                'date': lottery_result.date,
                'unique_id': str(lottery_result.unique_id),
            }, status=status.HTTP_200_OK)
        
        # No result info found
        return Response({
            'message': 'Better luck next time',
            'ticket_number': ticket_number,
            'date': check_date
        }, status=status.HTTP_200_OK)