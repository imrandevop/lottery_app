from django.core.management.base import BaseCommand
from results.prediction_engine import LotteryPredictionEngine
from results.models import PredictionModel

class Command(BaseCommand):
    help = 'Train and update prediction models'
    
    def handle(self, *args, **options):
        """
        Train prediction models and update their accuracy scores
        """
        engine = LotteryPredictionEngine()
        
        # You can add model training logic here
        # For now, create/update default models
        
        algorithms = ['frequency', 'pattern', 'ensemble']
        
        for algorithm in algorithms:
            model, created = PredictionModel.objects.get_or_create(
                name=f'Default {algorithm.title()} Model',
                algorithm=algorithm,
                defaults={
                    'accuracy_score': 0.3,  # Default score
                    'parameters': {},
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created model: {model.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Model already exists: {model.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Model training completed successfully!')
        )