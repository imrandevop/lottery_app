# views.py (path: lottery/views.py)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    LotteryType, LotteryDraw, 
    FirstPrize, SecondPrize, ThirdPrize, FourthPrize, 
    FifthPrize, ConsolationPrize, SixthPrize, SeventhPrize, 
    EighthPrize, NinthPrize, TenthPrize, 
)
from .serializers import LotteryResultSerializer, DateGroupedResultsSerializer

class TodayResultAPIView(APIView):
    """
    API endpoint that returns today's lottery results in the exact format shown in the image
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        today = timezone.now().date()
        
        # Get today's lottery draws
        today_draws = LotteryDraw.objects.filter(
            draw_date=today,
            result_declared=True
        ).select_related('lottery_type').prefetch_related(
            'first_prize', 'consolation_prizes'
        ).order_by('-draw_number')
        
        if not today_draws.exists():
            return Response({
                "status": "success",
                "message": "No results available for today",
                "data": [],
                "date": today.isoformat(),
                "date_display": "Today Result"
            })
        
        results = []
        
        for draw in today_draws:
            # Build the lottery name exactly as shown in image
            lottery_name = f"{draw.lottery_type.name} {draw.lottery_type.code} {draw.draw_number}"
            
            # Get first prize info
            first_prize_data = None
            if hasattr(draw, 'first_prize') and draw.first_prize:
                first_prize_data = {
                    "amount": int(draw.first_prize.amount),
                    "amount_display": f"Rs {int(draw.first_prize.amount)}/-",
                    "amount_lakhs": f"[{int(draw.first_prize.amount) // 100000} Lakhs]",
                    "ticket_number": draw.first_prize.ticket_number,
                    "place": draw.first_prize.place
                }
            
            # Get consolation prizes
            consolation_prizes = []
            for prize in draw.consolation_prizes.all():
                consolation_prizes.append({
                    "ticket_number": prize.ticket_number,
                    "amount": int(prize.amount)
                })
            
            # Group consolation prizes in sets of 3 for display (as shown in image)
            consolation_rows = []
            for i in range(0, len(consolation_prizes), 3):
                row = consolation_prizes[i:i+3]
                consolation_rows.append(row)
            
            result_item = {
                "lottery_name": lottery_name,
                "lottery_type": draw.lottery_type.name,
                "lottery_code": draw.lottery_type.code,
                "draw_number": draw.draw_number,
                "is_new": draw.draw_date == today,  # Mark as NEW if it's today
                "first_prize": first_prize_data,
                "consolation_prizes": consolation_prizes,
                "consolation_rows": consolation_rows,  # Grouped for display
                "consolation_amount": 8000 if consolation_prizes else 0,  # Default amount as shown
                "draw_date": draw.draw_date.isoformat()
            }
            
            results.append(result_item)
        
        return Response({
            "status": "success",
            "data": results,
            "date": today.isoformat(),
            "date_display": "Today Result",
            "total_results": len(results)
        })


class PreviousDaysResultAPIView(APIView):
    """
    API endpoint that returns previous days' lottery results in the same format
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get query parameters
        days_back = int(request.query_params.get('days', 7))  # Default 7 days
        specific_date = request.query_params.get('date')  # Format: YYYY-MM-DD
        
        today = timezone.now().date()
        
        if specific_date:
            try:
                target_date = timezone.datetime.strptime(specific_date, '%Y-%m-%d').date()
                draws = LotteryDraw.objects.filter(
                    draw_date=target_date,
                    result_declared=True
                )
                
                date_display = self._get_date_display(target_date, today)
                
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Get results from previous days (excluding today)
            start_date = today - timedelta(days=days_back)
            draws = LotteryDraw.objects.filter(
                draw_date__gte=start_date,
                draw_date__lt=today,  # Exclude today
                result_declared=True
            )
            date_display = f"Previous {days_back} Days Results"
        
        draws = draws.select_related('lottery_type').prefetch_related(
            'first_prize', 'consolation_prizes'
        ).order_by('-draw_date', '-draw_number')
        
        if not draws.exists():
            return Response({
                "status": "success",
                "message": "No results available for the specified period",
                "data": [],
                "date_display": date_display
            })
        
        # Group results by date
        grouped_results = {}
        
        for draw in draws:
            date_key = draw.draw_date.isoformat()
            
            if date_key not in grouped_results:
                grouped_results[date_key] = {
                    "date": draw.draw_date.isoformat(),
                    "date_display": self._get_date_display(draw.draw_date, today),
                    "results": []
                }
            
            # Build the lottery name
            lottery_name = f"{draw.lottery_type.name} {draw.lottery_type.code} {draw.draw_number}"
            
            # Get first prize info
            first_prize_data = None
            if hasattr(draw, 'first_prize') and draw.first_prize:
                first_prize_data = {
                    "amount": int(draw.first_prize.amount),
                    "amount_display": f"Rs {int(draw.first_prize.amount)}/-",
                    "amount_lakhs": f"[{int(draw.first_prize.amount) // 100000} Lakhs]",
                    "ticket_number": draw.first_prize.ticket_number,
                    "place": draw.first_prize.place
                }
            
            # Get consolation prizes
            consolation_prizes = []
            for prize in draw.consolation_prizes.all():
                consolation_prizes.append({
                    "ticket_number": prize.ticket_number,
                    "amount": int(prize.amount)
                })
            
            # Group consolation prizes in rows of 3
            consolation_rows = []
            for i in range(0, len(consolation_prizes), 3):
                row = consolation_prizes[i:i+3]
                consolation_rows.append(row)
            
            result_item = {
                "lottery_name": lottery_name,
                "lottery_type": draw.lottery_type.name,
                "lottery_code": draw.lottery_type.code,
                "draw_number": draw.draw_number,
                "is_new": False,  # Previous results are not new
                "first_prize": first_prize_data,
                "consolation_prizes": consolation_prizes,
                "consolation_rows": consolation_rows,
                "consolation_amount": 8000 if consolation_prizes else 0,
                "draw_date": draw.draw_date.isoformat()
            }
            
            grouped_results[date_key]["results"].append(result_item)
        
        # Convert to list and sort by date (most recent first)
        result_list = list(grouped_results.values())
        result_list.sort(key=lambda x: x['date'], reverse=True)
        
        return Response({
            "status": "success",
            "data": result_list,
            "date_display": date_display,
            "total_dates": len(result_list),
            "total_results": sum(len(group["results"]) for group in result_list)
        })
    
    def _get_date_display(self, date, today):
        """Helper method to format date display"""
        if date == today:
            return "Today Result"
        elif date == today - timedelta(days=1):
            return "Yesterday Result"
        else:
            return f"{date.strftime('%d %b %Y')} Result"


class CombinedResultsAPIView(APIView):
    """
    API endpoint that returns both today's and previous days' results in one call
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        days_back = int(request.query_params.get('days', 7))
        today = timezone.now().date()
        start_date = today - timedelta(days=days_back)
        
        # Get all draws including today
        draws = LotteryDraw.objects.filter(
            draw_date__gte=start_date,
            result_declared=True
        ).select_related('lottery_type').prefetch_related(
            'first_prize', 'consolation_prizes'
        ).order_by('-draw_date', '-draw_number')
        
        if not draws.exists():
            return Response({
                "status": "success",
                "message": "No results available",
                "data": []
            })
        
        # Group results by date
        grouped_results = {}
        
        for draw in draws:
            date_key = draw.draw_date.isoformat()
            
            if date_key not in grouped_results:
                # Determine date display
                if draw.draw_date == today:
                    date_display = "Today Result"
                elif draw.draw_date == today - timedelta(days=1):
                    date_display = "Yesterday Result"
                else:
                    date_display = f"{draw.draw_date.strftime('%d %b %Y')} Result"
                
                grouped_results[date_key] = {
                    "date": draw.draw_date.isoformat(),
                    "date_display": date_display,
                    "is_today": draw.draw_date == today,
                    "results": []
                }
            
            # Build lottery result data
            lottery_name = f"{draw.lottery_type.name} {draw.lottery_type.code} {draw.draw_number}"
            
            first_prize_data = None
            if hasattr(draw, 'first_prize') and draw.first_prize:
                first_prize_data = {
                    "amount": int(draw.first_prize.amount),
                    "amount_display": f"Rs {int(draw.first_prize.amount)}/-",
                    "amount_lakhs": f"[{int(draw.first_prize.amount) // 100000} Lakhs]",
                    "ticket_number": draw.first_prize.ticket_number,
                    "place": draw.first_prize.place
                }
            
            consolation_prizes = []
            for prize in draw.consolation_prizes.all():
                consolation_prizes.append({
                    "ticket_number": prize.ticket_number,
                    "amount": int(prize.amount)
                })
            
            consolation_rows = []
            for i in range(0, len(consolation_prizes), 3):
                row = consolation_prizes[i:i+3]
                consolation_rows.append(row)
            
            result_item = {
                "lottery_name": lottery_name,
                "lottery_type": draw.lottery_type.name,
                "lottery_code": draw.lottery_type.code,
                "draw_number": draw.draw_number,
                "is_new": draw.draw_date == today,
                "first_prize": first_prize_data,
                "consolation_prizes": consolation_prizes,
                "consolation_rows": consolation_rows,
                "consolation_amount": 8000 if consolation_prizes else 0,
                "draw_date": draw.draw_date.isoformat()
            }
            
            grouped_results[date_key]["results"].append(result_item)
        
        # Convert to list and sort by date
        result_list = list(grouped_results.values())
        result_list.sort(key=lambda x: x['date'], reverse=True)
        
        return Response({
            "status": "success",
            "data": result_list,
            "total_dates": len(result_list),
            "total_results": sum(len(group["results"]) for group in result_list)
        })


# Simple function-based view for basic today's result
@csrf_exempt
def today_result_simple(request):
    """Simple function-based view for today's results"""
    today = timezone.now().date()
    
    draws = LotteryDraw.objects.filter(
        draw_date=today,
        result_declared=True
    ).select_related('lottery_type').prefetch_related('first_prize', 'consolation_prizes')
    
    results = []
    for draw in draws:
        lottery_name = f"{draw.lottery_type.name} {draw.lottery_type.code} {draw.draw_number}"
        
        first_prize = None
        if hasattr(draw, 'first_prize') and draw.first_prize:
            first_prize = {
                "ticket_number": draw.first_prize.ticket_number,
                "place": draw.first_prize.place,
                "amount": int(draw.first_prize.amount)
            }
        
        consolation_prizes = [
            {"ticket_number": prize.ticket_number, "amount": int(prize.amount)}
            for prize in draw.consolation_prizes.all()
        ]
        
        results.append({
            "lottery_name": lottery_name,
            "winner_list_title": f"{lottery_name} Winner List",
            "first_prize": first_prize,
            "consolation_prizes": consolation_prizes,
            "is_new": True
        })
    
    return JsonResponse({
        "status": "success",
        "date_display": "Today Result",
        "results": results
    })


class LotteryResultsView(APIView):
    """
    Comprehensive API for lottery results with various filtering options.
    
    Query Parameters:
    - date: Specific date in YYYY-MM-DD format
    - start_date: Start date for range in YYYY-MM-DD format
    - end_date: End date for range in YYYY-MM-DD format
    - days: Number of days to fetch (from today backwards)
    - lottery_type: ID of lottery type
    - lottery_code: Code of lottery type (e.g., 'SK' for Suvarna Keralam)
    - draw_number: Specific draw number
    - period: Predefined period ('today', 'yesterday', 'week', 'month', 'all')
    - group_by_date: Whether to group results by date (true/false)
    - search: Search term for ticket numbers
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Extract query parameters
        date_str = request.query_params.get('date')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        days_str = request.query_params.get('days')
        lottery_type_id = request.query_params.get('lottery_type')
        lottery_code = request.query_params.get('lottery_code')
        draw_number = request.query_params.get('draw_number')
        period = request.query_params.get('period')
        group_by_date = request.query_params.get('group_by_date', 'true').lower() == 'true'
        search = request.query_params.get('search')
        
        # Initialize filter conditions
        filter_conditions = Q(result_declared=True)
        
        # Handle date filtering
        today = timezone.now().date()
        
        if period:
            if period == 'today':
                filter_conditions &= Q(draw_date=today)
            elif period == 'yesterday':
                filter_conditions &= Q(draw_date=today - timedelta(days=1))
            elif period == 'week':
                filter_conditions &= Q(draw_date__gte=today - timedelta(days=7))
            elif period == 'month':
                filter_conditions &= Q(draw_date__gte=today - timedelta(days=30))
            # 'all' doesn't need additional filtering
        elif date_str:
            try:
                date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                filter_conditions &= Q(draw_date=date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif start_date_str and end_date_str:
            try:
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                filter_conditions &= Q(draw_date__gte=start_date, draw_date__lte=end_date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif days_str:
            try:
                days = int(days_str)
                filter_conditions &= Q(draw_date__gte=today - timedelta(days=days))
            except ValueError:
                return Response(
                    {"error": "Days parameter must be a number."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Default to last 7 days if no date parameters provided
            filter_conditions &= Q(draw_date__gte=today - timedelta(days=7))
        
        # Apply other filters
        if lottery_type_id:
            filter_conditions &= Q(lottery_type_id=lottery_type_id)
        
        if lottery_code:
            filter_conditions &= Q(lottery_type__code=lottery_code)
        
        if draw_number:
            filter_conditions &= Q(draw_number=draw_number)
        
        # Apply search for ticket numbers
        if search:
            search_draws_ids = set()
            
            # Search in FirstPrize
            first_prize_draws = FirstPrize.objects.filter(
                ticket_number__icontains=search
            ).values_list('draw_id', flat=True)
            search_draws_ids.update(first_prize_draws)
            
            # Search in SecondPrize
            second_prize_draws = SecondPrize.objects.filter(
                ticket_number__icontains=search
            ).values_list('draw_id', flat=True)
            search_draws_ids.update(second_prize_draws)
            
            # Search in ThirdPrize
            third_prize_draws = ThirdPrize.objects.filter(
                ticket_number__icontains=search
            ).values_list('draw_id', flat=True)
            search_draws_ids.update(third_prize_draws)
            
            # Search in FourthPrize
            fourth_prize_draws = FourthPrize.objects.filter(
                ticket_number__icontains=search
            ).values_list('draw_id', flat=True)
            search_draws_ids.update(fourth_prize_draws)
            
            # Search in FifthPrize
            fifth_prize_draws = FifthPrize.objects.filter(
                ticket_number__icontains=search
            ).values_list('draw_id', flat=True)
            search_draws_ids.update(fifth_prize_draws)
            
            # Search in ConsolationPrize
            consolation_prize_draws = ConsolationPrize.objects.filter(
                ticket_number__icontains=search
            ).values_list('draw_id', flat=True)
            search_draws_ids.update(consolation_prize_draws)
            
            # For 4-digit numbers (6th-10th prizes)
            if len(search) <= 4:
                # Search in SixthPrize
                sixth_prize_draws = SixthPrize.objects.filter(
                    number__icontains=search
                ).values_list('draw_id', flat=True)
                search_draws_ids.update(sixth_prize_draws)
                
                # Search in SeventhPrize
                seventh_prize_draws = SeventhPrize.objects.filter(
                    number__icontains=search
                ).values_list('draw_id', flat=True)
                search_draws_ids.update(seventh_prize_draws)
                
                # Search in EighthPrize
                eighth_prize_draws = EighthPrize.objects.filter(
                    number__icontains=search
                ).values_list('draw_id', flat=True)
                search_draws_ids.update(eighth_prize_draws)
                
                # Search in NinthPrize
                ninth_prize_draws = NinthPrize.objects.filter(
                    number__icontains=search
                ).values_list('draw_id', flat=True)
                search_draws_ids.update(ninth_prize_draws)
                
                # Search in TenthPrize
                tenth_prize_draws = TenthPrize.objects.filter(
                    number__icontains=search
                ).values_list('draw_id', flat=True)
                search_draws_ids.update(tenth_prize_draws)
            
            if search_draws_ids:
                filter_conditions &= Q(id__in=search_draws_ids)
            else:
                # If no draws match the search, return empty result
                return Response([])
        
        # Fetch the filtered draws with related data
        draws = LotteryDraw.objects.filter(filter_conditions).select_related(
            'lottery_type'
        ).prefetch_related(
            'first_prize', 'second_prize', 'third_prize', 'fourth_prize',
            'fifth_prizes', 'consolation_prizes', 'sixth_prizes', 
            'seventh_prizes', 'eighth_prizes', 'ninth_prizes', 'tenth_prizes'
        ).order_by('-draw_date', '-draw_number')
        
        # Return the response based on grouping preference
        if group_by_date:
            # Group results by date
            date_groups = {}
            
            for draw in draws:
                date_str = draw.draw_date.isoformat()
                if date_str not in date_groups:
                    # Format date for display
                    if draw.draw_date == today:
                        date_display = "Today Result"
                    elif draw.draw_date == today - timedelta(days=1):
                        date_display = "Yesterday Result"
                    else:
                        date_display = draw.draw_date.strftime("%d %b %Y Result")
                    
                    date_groups[date_str] = {
                        'date': draw.draw_date,
                        'date_display': date_display,
                        'results': []
                    }
                
                date_groups[date_str]['results'].append(draw)
            
            # Convert to list and sort by date
            result_list = list(date_groups.values())
            result_list.sort(key=lambda x: x['date'], reverse=True)
            
            serializer = DateGroupedResultsSerializer(result_list, many=True)
            return Response(serializer.data)
        else:
            # Return flat list of results
            serializer = LotteryResultSerializer(draws, many=True)
            return Response(serializer.data)


class SingleDrawResultView(APIView):
    """
    API to get detailed results for a single lottery draw.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, draw_id):
        try:
            draw = LotteryDraw.objects.get(id=draw_id)
            serializer = LotteryResultSerializer(draw)
            return Response(serializer.data)
        except LotteryDraw.DoesNotExist:
            return Response(
                {"error": "Draw not found."},
                status=status.HTTP_404_NOT_FOUND
            )

@csrf_exempt
def get_lottery_draw(request, draw_id):
    """API endpoint to get lottery draw details"""
    print(f"API called with draw_id: {draw_id}")
    
    try:
        draw = LotteryDraw.objects.get(id=draw_id)
        data = {
            'id': draw.id,
            'lottery_type': draw.lottery_type_id,
            'draw_number': draw.draw_number,
        }
        
        if hasattr(draw, 'draw_date') and draw.draw_date is not None:
            data['draw_date'] = draw.draw_date.isoformat()
        
        print(f"Found draw: {data}")
        return JsonResponse(data)
    except LotteryDraw.DoesNotExist:
        print(f"Draw not found: {draw_id}")
        return JsonResponse({'error': 'Draw not found'}, status=404)
    except Exception as e:
        print(f"Error fetching draw: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def test_json_view(request):
    """Simple test view to return JSON"""
    print("Test JSON view called")
    return JsonResponse({'test': 'success', 'message': 'API is working correctly'})