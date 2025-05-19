from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import LotteryDraw, LotteryType, WinningTicket, PrizeCategory
from .serializers import LotteryResultSerializer, DateGroupedResultsSerializer
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
 


class LotteryResultsView(APIView):
    """
    Comprehensive API for lottery results with various filtering options.
    
    Query Parameters:
    - date: Specific date in YYYY-MM-DD format
    - start_date: Start date for range in YYYY-MM-DD format
    - end_date: End date for range in YYYY-MM-DD format
    - days: Number of days to fetch (from today backwards)
    - lottery_type: ID of lottery type
    - lottery_code: Code of lottery type (e.g., 'AK' for Akshaya)
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
        
        # Apply search if provided
        if search:
            winner_draws = WinningTicket.objects.filter(
                Q(number__contains=search) | Q(series__iexact=search)
            ).values_list('draw_id', flat=True)
            
            filter_conditions &= Q(id__in=winner_draws)
        
        # Fetch the filtered draws with related data
        draws = LotteryDraw.objects.filter(filter_conditions).select_related(
            'lottery_type'
        ).prefetch_related(
            'winners', 'winners__prize_category'
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


@staff_member_required
def get_lottery_type_for_draw(request):
    """Get the lottery type for a given draw ID."""
    draw_id = request.GET.get('draw_id')
    try:
        draw = LotteryDraw.objects.get(id=draw_id)
        return JsonResponse({
            'lottery_type_id': draw.lottery_type.id,
            'lottery_type_name': str(draw.lottery_type)
        })
    except (LotteryDraw.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid draw ID'}, status=400)

@staff_member_required
def get_prizes_for_lottery_type(request):
    """Get prize categories for a given lottery type ID."""
    lottery_type_id = request.GET.get('lottery_type_id')
    
    try:
        prizes = PrizeCategory.objects.filter(lottery_type_id=lottery_type_id).order_by('amount')
        
        # Also include prizes that don't have a lottery type (if any)
        prizes_without_type = PrizeCategory.objects.filter(lottery_type__isnull=True).order_by('amount')
        
        # Combine the querysets
        all_prizes = list(prizes) + list(prizes_without_type)
        
        # Format for JSON response
        prize_data = [{'id': p.id, 'name': str(p)} for p in all_prizes]
        
        return JsonResponse({'prizes': prize_data})
    except ValueError:
        return JsonResponse({'error': 'Invalid lottery type ID'}, status=400)