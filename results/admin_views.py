# admin_views.py - Updated with simple FCM integration
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.contrib.admin import site
from django.contrib.admin.sites import AdminSite
from .models import Lottery, LotteryResult, PrizeEntry  # Removed NotificationLog import
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import re
from datetime import datetime
import logging

logger = logging.getLogger('lottery_app')

def clean_spaces_from_data(data):
    """
    Helper function to remove spaces from specific fields
    """
    cleaned_data = data.copy()
    
    # Fields that should not have spaces
    # Removed 'name' and 'description' from this list
    no_space_fields = [
        'draw_number', 'ticket_number', 'place', 'code'
    ]
    
    for key, value in cleaned_data.items():
        if isinstance(value, str):
            # Check if this field should not have spaces
            should_clean = any(field in key.lower() for field in no_space_fields)
            if should_clean:
                cleaned_data[key] = re.sub(r'\s+', '', value)
    
    return cleaned_data


def clean_list_data(data_list):
    """
    Clean spaces from list of data (for getlist)
    """
    return [re.sub(r'\s+', '', item) if isinstance(item, str) else item for item in data_list]


@csrf_protect
@staff_member_required
def add_result_view(request):
    """Custom view for adding lottery results with a better UI."""
    if request.method == 'POST':
        return handle_form_submission(request)
    
    # Define prize types for the template
    prize_types = [
        ('1st', '1st Prize'),
        ('consolation', 'Consolation Prize'),
        ('2nd', '2nd Prize'),
        ('3rd', '3rd Prize'),
        ('4th', '4th Prize'),
        ('5th', '5th Prize'),
        ('6th', '6th Prize'),
        ('7th', '7th Prize'),
        ('8th', '8th Prize'),
        ('9th', '9th Prize'),
        ('10th', '10th Prize'),
    ]
    
    # Get admin context for sidebar
    admin_site = site
    
    context = {
        'title': 'Add Lottery Result',
        'lotteries': Lottery.objects.all(),
        'prize_types': prize_types,
        'opts': LotteryResult._meta,
        'has_view_permission': True,
        'has_add_permission': True,
        'has_change_permission': True,
        'has_delete_permission': True,
        # Admin context for sidebar
        'site_header': admin_site.site_header,
        'site_title': admin_site.site_title,
        'site_url': admin_site.site_url,
        'has_permission': admin_site.has_permission(request),
        'available_apps': admin_site.get_app_list(request),
        'is_popup': False,
        'is_nav_sidebar_enabled': True,
        'app_label': 'results',
    }
    return render(request, 'admin/lottery_add_result.html', context)


@csrf_protect
@staff_member_required
def handle_form_submission(request):
    """Handle the form submission for adding lottery results."""
    try:
        # Clean the POST data to remove spaces
        cleaned_post = clean_spaces_from_data(request.POST)
        
        # Validate required fields
        lottery_id = cleaned_post.get('lottery')
        date = cleaned_post.get('date')
        draw_number = cleaned_post.get('draw_number')
        
        if not all([lottery_id, date, draw_number]):
            messages.error(request, 'Please fill in all required fields.')
            
            # For AJAX requests, return the form with errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                prize_types = [
                    ('1st', '1st Prize'),
                    ('consolation', 'Consolation Prize'),
                    ('2nd', '2nd Prize'),
                    ('3rd', '3rd Prize'),
                    ('4th', '4th Prize'),
                    ('5th', '5th Prize'),
                    ('6th', '6th Prize'),
                    ('7th', '7th Prize'),
                    ('8th', '8th Prize'),
                    ('9th', '9th Prize'),
                    ('10th', '10th Prize'),
                ]
                
                admin_site = site
                context = {
                    'title': 'Add Lottery Result',
                    'lotteries': Lottery.objects.all(),
                    'prize_types': prize_types,
                    'opts': LotteryResult._meta,
                    'has_view_permission': True,
                    'has_add_permission': True,
                    'has_change_permission': True,
                    'has_delete_permission': True,
                    'site_header': admin_site.site_header,
                    'site_title': admin_site.site_title,
                    'site_url': admin_site.site_url,
                    'has_permission': admin_site.has_permission(request),
                    'available_apps': admin_site.get_app_list(request),
                    'is_popup': False,
                    'is_nav_sidebar_enabled': True,
                    'app_label': 'results',
                }
                return render(request, 'admin/lottery_add_result.html', context)
            
            # For non-AJAX requests, redirect
            return redirect('results:add_result')
        
        # Get lottery object
        lottery = Lottery.objects.get(id=lottery_id)
        
        # Create lottery result - simplified without manual FCM calls
        lottery_result = LotteryResult.objects.create(
            lottery=lottery,
            date=date,
            draw_number=draw_number,  # Already cleaned of spaces
            is_published=cleaned_post.get('is_published') == 'on',
            is_bumper=cleaned_post.get('is_bumper') == 'on',
            results_ready_notification=cleaned_post.get('results_ready_notification') == 'on'
        )
        
        # Process prize entries
        prize_types = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', 'consolation']
        
        for prize_type in prize_types:
            # Clean the list data to remove spaces
            prize_amounts = clean_list_data(request.POST.getlist(f'{prize_type}_prize_amount[]'))
            ticket_numbers = clean_list_data(request.POST.getlist(f'{prize_type}_ticket_number[]'))
            places = clean_list_data(request.POST.getlist(f'{prize_type}_place[]'))
            
            # SERVER-SIDE VALIDATION: Check 4-digit requirement for 7th-10th prizes
            four_digit_prizes = ['7th', '8th', '9th', '10th']
            if prize_type in four_digit_prizes:
                for ticket in ticket_numbers:
                    if ticket and (not re.match(r'^\d{4}$', ticket) or len(ticket) != 4):
                        prize_name = f'{prize_type.capitalize()}'
                        messages.error(request, f'⚠️ {prize_name} prize requires exactly 4 digits! Ticket "{ticket}" is invalid. Please correct it before saving.')
                        return redirect(request.path)
            
            # Handle special logic for consolation and 4th-10th prizes
            special_prizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th']
            
            if prize_type in special_prizes:
                # For special prizes, check if there are tickets without corresponding amounts
                has_tickets = any(ticket.strip() for ticket in ticket_numbers)
                has_valid_amounts = any(amount and amount.strip() and amount.strip() != '0' for amount in prize_amounts)
                
                if has_tickets and not has_valid_amounts:
                    prize_name = 'Consolation' if prize_type == 'consolation' else f'{prize_type.capitalize()}'
                    messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                    return redirect(request.path)
                
                # For special prizes, each amount corresponds to multiple tickets (up to 3)
                # Tickets are grouped by entries, with up to 3 tickets per entry
                entry_index = 0
                current_amount = None
                
                for i, ticket in enumerate(ticket_numbers):
                    if ticket:  # Only process non-empty tickets
                        # Determine which entry this ticket belongs to (3 tickets per entry)
                        entry_index = i // 3
                        
                        # Get the amount for this entry
                        if entry_index < len(prize_amounts) and prize_amounts[entry_index]:
                            current_amount = prize_amounts[entry_index]
                        
                        if current_amount:
                            PrizeEntry.objects.create(
                                lottery_result=lottery_result,
                                prize_type=prize_type,
                                prize_amount=current_amount,
                                ticket_number=ticket,
                                place=None  # Special prizes don't have places
                            )
            else:
                # For regular prizes (1st, 2nd, 3rd), check for tickets without amounts
                for i, ticket in enumerate(ticket_numbers):
                    if ticket.strip():  # If there's a ticket number
                        amount = prize_amounts[i] if i < len(prize_amounts) else ''
                        if not amount or amount.strip() == '' or amount.strip() == '0':
                            prize_name = f'{prize_type.capitalize()}'
                            messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                            return redirect(request.path)
                
                # Original logic for 1st, 2nd, 3rd prizes
                for i, (amount, ticket) in enumerate(zip(prize_amounts, ticket_numbers)):
                    if amount and ticket:
                        place = places[i] if i < len(places) and prize_type in ['1st', '2nd', '3rd'] else None
                        PrizeEntry.objects.create(
                            lottery_result=lottery_result,
                            prize_type=prize_type,
                            prize_amount=amount,
                            ticket_number=ticket,  # Already cleaned of spaces
                            place=place  # Already cleaned of spaces
                        )
        
        # Show appropriate success message
        if lottery_result.results_ready_notification:
            messages.success(request, f'✅ Lottery result for {lottery_result} has been created successfully and users will be notified! 📱')
        else:
            messages.success(request, f'✅ Lottery result for {lottery_result} has been created successfully.')
        
        # For AJAX requests, return the template with updated context
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Convert prize entries to a format JavaScript can use
            prize_entries_json = {}
            try:
                for prize_type in prize_types:
                    entries = lottery_result.prizes.filter(prize_type=prize_type)
                    prize_entries_json[prize_type] = [
                        {
                            'prize_amount': str(entry.prize_amount),
                            'ticket_number': entry.ticket_number,
                            'place': entry.place or ''
                        }
                        for entry in entries
                    ]
                
                # Convert to JSON string safely
                prize_entries_json_str = json.dumps(prize_entries_json) if prize_entries_json else '{}'
                
            except Exception as e:
                print(f"Error preparing prize entries JSON: {e}")
                prize_entries_json_str = '{}'
            
            # Get admin context for sidebar
            admin_site = site
            
            context = {
                'title': 'Edit Lottery Result',
                'lotteries': Lottery.objects.all(),
                'prize_types': [
                    ('1st', '1st Prize'),
                    ('consolation', 'Consolation Prize'),
                    ('2nd', '2nd Prize'),
                    ('3rd', '3rd Prize'),
                    ('4th', '4th Prize'),
                    ('5th', '5th Prize'),
                    ('6th', '6th Prize'),
                    ('7th', '7th Prize'),
                    ('8th', '8th Prize'),
                    ('9th', '9th Prize'),
                    ('10th', '10th Prize'),
                ],
                'opts': LotteryResult._meta,
                'has_view_permission': True,
                'has_add_permission': True,
                'has_change_permission': True,
                'has_delete_permission': True,
                # Admin context for sidebar
                'site_header': admin_site.site_header,
                'site_title': admin_site.site_title,
                'site_url': admin_site.site_url,
                'has_permission': admin_site.has_permission(request),
                'available_apps': admin_site.get_app_list(request),
                'is_popup': False,
                'is_nav_sidebar_enabled': True,
                'app_label': 'results',
                # Lottery result data
                'lottery_result': lottery_result,
                'prize_entries_json': prize_entries_json_str,  # Safe JSON string
                'is_edit_mode': True,
            }
            return render(request, 'admin/lottery_add_result.html', context)
        
        # For non-AJAX requests, redirect
        return redirect(request.path)

    
    except Exception as e:
        messages.error(request, f'Error creating lottery result: {str(e)}')
        logger.error(f"❌ Error creating lottery result: {e}")
        # Get admin context for error case too
        admin_site = site
        context = {
            'title': 'Add Lottery Result',
            'lotteries': Lottery.objects.all(),
            'error': str(e),
            'opts': LotteryResult._meta,
            'has_view_permission': True,
            'has_add_permission': True,
            'has_change_permission': True,
            'has_delete_permission': True,
            # Admin context for sidebar
            'site_header': admin_site.site_header,
            'site_title': admin_site.site_title,
            'site_url': admin_site.site_url,
            'has_permission': admin_site.has_permission(request),
            'available_apps': admin_site.get_app_list(request),
            'is_popup': False,
            'is_nav_sidebar_enabled': True,
            'app_label': 'results',
        }
        return render(request, 'admin/lottery_add_result.html', context)


@csrf_protect
@staff_member_required
def edit_result_view(request, result_id):
    """Custom view for editing lottery results with a better UI."""
    lottery_result = get_object_or_404(LotteryResult, id=result_id)
    
    if request.method == 'POST':
        # Handle form submission for edit
        return handle_edit_form_submission(request, lottery_result)
    
    # Define prize types for the template
    prize_types = [
        ('1st', '1st Prize'),
        ('consolation', 'Consolation Prize'),
        ('2nd', '2nd Prize'),
        ('3rd', '3rd Prize'),
        ('4th', '4th Prize'),
        ('5th', '5th Prize'),
        ('6th', '6th Prize'),
        ('7th', '7th Prize'),
        ('8th', '8th Prize'),
        ('9th', '9th Prize'),
        ('10th', '10th Prize'),
        
    ]
    
    # Get admin context for sidebar
    admin_site = site
    
    # Convert prize entries to a format JavaScript can use
    prize_entries_json = {}
    try:
        for prize_type, _ in prize_types:
            entries = lottery_result.prizes.filter(prize_type=prize_type)
            prize_entries_json[prize_type] = [
                {
                    'prize_amount': str(entry.prize_amount),
                    'ticket_number': entry.ticket_number,
                    'place': entry.place or ''
                }
                for entry in entries
            ]
        
        # Convert to JSON string safely
        prize_entries_json_str = json.dumps(prize_entries_json) if prize_entries_json else '{}'
        
    except Exception as e:
        print(f"Error preparing prize entries JSON: {e}")
        prize_entries_json_str = '{}'
    
    context = {
        'title': 'Edit Lottery Result',
        'lotteries': Lottery.objects.all(),
        'prize_types': prize_types,
        'opts': LotteryResult._meta,
        'has_view_permission': True,
        'has_add_permission': True,
        'has_change_permission': True,
        'has_delete_permission': True,
        # Admin context for sidebar
        'site_header': admin_site.site_header,
        'site_title': admin_site.site_title,
        'site_url': admin_site.site_url,
        'has_permission': admin_site.has_permission(request),
        'available_apps': admin_site.get_app_list(request),
        'is_popup': False,
        'is_nav_sidebar_enabled': True,
        'app_label': 'results',
        # Lottery result data
        'lottery_result': lottery_result,
        'prize_entries_json': prize_entries_json_str,  # Safe JSON string
        'is_edit_mode': True,
    }
    return render(request, 'admin/lottery_add_result.html', context)

@csrf_protect
@staff_member_required
def handle_edit_form_submission(request, lottery_result):
    """Handle the form submission for editing lottery results."""
    try:
        # Clean the POST data to remove spaces
        cleaned_post = clean_spaces_from_data(request.POST)
        
        # Validate required fields
        lottery_id = cleaned_post.get('lottery')
        date = cleaned_post.get('date')
        draw_number = cleaned_post.get('draw_number')
        
        if not all([lottery_id, date, draw_number]):
            messages.error(request, 'Please fill in all required fields.')
            
            # For AJAX requests, return the form with errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                prize_types = [
                    ('1st', '1st Prize'),
                    ('consolation', 'Consolation Prize'),
                    ('2nd', '2nd Prize'),
                    ('3rd', '3rd Prize'),
                    ('4th', '4th Prize'),
                    ('5th', '5th Prize'),
                    ('6th', '6th Prize'),
                    ('7th', '7th Prize'),
                    ('8th', '8th Prize'),
                    ('9th', '9th Prize'),
                    ('10th', '10th Prize'),
                ]
                
                admin_site = site
                context = {
                    'title': 'Edit Lottery Result',
                    'lotteries': Lottery.objects.all(),
                    'prize_types': prize_types,
                    'opts': LotteryResult._meta,
                    'has_view_permission': True,
                    'has_add_permission': True,
                    'has_change_permission': True,
                    'has_delete_permission': True,
                    'site_header': admin_site.site_header,
                    'site_title': admin_site.site_title,
                    'site_url': admin_site.site_url,
                    'has_permission': admin_site.has_permission(request),
                    'available_apps': admin_site.get_app_list(request),
                    'is_popup': False,
                    'is_nav_sidebar_enabled': True,
                    'app_label': 'results',
                    'lottery_result': lottery_result,
                    'is_edit_mode': True,
                }
                return render(request, 'admin/lottery_add_result.html', context)
            
            # For non-AJAX requests, redirect
            return redirect('results:edit_result', result_id=lottery_result.id)
        
        # Store previous notification state to check if checkbox was newly checked
        previous_notification_state = lottery_result.results_ready_notification
        
        # Update lottery result
        lottery_result.lottery_id = lottery_id
        lottery_result.date = date
        lottery_result.draw_number = draw_number  # Already cleaned of spaces
        lottery_result.is_published = cleaned_post.get('is_published') == 'on'
        lottery_result.is_bumper = cleaned_post.get('is_bumper') == 'on'
        lottery_result.results_ready_notification = cleaned_post.get('results_ready_notification') == 'on'
        lottery_result.save()
        
        # Delete existing prize entries
        lottery_result.prizes.all().delete()
        
        # Process prize entries
        prize_types = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', 'consolation']
        
        for prize_type in prize_types:
            # Clean the list data to remove spaces
            prize_amounts = clean_list_data(request.POST.getlist(f'{prize_type}_prize_amount[]'))
            ticket_numbers = clean_list_data(request.POST.getlist(f'{prize_type}_ticket_number[]'))
            places = clean_list_data(request.POST.getlist(f'{prize_type}_place[]'))
            
            # SERVER-SIDE VALIDATION: Check 4-digit requirement for 7th-10th prizes
            four_digit_prizes = ['7th', '8th', '9th', '10th']
            if prize_type in four_digit_prizes:
                for ticket in ticket_numbers:
                    if ticket and (not re.match(r'^\d{4}$', ticket) or len(ticket) != 4):
                        prize_name = f'{prize_type.capitalize()}'
                        messages.error(request, f'⚠️ {prize_name} prize requires exactly 4 digits! Ticket "{ticket}" is invalid. Please correct it before saving.')
                        return redirect(request.path)
            
            
            # Handle special logic for consolation and 4th-10th prizes
            special_prizes = ['consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th']
            
            if prize_type in special_prizes:
                # For special prizes, check if there are tickets without corresponding amounts
                has_tickets = any(ticket.strip() for ticket in ticket_numbers)
                has_valid_amounts = any(amount and amount.strip() and amount.strip() != '0' for amount in prize_amounts)
                
                if has_tickets and not has_valid_amounts:
                    prize_name = 'Consolation' if prize_type == 'consolation' else f'{prize_type.capitalize()}'
                    messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                    return redirect(request.path)
                
                # For special prizes, each amount corresponds to multiple tickets (up to 3)
                # Tickets are grouped by entries, with up to 3 tickets per entry
                entry_index = 0
                current_amount = None
                
                for i, ticket in enumerate(ticket_numbers):
                    if ticket:  # Only process non-empty tickets
                        # Determine which entry this ticket belongs to (3 tickets per entry)
                        entry_index = i // 3
                        
                        # Get the amount for this entry
                        if entry_index < len(prize_amounts) and prize_amounts[entry_index]:
                            current_amount = prize_amounts[entry_index]
                        
                        if current_amount:
                            PrizeEntry.objects.create(
                                lottery_result=lottery_result,
                                prize_type=prize_type,
                                prize_amount=current_amount,
                                ticket_number=ticket,
                                place=None  # Special prizes don't have places
                            )
            else:
                # For regular prizes (1st, 2nd, 3rd), check for tickets without amounts
                for i, ticket in enumerate(ticket_numbers):
                    if ticket.strip():  # If there's a ticket number
                        amount = prize_amounts[i] if i < len(prize_amounts) else ''
                        if not amount or amount.strip() == '' or amount.strip() == '0':
                            prize_name = f'{prize_type.capitalize()}'
                            messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                            return redirect(request.path)
                
                # Original logic for 1st, 2nd, 3rd prizes
                for i, (amount, ticket) in enumerate(zip(prize_amounts, ticket_numbers)):
                    if amount and ticket:
                        place = places[i] if i < len(places) and prize_type in ['1st', '2nd', '3rd'] else None
                        PrizeEntry.objects.create(
                            lottery_result=lottery_result,
                            prize_type=prize_type,
                            prize_amount=amount,
                            ticket_number=ticket,  # Already cleaned of spaces
                            place=place  # Already cleaned of spaces
                        )
        
        # Show appropriate success message
        newly_checked_notification = (
            lottery_result.results_ready_notification and 
            not previous_notification_state
        )
        
        if newly_checked_notification:
            messages.success(request, f'✅ Lottery result for {lottery_result} has been updated successfully and users will be notified! 📱')
        else:
            messages.success(request, f'✅ Lottery result for {lottery_result} has been updated successfully.')
        
        # For AJAX requests, return the template with updated context
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Convert prize entries to a format JavaScript can use
            prize_entries_json = {}
            try:
                for prize_type in prize_types:
                    entries = lottery_result.prizes.filter(prize_type=prize_type)
                    prize_entries_json[prize_type] = [
                        {
                            'prize_amount': str(entry.prize_amount),
                            'ticket_number': entry.ticket_number,
                            'place': entry.place or ''
                        }
                        for entry in entries
                    ]
                
                # Convert to JSON string safely
                prize_entries_json_str = json.dumps(prize_entries_json) if prize_entries_json else '{}'
                
            except Exception as e:
                print(f"Error preparing prize entries JSON: {e}")
                prize_entries_json_str = '{}'
            
            # Get admin context for sidebar
            admin_site = site
            
            context = {
                'title': 'Edit Lottery Result',
                'lotteries': Lottery.objects.all(),
                'prize_types': [
                    ('1st', '1st Prize'),
                    ('consolation', 'Consolation Prize'),
                    ('2nd', '2nd Prize'),
                    ('3rd', '3rd Prize'),
                    ('4th', '4th Prize'),
                    ('5th', '5th Prize'),
                    ('6th', '6th Prize'),
                    ('7th', '7th Prize'),
                    ('8th', '8th Prize'),
                    ('9th', '9th Prize'),
                    ('10th', '10th Prize'),
                ],
                'opts': LotteryResult._meta,
                'has_view_permission': True,
                'has_add_permission': True,
                'has_change_permission': True,
                'has_delete_permission': True,
                # Admin context for sidebar
                'site_header': admin_site.site_header,
                'site_title': admin_site.site_title,
                'site_url': admin_site.site_url,
                'has_permission': admin_site.has_permission(request),
                'available_apps': admin_site.get_app_list(request),
                'is_popup': False,
                'is_nav_sidebar_enabled': True,
                'app_label': 'results',
                # Lottery result data
                'lottery_result': lottery_result,
                'prize_entries_json': prize_entries_json_str,  # Safe JSON string
                'is_edit_mode': True,
            }
            return render(request, 'admin/lottery_add_result.html', context)
        
        # For non-AJAX requests, redirect
        return redirect(request.path)

    
    except Exception as e:
        messages.error(request, f'Error updating lottery result: {str(e)}')
        logger.error(f"❌ Error updating lottery result: {e}")
        # Get admin context for error case too
        admin_site = site
        context = {
            'title': 'Edit Lottery Result',
            'lotteries': Lottery.objects.all(),
            'error': str(e),
            'opts': LotteryResult._meta,
            'has_view_permission': True,
            'has_add_permission': True,
            'has_change_permission': True,
            'has_delete_permission': True,
            # Admin context for sidebar
            'site_header': admin_site.site_header,
            'site_title': admin_site.site_title,
            'site_url': admin_site.site_url,
            'has_permission': admin_site.has_permission(request),
            'available_apps': admin_site.get_app_list(request),
            'is_popup': False,
            'is_nav_sidebar_enabled': True,
            'app_label': 'results',
            # Lottery result data
            'lottery_result': lottery_result,
            'is_edit_mode': True,
        }
        return render(request, 'admin/lottery_add_result.html', context)


@csrf_protect
@staff_member_required
@require_POST
def auto_save_ticket(request):
    """Auto-save ticket number for 4th-10th prizes."""
    try:
        # Parse JSON request body
        data = json.loads(request.body)
        
        # Extract data
        result_id = data.get('result_id')
        prize_type = data.get('prize_type')
        ticket_number = data.get('ticket_number', '').strip()
        prize_amount = data.get('prize_amount', '').strip()
        original_ticket = data.get('original_ticket_number', '').strip()  # Track original ticket number
        
        # Validate required fields
        if not all([result_id, prize_type, ticket_number, prize_amount]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)
        
        # Validate prize type (only 4th-10th allowed)
        allowed_prize_types = ['4th', '5th', '6th', '7th', '8th', '9th', '10th']
        if prize_type not in allowed_prize_types:
            return JsonResponse({
                'success': False,
                'error': 'Auto-save only allowed for 4th-10th prizes'
            }, status=400)
        
        # Clean spaces from ticket number
        cleaned_ticket = re.sub(r'\s+', '', ticket_number)
        cleaned_original = re.sub(r'\s+', '', original_ticket) if original_ticket else ''
        
        if not cleaned_ticket:
            return JsonResponse({
                'success': False,
                'error': 'Invalid ticket number'
            }, status=400)
        
        # Get lottery result
        try:
            lottery_result = LotteryResult.objects.get(id=result_id)
        except LotteryResult.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Lottery result not found'
            }, status=404)
        
        # If this is an edit of existing ticket (original_ticket provided)
        if cleaned_original and cleaned_original != cleaned_ticket:
            # Find the entry with the original ticket number
            original_entry = PrizeEntry.objects.filter(
                lottery_result=lottery_result,
                prize_type=prize_type,
                ticket_number=cleaned_original
            ).first()
            
            if original_entry:
                # Check if the new ticket number already exists (would create duplicate)
                duplicate_entry = PrizeEntry.objects.filter(
                    lottery_result=lottery_result,
                    prize_type=prize_type,
                    ticket_number=cleaned_ticket
                ).exclude(id=original_entry.id).first()
                
                if duplicate_entry:
                    return JsonResponse({
                        'success': False,
                        'error': f'Ticket number {cleaned_ticket} already exists for {prize_type} prize'
                    }, status=400)
                
                # Update the original entry with new ticket number and amount
                original_entry.ticket_number = cleaned_ticket
                original_entry.prize_amount = prize_amount
                original_entry.save(update_fields=['ticket_number', 'prize_amount'])
                
                logger.info(f"Updated ticket from {cleaned_original} to {cleaned_ticket} for {prize_type} prize in result {result_id}")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Ticket updated successfully',
                    'action': 'updated',
                    'entry_id': original_entry.id
                })
        
        # Check if ticket already exists for this prize type
        existing_entry = PrizeEntry.objects.filter(
            lottery_result=lottery_result,
            prize_type=prize_type,
            ticket_number=cleaned_ticket
        ).first()
        
        if existing_entry:
            # Update existing entry with new prize amount if needed
            if str(existing_entry.prize_amount) != str(prize_amount):
                existing_entry.prize_amount = prize_amount
                existing_entry.save(update_fields=['prize_amount'])
                return JsonResponse({
                    'success': True,
                    'message': 'Ticket updated successfully',
                    'action': 'updated',
                    'entry_id': existing_entry.id
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Ticket already exists',
                    'action': 'existing',
                    'entry_id': existing_entry.id
                })
        
        # Create new prize entry
        prize_entry = PrizeEntry.objects.create(
            lottery_result=lottery_result,
            prize_type=prize_type,
            prize_amount=prize_amount,
            ticket_number=cleaned_ticket,
            place=None  # Special prizes don't have places
        )
        
        logger.info(f"Auto-saved ticket: {cleaned_ticket} for {prize_type} prize in result {result_id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Ticket saved successfully',
            'action': 'created',
            'entry_id': prize_entry.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in auto_save_ticket: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


