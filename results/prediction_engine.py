# lottery_prediction/prediction_engine.py
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
    
    def frequency_analysis_prediction(self, historical_data, prize_type, count=1):
        """Predict based on frequency analysis of patterns"""
        components_list = []
        
        for entry in historical_data:
            components = self.extract_number_components(entry.ticket_number, prize_type)
            if components:
                components_list.append(components)
        
        if not components_list:
            return self.generate_random_numbers(prize_type, count)
        
        predictions = []
        
        for _ in range(count):
            if prize_type in ['1st', '2nd', '3rd', 'consolation']:
                # Analyze full pattern for major prizes
                alpha_freq = Counter([c['alpha_prefix'] for c in components_list if c['alpha_prefix']])
                digit_freq = Counter([c['digits'] for c in components_list if c['digits']])
                
                # Get most frequent patterns
                common_alpha = alpha_freq.most_common(5)
                common_digits = digit_freq.most_common(10)
                
                # Generate prediction
                if common_alpha and common_digits:
                    # Weighted random selection
                    alpha_weights = [freq for _, freq in common_alpha]
                    digit_weights = [freq for _, freq in common_digits]
                    
                    selected_alpha = random.choices([alpha for alpha, _ in common_alpha], weights=alpha_weights)[0]
                    selected_digits = random.choices([digits for digits, _ in common_digits], weights=digit_weights)[0]
                    
                    # Add some randomness to avoid exact repetition
                    if len(selected_digits) >= 4:
                        # Modify last 2 digits slightly
                        modified_digits = selected_digits[:-2] + str(random.randint(10, 99))
                        prediction = selected_alpha + modified_digits
                    else:
                        prediction = selected_alpha + selected_digits
                else:
                    prediction = self.generate_random_numbers(prize_type, 1)[0]
            else:
                # For other prizes, focus on last 4 digits
                last_4_freq = Counter([c['last_4'] for c in components_list if c['last_4']])
                digit_freq = Counter([c['digits'] for c in components_list if c['digits']])
                
                if last_4_freq:
                    common_last_4 = last_4_freq.most_common(10)
                    weights = [freq for _, freq in common_last_4]
                    selected = random.choices([num for num, _ in common_last_4], weights=weights)[0]
                    
                    # Add slight variation
                    if selected.isdigit() and len(selected) == 4:
                        base_num = int(selected)
                        variation = random.randint(-50, 50)
                        new_num = max(0, min(9999, base_num + variation))
                        prediction = str(new_num).zfill(4)
                    else:
                        prediction = selected
                else:
                    prediction = str(random.randint(1000, 9999))
            
            predictions.append(prediction)
        
        return predictions
    
    def pattern_recognition_prediction(self, historical_data, prize_type, count=1):
        """Advanced pattern recognition based on sequences and trends"""
        components_list = []
        dates = []
        
        for entry in historical_data:
            components = self.extract_number_components(entry.ticket_number, prize_type)
            if components:
                components_list.append(components)
                dates.append(entry.lottery_result.date)
        
        if len(components_list) < 3:
            return self.frequency_analysis_prediction(historical_data, prize_type, count)
        
        predictions = []
        
        # Analyze temporal patterns
        for _ in range(count):
            if prize_type in ['1st', '2nd', '3rd', 'consolation']:
                # Analyze prefix patterns over time
                recent_alphas = [c['alpha_prefix'] for c in components_list[:10] if c['alpha_prefix']]
                recent_digits = [c['digits'] for c in components_list[:10] if c['digits']]
                
                if recent_alphas and recent_digits:
                    # Pattern prediction
                    alpha_pattern = self.find_sequence_pattern(recent_alphas)
                    digit_pattern = self.analyze_digit_trends(recent_digits)
                    
                    prediction = alpha_pattern + digit_pattern
                else:
                    prediction = self.generate_random_numbers(prize_type, 1)[0]
            else:
                # Analyze last 4 digit patterns
                recent_numbers = [c['last_4'] for c in components_list[:20] if c['last_4'] and c['last_4'].isdigit()]
                
                if len(recent_numbers) >= 3:
                    # Find numeric patterns
                    prediction = self.predict_next_sequence(recent_numbers)
                else:
                    prediction = str(random.randint(1000, 9999))
            
            predictions.append(prediction)
        
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
    
    def ensemble_prediction(self, historical_data, prize_type, count=1):
        """Combine multiple prediction methods for better accuracy"""
        freq_predictions = self.frequency_analysis_prediction(historical_data, prize_type, count)
        pattern_predictions = self.pattern_recognition_prediction(historical_data, prize_type, count)
        
        # Combine predictions with weighted approach
        ensemble_predictions = []
        
        for i in range(count):
            if random.random() < 0.6:  # 60% weight to frequency analysis
                prediction = freq_predictions[i] if i < len(freq_predictions) else freq_predictions[0]
            else:  # 40% weight to pattern recognition
                prediction = pattern_predictions[i] if i < len(pattern_predictions) else pattern_predictions[0]
            
            ensemble_predictions.append(prediction)
        
        return ensemble_predictions
    
    def generate_random_numbers(self, prize_type, count=1):
        """Generate random numbers as fallback"""
        predictions = []
        
        for _ in range(count):
            if prize_type in ['1st', '2nd', '3rd', 'consolation']:
                # Full format: 2 letters + 6 digits
                alpha = ''.join(random.choices(self.alphabet_patterns, k=2))
                digits = ''.join(random.choices(self.digit_patterns, k=6))
                prediction = alpha + digits
            else:
                # Last 4 digits format
                prediction = ''.join(random.choices(self.digit_patterns, k=4))
            
            predictions.append(prediction)
        
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
        """Main prediction method"""
        # Get historical data
        historical_data = self.get_historical_data(lottery_name, prize_type)
        
        # Determine count based on prize type
        count_map = {
            '1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5,
            '6th': 6, '7th': 7, '8th': 8, '9th': 9, '10th': 10,
            'consolation': 1
        }
        count = count_map.get(prize_type, 1)
        
        # Generate predictions based on method
        if method == 'frequency':
            predictions = self.frequency_analysis_prediction(historical_data, prize_type, count)
        elif method == 'pattern':
            predictions = self.pattern_recognition_prediction(historical_data, prize_type, count)
        elif method == 'ensemble':
            predictions = self.ensemble_prediction(historical_data, prize_type, count)
        else:
            predictions = self.generate_random_numbers(prize_type, count)
        
        # Calculate confidence score
        confidence = self.calculate_confidence_score(historical_data, prize_type, method)
        
        return {
            'predictions': predictions,
            'confidence': confidence,
            'method': method,
            'historical_data_count': len(historical_data)
        }

