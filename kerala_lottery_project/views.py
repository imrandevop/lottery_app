from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db import connection
from django.core.cache import cache
from results.models import LotteryResult, PrizeEntry
import logging

logger = logging.getLogger('lottery_app')

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Enhanced health check with database and cache monitoring"""
        try:
            # Check database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_status = "connected"
            
            # Check Redis cache
            try:
                cache.set('health_check', 'ok', 30)
                cache_result = cache.get('health_check')
                cache_status = "connected" if cache_result == 'ok' else "disconnected"
            except Exception:
                cache_status = "disconnected"
            
            # Get basic stats
            stats = {
                'total_results': LotteryResult.objects.count(),
                'published_results': LotteryResult.objects.filter(is_published=True).count(),
                'total_prizes': PrizeEntry.objects.count(),
            }
            
            health_data = {
                'status': 'healthy' if db_status == 'connected' else 'unhealthy',
                'timestamp': timezone.now().isoformat(),
                'database': db_status,
                'cache': cache_status,
                'stats': stats
            }
            
            status_code = 200 if db_status == 'connected' else 503
            return Response(health_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response({
                'status': 'unhealthy',
                'timestamp': timezone.now().isoformat(),
                'error': str(e)
            }, status=503)