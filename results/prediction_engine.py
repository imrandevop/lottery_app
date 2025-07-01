# lottery_prediction/prediction_engine.py (UPDATED)
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta
import random
from django.db.models import Q
from django.utils import timezone
from results.models import LotteryResult, PrizeEntry, Lottery  # Replace with your actual app name
from .models import PredictionHistory, PredictionModel

class LotteryPredictionEngine:
    """
    Advanced lottery prediction engine using multiple algorithms
    """
    
    def __init__(self):
        self.alphabet_patterns = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.digit_patterns = '0123456789'
    
    def validate_lottery_exists(self, lottery_name):
        """Check if lottery exists and return lottery object"""
        try:
            # Case-insensitive search for lottery name
            lottery = Lottery.objects.get(name__iexact=lottery_name)
            return lottery
        except Lottery.DoesNotExist:
            return None
    
    def get_historical_data(self, lottery_name=None, prize_type=None, limit=1000):
        """Fetch historical lottery data"""
        query = Q(lottery_result__is_published=True)
        
        if lottery_name:
            # Handle case-insensitive lottery name matching
            query &= Q(lottery_result__lottery__name__icontains=lottery_name)
        
        if prize_type:
            query &= Q(prize_type=prize_type)
        
        # Get historical data ordered by most recent first
        historical_data = PrizeEntry.objects.filter(query).select_related(
            'lottery_result', 'lottery_result__lottery'
        ).order_by('-lottery_result__date')[:limit]
        
        return historical_data
    
    def extract_number_components(self, ticket_number, prize_type):
        """Extract meaningful components from ticket numbers"""
        if not ticket_number:
            return None
            
        ticket_number = str(ticket_number).strip().upper()
        
        # For 1st, 2nd, 3rd prizes - full number analysis
        if prize_type in ['1st', '2nd', '3rd', 'consolation']:
            # Pattern like "PS782804"
            alpha_part = re.findall(r'[A-Z]+', ticket_number)
            digit_part = re.findall(r'\d+', ticket_number)
            
            return {
                'full_number': ticket_number,
                'alpha_prefix': alpha_part[0] if alpha_part else '',
                'digits': digit_part[0] if digit_part else '',
                'last_4': ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number,
                'first_digit': ticket_number[0] if ticket_number else '',
                'last_digit': ticket_number[-1] if ticket_number else ''
            }
        else:
            # For other prizes - last 4 digits analysis
            return {
                'full_number': ticket_number,
                'last_4': ticket_number[-4:] if len(ticket_number) >= 4 else ticket_number,
                'digits': re.findall(r'\d+', ticket_number)[0] if re.findall(r'\d+', ticket_number) else ticket_number,
                'first_digit': ticket_number[0] if ticket_number else '',
                'last_digit': ticket_number[-1] if ticket_number else ''
            }
    
    def frequency_analysis_prediction(self, historical_data, prize_type, count=1, lottery_code=None):
        """Predict based on frequency analysis of patterns"""
        components_list = []
        
        for entry in historical_data:
            components = self.extract_number_components(entry.ticket_number, prize_type)
            if components:
                components_list.append(components)
        
        if not components_list:
            return self.generate_random_numbers(prize_type, count, lottery_code)
        
        predictions = []
        
        if prize_type in ['1st', '2nd', '3rd', 'consolation']:
            # For major prizes - single prediction with lottery code
            alpha_freq = Counter([c['alpha_prefix'] for c in components_list if c['alpha_prefix']])
            digit_freq = Counter([c['digits'] for c in components_list if c['digits']])
            
            # Get most frequent patterns
            common_alpha = alpha_freq.most_common(5)
            common_digits = digit_freq.most_common(10)
            
            # Generate prediction with lottery code
            if common_digits and lottery_code:
                # Use lottery code as first letter
                digit_weights = [freq for _, freq in common_digits]
                selected_digits = random.choices([digits for digits, _ in common_digits], weights=digit_weights)[0]
                
                # Add some randomness to avoid exact repetition
                if len(selected_digits) >= 4:
                    # Modify last 2 digits slightly
                    modified_digits = selected_digits[:-2] + str(random.randint(10, 99))
                    prediction = lottery_code + modified_digits
                else:
                    prediction = lottery_code + selected_digits
            else:
                prediction = self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            
            predictions.append(prediction)
        else:
            # For 4th prize and above - last 4 digits format (12 numbers)
            last_4_freq = Counter([c['last_4'] for c in components_list if c['last_4']])
            digit_freq = Counter([c['digits'] for c in components_list if c['digits']])
            
            if last_4_freq:
                common_last_4 = last_4_freq.most_common(20)  # Get more options for 12 predictions
                weights = [freq for _, freq in common_last_4]
                
                # Generate 12 unique numbers with variations
                used_numbers = set()
                while len(used_numbers) < count:
                    selected = random.choices([num for num, _ in common_last_4], weights=weights)[0]
                    
                    # Add slight variation to avoid duplicates
                    if selected.isdigit() and len(selected) == 4:
                        base_num = int(selected)
                        variation = random.randint(-100, 100)
                        new_num = max(0, min(9999, base_num + variation))
                        varied_prediction = str(new_num).zfill(4)
                    else:
                        varied_prediction = selected
                    
                    used_numbers.add(varied_prediction)
                
                prediction_batch = list(used_numbers)[:count]
            else:
                # Generate 12 random 4-digit numbers
                prediction_batch = [str(random.randint(1000, 9999)) for _ in range(count)]
            
            predictions.extend(prediction_batch)
        
        return predictions[:count]  # Ensure we return exactly the requested count
    
    def pattern_recognition_prediction(self, historical_data, prize_type, count=1, lottery_code=None):
        """Advanced pattern recognition based on sequences and trends"""
        components_list = []
        dates = []
        
        for entry in historical_data:
            components = self.extract_number_components(entry.ticket_number, prize_type)
            if components:
                components_list.append(components)
                dates.append(entry.lottery_result.date)
        
        if len(components_list) < 3:
            return self.frequency_analysis_prediction(historical_data, prize_type, count, lottery_code)
        
        predictions = []
        
        # Analyze temporal patterns
        if prize_type in ['1st', '2nd', '3rd', 'consolation']:
            # For major prizes - single prediction
            recent_alphas = [c['alpha_prefix'] for c in components_list[:10] if c['alpha_prefix']]
            recent_digits = [c['digits'] for c in components_list[:10] if c['digits']]
            
            if recent_digits and lottery_code:
                # Pattern prediction with lottery code
                digit_pattern = self.analyze_digit_trends(recent_digits)
                prediction = lottery_code + digit_pattern
            else:
                prediction = self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            
            predictions.append(prediction)
        else:
            # For 4th+ prizes - generate 12 numbers
            recent_numbers = [c['last_4'] for c in components_list[:30] if c['last_4'] and c['last_4'].isdigit()]
            
            if len(recent_numbers) >= 3:
                # Generate 12 varied predictions
                used_numbers = set()
                base_predictions = []
                
                # Get several base patterns
                for i in range(0, min(12, len(recent_numbers)), 3):
                    pattern_group = recent_numbers[i:i+3]
                    base_pred = self.predict_next_sequence(pattern_group)
                    base_predictions.append(base_pred)
                
                # Generate variations to reach 12 numbers
                for base_pred in base_predictions:
                    if len(used_numbers) >= count:
                        break
                    
                    used_numbers.add(base_pred)
                    
                    # Add variations of this base prediction
                    base_num = int(base_pred) if base_pred.isdigit() else random.randint(1000, 9999)
                    for variation in [-200, -100, -50, 50, 100, 200]:
                        if len(used_numbers) >= count:
                            break
                        varied_num = max(1000, min(9999, base_num + variation))
                        used_numbers.add(str(varied_num).zfill(4))
                
                # Fill remaining slots with random numbers if needed
                while len(used_numbers) < count:
                    random_num = str(random.randint(1000, 9999))
                    used_numbers.add(random_num)
                
                predictions = list(used_numbers)[:count]
            else:
                # Generate 12 random numbers
                predictions = [str(random.randint(1000, 9999)) for _ in range(count)]
        
        return predictions
    
    def find_sequence_pattern(self, alpha_sequence):
        """Find patterns in alphabetic sequences"""
        if not alpha_sequence:
            return random.choice(['PA', 'PB', 'PC', 'PD', 'PE'])
        
        # Analyze most recent pattern
        recent = alpha_sequence[0] if alpha_sequence else 'PA'
        
        if len(recent) >= 2:
            first_char = recent[0]
            second_char = recent[1]
            
            # Simple pattern: increment second character
            next_second = chr((ord(second_char) - ord('A') + 1) % 26 + ord('A'))
            return first_char + next_second
        
        return recent
    
    def analyze_digit_trends(self, digit_sequence):
        """Analyze trends in digit sequences"""
        if not digit_sequence:
            return str(random.randint(100000, 999999))
        
        # Get the most recent number
        recent = digit_sequence[0] if digit_sequence else '000000'
        
        if recent.isdigit():
            base_num = int(recent)
            # Add trend-based variation
            variation = random.randint(-1000, 1000)
            new_num = max(100000, min(999999, base_num + variation))
            return str(new_num)
        
        return recent
    
    def predict_next_sequence(self, number_sequence):
        """Predict next number in sequence using statistical analysis"""
        numbers = [int(n) for n in number_sequence if n.isdigit()]
        
        if len(numbers) < 2:
            return str(random.randint(1000, 9999))
        
        # Calculate differences and trends
        diffs = [numbers[i] - numbers[i+1] for i in range(len(numbers)-1)]
        
        if diffs:
            avg_diff = sum(diffs) / len(diffs)
            # Predict next number
            predicted = int(numbers[0] + avg_diff + random.randint(-100, 100))
            predicted = max(1000, min(9999, predicted))
            return str(predicted).zfill(4)
        
        return str(random.randint(1000, 9999))
    
    def ensemble_prediction(self, historical_data, prize_type, count=1, lottery_code=None):
        """Combine multiple prediction methods for better accuracy"""
        freq_predictions = self.frequency_analysis_prediction(historical_data, prize_type, count, lottery_code)
        pattern_predictions = self.pattern_recognition_prediction(historical_data, prize_type, count, lottery_code)
        
        # Combine predictions with weighted approach
        if prize_type in ['1st', '2nd', '3rd', 'consolation']:
            # For major prizes - single number
            if random.random() < 0.6:  # 60% weight to frequency analysis
                prediction = freq_predictions[0] if freq_predictions else self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            else:  # 40% weight to pattern recognition
                prediction = pattern_predictions[0] if pattern_predictions else self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            
            return [prediction]
        else:
            # For 4th+ prizes - combine and mix 12 numbers
            ensemble_predictions = []
            
            # Take 60% from frequency, 40% from pattern
            freq_count = int(count * 0.6)  # ~7 numbers
            pattern_count = count - freq_count  # ~5 numbers
            
            # Add frequency predictions
            ensemble_predictions.extend(freq_predictions[:freq_count])
            
            # Add pattern predictions
            ensemble_predictions.extend(pattern_predictions[:pattern_count])
            
            # Fill any remaining slots
            while len(ensemble_predictions) < count:
                ensemble_predictions.append(str(random.randint(1000, 9999)))
            
            # Remove duplicates and ensure we have exactly 'count' numbers
            unique_predictions = list(dict.fromkeys(ensemble_predictions))  # Preserves order, removes duplicates
            
            # If we lost numbers due to duplicates, add random ones
            while len(unique_predictions) < count:
                new_num = str(random.randint(1000, 9999))
                if new_num not in unique_predictions:
                    unique_predictions.append(new_num)
            
            return unique_predictions[:count]
    
    def generate_random_numbers(self, prize_type, count=1, lottery_code=None):
        """Generate random numbers as fallback"""
        predictions = []
        
        if prize_type in ['1st', '2nd', '3rd', 'consolation']:
            # Major prizes: Full format - lottery code + 6 digits (single number)
            if lottery_code:
                digits = ''.join(random.choices(self.digit_patterns, k=6))
                prediction = lottery_code + digits
            else:
                # Fallback if no lottery code
                alpha = ''.join(random.choices(self.alphabet_patterns, k=1))
                digits = ''.join(random.choices(self.digit_patterns, k=6))
                prediction = alpha + digits
            predictions.append(prediction)
        else:
            # 4th+ prizes: Last 4 digits format (12 numbers)
            used_numbers = set()
            while len(used_numbers) < count:
                prediction = ''.join(random.choices(self.digit_patterns, k=4))
                used_numbers.add(prediction)
            predictions = list(used_numbers)
        
        return predictions
    
    def calculate_confidence_score(self, historical_data, prize_type, prediction_method):
        """Calculate confidence score based on historical accuracy and data quality"""
        base_confidence = 0.3  # Base confidence
        
        # Data quantity factor
        data_count = len(historical_data)
        if data_count > 100:
            data_factor = 0.3
        elif data_count > 50:
            data_factor = 0.2
        elif data_count > 20:
            data_factor = 0.15
        else:
            data_factor = 0.1
        
        # Method factor
        method_factors = {
            'frequency': 0.25,
            'pattern': 0.2,
            'ensemble': 0.3,
            'random': 0.1
        }
        method_factor = method_factors.get(prediction_method, 0.1)
        
        # Prize type factor (lower prizes are more predictable due to patterns)
        prize_factors = {
            '1st': 0.1, '2nd': 0.1, '3rd': 0.1, 'consolation': 0.1,
            '4th': 0.15, '5th': 0.15, '6th': 0.2, '7th': 0.2, '8th': 0.2, '9th': 0.2
        }
        prize_factor = prize_factors.get(prize_type, 0.1)
        
        confidence = min(0.85, base_confidence + data_factor + method_factor + prize_factor)
        return round(confidence, 2)
    
    def predict(self, lottery_name, prize_type, method='ensemble'):
        """Main prediction method with lottery validation"""
        # Validate lottery exists
        lottery = self.validate_lottery_exists(lottery_name)
        if not lottery:
            raise ValueError(f"Lottery '{lottery_name}' does not exist")
        
        # Get lottery code
        lottery_code = lottery.code.upper() if lottery.code else None
        
        # Get historical data
        historical_data = self.get_historical_data(lottery_name, prize_type)
        
        # Determine count based on prize type
        count_map = {
            '1st': 1, '2nd': 1, '3rd': 1, 'consolation': 1,  # Major prizes: 1 number each
            '4th': 12, '5th': 12, '6th': 12, '7th': 12, '8th': 12, '9th': 12, '10th': 12  # Minor prizes: 12 numbers each
        }
        count = count_map.get(prize_type, 12)  # Default to 12 for any other prize
        
        # Generate predictions based on method
        if method == 'frequency':
            predictions = self.frequency_analysis_prediction(historical_data, prize_type, count, lottery_code)
        elif method == 'pattern':
            predictions = self.pattern_recognition_prediction(historical_data, prize_type, count, lottery_code)
        elif method == 'ensemble':
            predictions = self.ensemble_prediction(historical_data, prize_type, count, lottery_code)
        else:
            predictions = self.generate_random_numbers(prize_type, count, lottery_code)
        
        # Calculate confidence score
        confidence = self.calculate_confidence_score(historical_data, prize_type, method)
        
        return {
            'predictions': predictions,
            'confidence': confidence,
            'method': method,
            'historical_data_count': len(historical_data),
            'lottery_code': lottery_code
        }


# lottery_prediction/views.py (UPDATED)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .serializers import LotteryPredictionRequestSerializer, LotteryPredictionResponseSerializer
from .prediction_engine import LotteryPredictionEngine
from .models import PredictionHistory

class LotteryPredictionAPIView(APIView):
    """
    API View for lottery number prediction with lottery validation
    """
    
    def post(self, request):
        """
        Generate lottery predictions
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
            # Initialize prediction engine
            engine = LotteryPredictionEngine()
            
            # Generate prediction (this will validate lottery exists)
            result = engine.predict(lottery_name, prize_type, method='ensemble')
            
            # Store prediction history
            prediction_history = PredictionHistory.objects.create(
                lottery_name=lottery_name,
                prize_type=prize_type,
                predicted_numbers=result['predictions'],
                prediction_date=timezone.now()
            )
            
            # Prepare response - simplified format
            response_data = {
                'status': 'success',
                'lottery_name': lottery_name,
                'prize_type': prize_type,
                'predicted_numbers': result['predictions'],
                'note': 'Predictions are based on statistical analysis of historical data. Lottery outcomes are random and these predictions are for entertainment purposes only.'
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            # Handle lottery not found error
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Prediction generation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)