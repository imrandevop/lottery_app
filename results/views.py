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

        # Extract lottery code from first character of ticket number
        if len(ticket_number) < 1:
            return Response(
                {'error': 'Invalid ticket number format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lottery_code = ticket_number[0].upper()
        
        # Verify lottery exists
        try:
            lottery = Lottery.objects.get(code=lottery_code)
        except Lottery.DoesNotExist:
            return Response(
                {'error': f'Lottery with code "{lottery_code}" not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get current datetime in Asia/Kolkata timezone
        current_datetime = localtime(now())
        current_date = current_datetime.date()
        result_publish_time = time(15, 0)  # 3:00 PM IST

        # Check if result is not published yet
        if check_date > current_date or (
            check_date == current_date and current_datetime.time() < result_publish_time
        ):
            # Get last 4 digits for checking
            last_4_digits = ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number
            
            # Get the most recent previous result for this lottery
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
                'last_4_digits': last_4_digits
            }
            
            if previous_result:
                # Check if this ticket won in the most recent result
                recent_winning_tickets = PrizeEntry.objects.filter(
                    ticket_number=ticket_number,
                    lottery_result=previous_result
                ).select_related('lottery_result__lottery')
                
                # Check for small prizes with last 4 digits in recent result
                recent_small_prizes = PrizeEntry.objects.filter(
                    ticket_number=last_4_digits,
                    lottery_result=previous_result
                ).select_related('lottery_result__lottery').exclude(
                    ticket_number=ticket_number
                )
                
                all_recent_wins = list(recent_winning_tickets) + list(recent_small_prizes)
                
                if all_recent_wins:
                    # User won in the most recent result!
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
                else:
                    # No win in recent result, but show it as suggestion
                    response_data['previous_result_suggestion'] = {
                        'message': 'Here is the most recent result for this lottery:',
                        'date': previous_result.date,
                        'draw_number': previous_result.draw_number,
                        'unique_id': str(previous_result.unique_id)
                    }
                
                # Also check ALL previous wins for this ticket
                all_previous_wins = PrizeEntry.objects.filter(
                    ticket_number=ticket_number,
                    lottery_result__lottery=lottery,
                    lottery_result__date__lt=check_date,
                    lottery_result__is_published=True
                ).select_related('lottery_result').order_by('-lottery_result__date')[:5]
                
                all_previous_small_prizes = PrizeEntry.objects.filter(
                    ticket_number=last_4_digits,
                    lottery_result__lottery=lottery,
                    lottery_result__date__lt=check_date,
                    lottery_result__is_published=True
                ).select_related('lottery_result').exclude(
                    ticket_number=ticket_number
                ).order_by('-lottery_result__date')[:5]
                
                all_previous_list = list(all_previous_wins) + list(all_previous_small_prizes)
                
                if all_previous_list:
                    previous_wins_data = []
                    for prize in all_previous_list:
                        is_small_prize = prize.ticket_number == last_4_digits and prize.ticket_number != ticket_number
                        previous_wins_data.append({
                            'date': prize.lottery_result.date.strftime('%Y-%m-%d'),
                            'prize_type': prize.get_prize_type_display(),
                            'prize_amount': float(prize.prize_amount),
                            'draw_number': prize.lottery_result.draw_number,
                            'match_type': 'Last 4 digits match' if is_small_prize else 'Full ticket match',
                            'winning_ticket_number': prize.ticket_number,
                            'unique_id': str(prize.lottery_result.unique_id)
                        })
                    
                    # Sort by date
                    from datetime import datetime
                    previous_wins_data.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d').date(), reverse=True)
                    
                    response_data['all_previous_wins'] = {
                        'message': 'Your previous wins with this ticket:',
                        'total_previous_wins': len(previous_wins_data),
                        'wins': previous_wins_data[:5]
                    }
            
            return Response(response_data, status=status.HTTP_200_OK)

        # Look for the specific lottery result for this date and lottery
        try:
            lottery_result = LotteryResult.objects.get(
                lottery=lottery,
                date=check_date,
                is_published=True
            )
        except LotteryResult.DoesNotExist:
            return Response({
                'message': 'No published result found for this lottery on the specified date',
                'ticket_number': ticket_number,
                'lottery_name': lottery.name,
                'lottery_code': lottery.code,
                'date': check_date,
                'result_published': False
            }, status=status.HTTP_200_OK)

        # Get last 4 digits of ticket number for small prize checking
        last_4_digits = ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number
        
        # Check for winning entries - both full ticket number and last 4 digits
        winning_tickets = PrizeEntry.objects.filter(
            ticket_number=ticket_number,
            lottery_result=lottery_result
        ).select_related('lottery_result__lottery')
        
        # Check for small prizes with last 4 digits
        small_prize_tickets = PrizeEntry.objects.filter(
            ticket_number=last_4_digits,
            lottery_result=lottery_result
        ).select_related('lottery_result__lottery').exclude(
            ticket_number=ticket_number  # Exclude full matches to avoid duplicates
        )

        all_winning_tickets = list(winning_tickets) + list(small_prize_tickets)

        if all_winning_tickets:
            results = []
            total_prize_amount = 0
            
            for prize in all_winning_tickets:
                prize_amount = float(prize.prize_amount)
                total_prize_amount += prize_amount
                
                # Determine if this is a small prize (last 4 digits match)
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

            # Return response based on number of prizes won
            if len(results) == 1:
                return Response({
                    'message': f'Congratulations! You won ₹{total_prize_amount:,.0f}',
                    'won_prize': True,
                    'result_published': True,
                    'prize_details': results[0]
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': f'Congratulations! You won multiple prizes totaling ₹{total_prize_amount:,.0f}',
                    'won_prize': True,
                    'result_published': True,
                    'total_prize_amount': total_prize_amount,
                    'total_prizes': len(results),
                    'prize_details': results
                }, status=status.HTTP_200_OK)

        # No prize won - check previous results and return lottery info
        
        # Check previous results for this ticket number in this lottery
        previous_results = PrizeEntry.objects.filter(
            ticket_number=ticket_number,
            lottery_result__lottery=lottery,
            lottery_result__date__lt=check_date,
            lottery_result__is_published=True
        ).select_related('lottery_result').order_by('-lottery_result__date')[:3]  # Last 3 results
        
        # Also check previous results for last 4 digits
        previous_small_prizes = PrizeEntry.objects.filter(
            ticket_number=last_4_digits,
            lottery_result__lottery=lottery,
            lottery_result__date__lt=check_date,
            lottery_result__is_published=True
        ).select_related('lottery_result').exclude(
            ticket_number=ticket_number  # Exclude full matches to avoid duplicates
        ).order_by('-lottery_result__date')[:3]
        
        response_data = {
            'message': 'Better luck next time! Your ticket did not win any prize.',
            'won_prize': False,
            'result_published': True,
            'ticket_number': ticket_number,
            'last_4_digits': last_4_digits,
            'lottery_info': {
                'name': lottery_result.lottery.name,
                'code': lottery_result.lottery.code,
                'date': lottery_result.date,
                'draw_number': lottery_result.draw_number,
                'unique_id': str(lottery_result.unique_id)
            }
        }
        
        # Add previous winning history if exists
        if previous_results.exists() or previous_small_prizes.exists():
            previous_wins = []
            
            # Add full ticket wins
            for prize in previous_results:
                previous_wins.append({
                    'date': prize.lottery_result.date,
                    'prize_type': prize.get_prize_type_display(),
                    'prize_amount': float(prize.prize_amount),
                    'draw_number': prize.lottery_result.draw_number,
                    'match_type': 'Full ticket match',
                    'winning_ticket_number': prize.ticket_number
                })
            
            # Add small prize wins (last 4 digits)
            for prize in previous_small_prizes:
                previous_wins.append({
                    'date': prize.lottery_result.date,
                    'prize_type': prize.get_prize_type_display(),
                    'prize_amount': float(prize.prize_amount),
                    'draw_number': prize.lottery_result.draw_number,
                    'match_type': 'Last 4 digits match',
                    'winning_ticket_number': prize.ticket_number
                })
            
            # Sort by date (most recent first)
            previous_wins.sort(key=lambda x: x['date'], reverse=True)
            
            response_data['previous_wins'] = {
                'message': 'Here are your previous wins with this ticket/number:',
                'total_previous_wins': len(previous_wins),
                'wins': previous_wins[:5]  # Show only last 5 wins
            }
        
        return Response(response_data, status=status.HTTP_200_OK)





