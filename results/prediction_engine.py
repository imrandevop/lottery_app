# lottery_prediction/prediction_engine.py (FINAL CLEAN VERSION)
from results.utils.cache_utils import (
    cache_prediction, get_cached_prediction,
    cache_historical_data, get_cached_historical_data
)
import logging

logger = logging.getLogger('lottery_app')
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta
import random
from django.db.models import Q
from django.utils import timezone
from results.models import LotteryResult, PrizeEntry, Lottery
from .models import PredictionHistory, PredictionModel

logger = logging.getLogger('lottery_app')

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
            lottery = Lottery.objects.get(name__iexact=lottery_name)
            return lottery
        except Lottery.DoesNotExist:
            return None
    
    def get_historical_data_optimized(self, lottery_name=None, prize_type=None, limit=500):
        """
        Optimized historical data fetching with reduced database load
        """
        # Build query with select_related for single query
        query = Q(lottery_result__is_published=True)
        
        if lottery_name:
            query &= Q(lottery_result__lottery__name__icontains=lottery_name)
        
        if prize_type:
            query &= Q(prize_type=prize_type)
        
        # Use select_related and values for efficiency
        historical_data = PrizeEntry.objects.filter(query).select_related(
            'lottery_result', 'lottery_result__lottery'
        ).values(
            'ticket_number',
            'prize_type', 
            'lottery_result__date',
            'lottery_result__lottery__name',
            'lottery_result__lottery__code'
        ).order_by('-lottery_result__date')[:limit]
        
        return historical_data
    
    def get_repeated_numbers(self, lottery_name, prize_type, count=12):
        """Get most frequently occurring 4-digit numbers from historical data for specific prize type"""
        # Build query for specific lottery, prize type, and published results only
        query = Q(lottery_result__is_published=True)
        query &= Q(lottery_result__lottery__name__iexact=lottery_name)
        query &= Q(prize_type=prize_type)
        
        # Get historical data for the specific prize type only
        historical_data = PrizeEntry.objects.filter(query).select_related(
            'lottery_result', 'lottery_result__lottery'
        ).order_by('-lottery_result__date')[:2000]
        
        # Extract last 4 digits from all ticket numbers
        last_4_digits = []
        for entry in historical_data:
            if entry.ticket_number:
                ticket_str = str(entry.ticket_number).strip()
                # Always get last 4 digits regardless of prize type
                last_4 = ticket_str[-4:] if len(ticket_str) >= 4 else ticket_str.zfill(4)
                if last_4.isdigit() and len(last_4) == 4:
                    last_4_digits.append(last_4)
        
        if not last_4_digits:
            # Generate random 4-digit numbers if no historical data
            return [str(random.randint(1000, 9999)).zfill(4) for _ in range(count)]
        
        # Count frequency of each 4-digit number
        digit_frequency = Counter(last_4_digits)
        most_frequent = digit_frequency.most_common()
        
        result = []
        
        # Add most frequent numbers first
        for num, freq in most_frequent:
            if len(result) >= count:
                break
            result.append(num)
        
        # Fill remaining slots with variations of existing numbers
        while len(result) < count:
            if most_frequent:
                # Take one of the top frequent numbers and create variations
                base_options = most_frequent[:min(5, len(most_frequent))]  # Use top 5 most frequent
                base_num = random.choice(base_options)[0]  # Randomly pick from top options
                base_int = int(base_num)
                
                # Create variations with different ranges for more diversity
                variation_ranges = [(-100, 100), (-500, 500), (-200, 200), (-300, 300), (-50, 50)]
                variation_range = random.choice(variation_ranges)
                
                for attempt in range(100):  # Max attempts to find unique number
                    variation = random.randint(variation_range[0], variation_range[1])
                    new_num = max(0, min(9999, base_int + variation))
                    new_num_str = str(new_num).zfill(4)
                    
                    if new_num_str not in result:
                        result.append(new_num_str)
                        break
                else:
                    # If couldn't create unique variation, use random
                    while True:
                        random_num = str(random.randint(1000, 9999)).zfill(4)
                        if random_num not in result:
                            result.append(random_num)
                            break
            else:
                # No historical data, generate random
                while True:
                    random_num = str(random.randint(1000, 9999)).zfill(4)
                    if random_num not in result:
                        result.append(random_num)
                        break
        
        return result[:count]
    
    def extract_number_components(self, ticket_number, prize_type):
        """Extract meaningful components from ticket numbers"""
        if not ticket_number:
            return None
            
        ticket_number = str(ticket_number).strip().upper()
        
        if prize_type in ['1st', '2nd', '3rd']:
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
        
        if prize_type in ['1st', '2nd', '3rd']:
            alpha_freq = Counter([c['alpha_prefix'] for c in components_list if c['alpha_prefix']])
            digit_freq = Counter([c['digits'] for c in components_list if c['digits']])
            
            common_alpha = alpha_freq.most_common(5)
            common_digits = digit_freq.most_common(10)
            
            if common_digits and lottery_code:
                second_alphabets = []
                for c in components_list:
                    if c['alpha_prefix'] and len(c['alpha_prefix']) >= 2:
                        second_alphabets.append(c['alpha_prefix'][1])
                
                if second_alphabets:
                    second_alpha_freq = Counter(second_alphabets)
                    common_second = second_alpha_freq.most_common(5)
                    weights = [freq for _, freq in common_second]
                    selected_second_alpha = random.choices([alpha for alpha, _ in common_second], weights=weights)[0]
                else:
                    selected_second_alpha = random.choice(self.alphabet_patterns)
                
                digit_weights = [freq for _, freq in common_digits]
                selected_digits = random.choices([digits for digits, _ in common_digits], weights=digit_weights)[0]
                
                if len(selected_digits) >= 4:
                    modified_digits = selected_digits[:-2] + str(random.randint(10, 99))
                    prediction = lottery_code + selected_second_alpha + modified_digits
                else:
                    padded_digits = selected_digits.zfill(6)
                    prediction = lottery_code + selected_second_alpha + padded_digits
            else:
                prediction = self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            
            predictions.append(prediction)
        else:
            last_4_freq = Counter([c['last_4'] for c in components_list if c['last_4']])
            
            if last_4_freq:
                common_last_4 = last_4_freq.most_common(20)
                weights = [freq for _, freq in common_last_4]
                
                used_numbers = set()
                while len(used_numbers) < count:
                    selected = random.choices([num for num, _ in common_last_4], weights=weights)[0]
                    
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
                prediction_batch = [str(random.randint(1000, 9999)) for _ in range(count)]
            
            predictions.extend(prediction_batch)
        
        return predictions[:count]

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
        
        if prize_type in ['1st', '2nd', '3rd']:
            recent_alphas = [c['alpha_prefix'] for c in components_list[:10] if c['alpha_prefix']]
            recent_digits = [c['digits'] for c in components_list[:10] if c['digits']]
            
            if recent_digits and lottery_code:
                second_alphabets = []
                for c in components_list[:10]:
                    if c['alpha_prefix'] and len(c['alpha_prefix']) >= 2:
                        second_alphabets.append(c['alpha_prefix'][1])
                
                if second_alphabets:
                    recent_second = second_alphabets[0] if second_alphabets else 'A'
                    next_second = chr((ord(recent_second) - ord('A') + 1) % 26 + ord('A'))
                else:
                    next_second = random.choice(self.alphabet_patterns)
                
                digit_pattern = self.analyze_digit_trends(recent_digits)
                prediction = lottery_code + next_second + digit_pattern
            else:
                prediction = self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            
            predictions.append(prediction)
        else:
            recent_numbers = [c['last_4'] for c in components_list[:30] if c['last_4'] and c['last_4'].isdigit()]
            
            if len(recent_numbers) >= 3:
                used_numbers = set()
                base_predictions = []
                
                for i in range(0, min(12, len(recent_numbers)), 3):
                    pattern_group = recent_numbers[i:i+3]
                    base_pred = self.predict_next_sequence(pattern_group)
                    base_predictions.append(base_pred)
                
                for base_pred in base_predictions:
                    if len(used_numbers) >= count:
                        break
                    
                    used_numbers.add(base_pred)
                    
                    base_num = int(base_pred) if base_pred.isdigit() else random.randint(1000, 9999)
                    for variation in [-200, -100, -50, 50, 100, 200]:
                        if len(used_numbers) >= count:
                            break
                        varied_num = max(1000, min(9999, base_num + variation))
                        used_numbers.add(str(varied_num).zfill(4))
                
                while len(used_numbers) < count:
                    random_num = str(random.randint(1000, 9999))
                    used_numbers.add(random_num)
                
                predictions = list(used_numbers)[:count]
            else:
                predictions = [str(random.randint(1000, 9999)) for _ in range(count)]
        
        return predictions
    
    def analyze_digit_trends(self, digit_sequence):
        """Analyze trends in digit sequences - ensure 6 digits"""
        if not digit_sequence:
            return str(random.randint(100000, 999999))
        
        recent = digit_sequence[0] if digit_sequence else '000000'
        
        if recent.isdigit():
            base_num = int(recent)
            variation = random.randint(-10000, 10000)
            new_num = max(100000, min(999999, base_num + variation))
            return str(new_num).zfill(6)
        
        return str(random.randint(100000, 999999))
    
    def predict_next_sequence(self, number_sequence):
        """Predict next number in sequence using statistical analysis"""
        numbers = [int(n) for n in number_sequence if n.isdigit()]
        
        if len(numbers) < 2:
            return str(random.randint(1000, 9999))
        
        diffs = [numbers[i] - numbers[i+1] for i in range(len(numbers)-1)]
        
        if diffs:
            avg_diff = sum(diffs) / len(diffs)
            predicted = int(numbers[0] + avg_diff + random.randint(-100, 100))
            predicted = max(1000, min(9999, predicted))
            return str(predicted).zfill(4)
        
        return str(random.randint(1000, 9999))
    
    def ensemble_prediction(self, historical_data, prize_type, count=1, lottery_code=None):
        """Combine multiple prediction methods for better accuracy"""
        freq_predictions = self.frequency_analysis_prediction(historical_data, prize_type, count, lottery_code)
        pattern_predictions = self.pattern_recognition_prediction(historical_data, prize_type, count, lottery_code)
        
        if prize_type in ['1st', '2nd', '3rd']:
            if random.random() < 0.6:
                prediction = freq_predictions[0] if freq_predictions else self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            else:
                prediction = pattern_predictions[0] if pattern_predictions else self.generate_random_numbers(prize_type, 1, lottery_code)[0]
            
            return [prediction]
        else:
            ensemble_predictions = []
            
            freq_count = int(count * 0.6)
            pattern_count = count - freq_count
            
            ensemble_predictions.extend(freq_predictions[:freq_count])
            ensemble_predictions.extend(pattern_predictions[:pattern_count])
            
            while len(ensemble_predictions) < count:
                ensemble_predictions.append(str(random.randint(1000, 9999)))
            
            unique_predictions = list(dict.fromkeys(ensemble_predictions))
            
            while len(unique_predictions) < count:
                new_num = str(random.randint(1000, 9999))
                if new_num not in unique_predictions:
                    unique_predictions.append(new_num)
            
            return unique_predictions[:count]

    def generate_random_numbers(self, prize_type, count=1, lottery_code=None):
        """Generate random numbers as fallback"""
        predictions = []
        
        if prize_type in ['1st', '2nd', '3rd']:
            if lottery_code:
                second_alphabet = random.choice(self.alphabet_patterns)
                digits = ''.join(random.choices(self.digit_patterns, k=6))
                prediction = lottery_code + second_alphabet + digits
            else:
                alpha = ''.join(random.choices(self.alphabet_patterns, k=2))
                digits = ''.join(random.choices(self.digit_patterns, k=6))
                prediction = alpha + digits
            predictions.append(prediction)
        else:
            used_numbers = set()
            while len(used_numbers) < count:
                prediction = ''.join(random.choices(self.digit_patterns, k=4))
                used_numbers.add(prediction)
            predictions = list(used_numbers)
        
        return predictions
    
    def calculate_confidence_score(self, historical_data, prize_type, prediction_method):
        """Calculate confidence score based on historical accuracy and data quality"""
        base_confidence = 0.3
        
        data_count = len(historical_data)
        if data_count > 100:
            data_factor = 0.3
        elif data_count > 50:
            data_factor = 0.2
        elif data_count > 20:
            data_factor = 0.15
        else:
            data_factor = 0.1
        
        method_factors = {
            'frequency': 0.25,
            'pattern': 0.2,
            'ensemble': 0.3,
            'random': 0.1
        }
        method_factor = method_factors.get(prediction_method, 0.1)
        
        prize_factors = {
            '1st': 0.1, '2nd': 0.1, '3rd': 0.1,
            '4th': 0.15, '5th': 0.15, '6th': 0.2, '7th': 0.2, '8th': 0.2, '9th': 0.2
        }
        prize_factor = prize_factors.get(prize_type, 0.1)
        
        confidence = min(0.85, base_confidence + data_factor + method_factor + prize_factor)
        return round(confidence, 2)
    
    def predict(self, lottery_name, prize_type, method='ensemble'):
        """Main prediction method with lottery validation"""
        # Check if consolation prize type is requested
        if prize_type == 'consolation':
            raise ValueError("Consolation prize predictions are not supported")
        
        lottery = self.validate_lottery_exists(lottery_name)
        if not lottery:
            raise ValueError(f"Lottery '{lottery_name}' does not exist")
        
        lottery_code = lottery.code.upper() if lottery.code else None
        historical_data = self.get_historical_data(lottery_name, prize_type)
        
        count_map = {
            '1st': 1, '2nd': 1, '3rd': 1,
            '4th': 12, '5th': 12, '6th': 12, '7th': 12, '8th': 12, '9th': 12, '10th': 12
        }
        count = count_map.get(prize_type, 12)
        
        if method == 'frequency':
            predictions = self.frequency_analysis_prediction(historical_data, prize_type, count, lottery_code)
        elif method == 'pattern':
            predictions = self.pattern_recognition_prediction(historical_data, prize_type, count, lottery_code)
        elif method == 'ensemble':
            predictions = self.ensemble_prediction(historical_data, prize_type, count, lottery_code)
        else:
            predictions = self.generate_random_numbers(prize_type, count, lottery_code)
        
        # Generate repeated numbers for all prize types EXCEPT consolation
        repeated_numbers = []
        if prize_type != 'consolation':
            repeated_numbers = self.get_repeated_numbers(lottery_name, prize_type, 12)
        
        confidence = self.calculate_confidence_score(historical_data, prize_type, method)
        
        return {
            'predictions': predictions,
            'repeated_numbers': repeated_numbers,
            'confidence': confidence,
            'method': method,
            'historical_data_count': len(historical_data),
            'lottery_code': lottery_code
        }
    
    def predict_with_cache(self, lottery_name, prize_type, method='ensemble'):
        """
        Cached version of predict method - MAJOR PERFORMANCE BOOST
        """
        # Try to get from cache first
        cached_result = get_cached_prediction(lottery_name, prize_type)
        if cached_result:
            logger.info(f"Returning cached prediction for {lottery_name}-{prize_type}")
            return cached_result
        
        # Generate new prediction if not cached
        try:
            result = self.predict(lottery_name, prize_type, method)
            
            # Cache the result for 1 hour
            cache_prediction(lottery_name, prize_type, result, timeout=3600)
            
            logger.info(f"Generated and cached new prediction for {lottery_name}-{prize_type}")
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for {lottery_name}-{prize_type}: {e}")
            raise

    def get_historical_data_cached(self, lottery_name=None, prize_type=None, limit=1000):
        """
        Cached version of historical data fetching
        """
        # Try cache first
        cached_data = get_cached_historical_data(lottery_name, prize_type)
        if cached_data:
            logger.info(f"Using cached historical data for {lottery_name}-{prize_type}")
            return cached_data
        
        # Fetch from database
        historical_data = self.get_historical_data(lottery_name, prize_type, limit)
        
        # Convert to list for caching
        data_list = list(historical_data.values(
            'ticket_number', 'prize_type', 'lottery_result__date'
        ))
        
        # Cache for 30 minutes
        cache_historical_data(lottery_name, prize_type, data_list, timeout=1800)
        
        return historical_data
    def get_repeated_numbers_cached(self, lottery_name, prize_type, count=12):
        """
        🚀 CACHED VERSION of get_repeated_numbers - Much faster!
        """
        from results.utils.cache_utils import cache_repeated_numbers, get_cached_repeated_numbers
        
        # Try cache first
        cached_numbers = get_cached_repeated_numbers(lottery_name, prize_type)
        if cached_numbers:
            logger.info(f"⚡ FAST: Using cached repeated numbers for {lottery_name}-{prize_type}")
            return cached_numbers
        
        # Generate new repeated numbers
        logger.info(f"🔄 GENERATING: New repeated numbers for {lottery_name}-{prize_type}")
        repeated_numbers = self.get_repeated_numbers(lottery_name, prize_type, count)
        
        # Cache for 2 hours (repeated numbers change less frequently)
        cache_repeated_numbers(lottery_name, prize_type, repeated_numbers, timeout=7200)
        
        return repeated_numbers
    def get_historical_data(self, lottery_name=None, prize_type=None, limit=1000):
        """
        UPDATED: Use the optimized version by default
        """
        return self.get_historical_data_optimized(lottery_name, prize_type, limit)