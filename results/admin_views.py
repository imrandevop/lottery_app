# admin_views.py - Updated with simple FCM integration
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect, csrf_exempt
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


def handle_auto_import(request, url):
    """
    Handle automatic import of lottery results from Kerala Lotteries URL or Ponkudam URL
    """
    try:
        from .services.scraper_factory import ScraperFactory
        from .services.lottery_scraper import KeralaLotteryScraper

        messages.info(request, f"🔄 Fetching lottery data from URL...")

        # Scrape the lottery data
        scraped_data = ScraperFactory.scrape_lottery_result(url)

        # Match lottery name to existing lottery
        scraper = KeralaLotteryScraper()
        existing_lotteries = list(Lottery.objects.values_list('id', 'name'))
        matched_lottery_id = scraper.match_lottery_name(
            scraped_data['lottery_name'],
            existing_lotteries
        )

        if not matched_lottery_id:
            messages.warning(
                request,
                f"⚠️ Could not match lottery name '{scraped_data['lottery_name']}' to existing lottery. "
                f"Please create a lottery with this name first or enter data manually."
            )
            return redirect('results:add_result')

        # Create the LotteryResult
        lottery_result = LotteryResult.objects.create(
            lottery_id=matched_lottery_id,
            draw_number=scraped_data['draw_number'],
            date=scraped_data['date'],
            is_published=request.POST.get('is_published') == 'on',
            is_bumper=request.POST.get('is_bumper') == 'on',
            results_ready_notification=request.POST.get('results_ready_notification') == 'on'
        )

        # Create all prize entries
        prizes_created = 0
        for prize_data in scraped_data['prizes']:
            PrizeEntry.objects.create(
                lottery_result=lottery_result,
                prize_type=prize_data['prize_type'],
                prize_amount=prize_data['prize_amount'],
                ticket_number=prize_data['ticket_number'],
                place=prize_data.get('place', '')
            )
            prizes_created += 1

        messages.success(
            request,
            f"✅ Successfully imported {scraped_data['lottery_name']} - {scraped_data['draw_number']} "
            f"with {prizes_created} prize entries!"
        )

        # Redirect to the admin list view
        return redirect('/admin/results/lotteryresult/')

    except Exception as e:
        logger.error(f"Error during auto-import: {e}", exc_info=True)

        messages.error(
            request,
            f"❌ Auto-import failed: {str(e)}. Please try manual entry or check the URL."
        )
        return redirect('results:add_result')


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
        # Check if auto-import from URL is requested
        auto_import_url = request.POST.get('auto_import_url', '').strip()

        if auto_import_url:
            # Handle auto-import from URL (bypass normal validation)
            return handle_auto_import(request, auto_import_url)

        # === MANUAL ENTRY MODE ===
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
            results_ready_notification=cleaned_post.get('results_ready_notification') == 'on',
            # Sort flags for 4th-10th prizes
            sort_4th_prize=cleaned_post.get('sort_4th_prize') == 'on',
            sort_5th_prize=cleaned_post.get('sort_5th_prize') == 'on',
            sort_6th_prize=cleaned_post.get('sort_6th_prize') == 'on',
            sort_7th_prize=cleaned_post.get('sort_7th_prize') == 'on',
            sort_8th_prize=cleaned_post.get('sort_8th_prize') == 'on',
            sort_9th_prize=cleaned_post.get('sort_9th_prize') == 'on',
            sort_10th_prize=cleaned_post.get('sort_10th_prize') == 'on'
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

            # Handle special logic for 2nd, 3rd, consolation and 4th-10th prizes (bulk mode with no place)
            bulk_mode_prizes = ['2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th']

            if prize_type in bulk_mode_prizes:
                # For bulk mode prizes, check if there are tickets without corresponding amounts
                has_tickets = any(ticket.strip() for ticket in ticket_numbers)
                has_valid_amounts = any(amount and amount.strip() and amount.strip() != '0' for amount in prize_amounts)

                if has_tickets and not has_valid_amounts:
                    prize_name = 'Consolation' if prize_type == 'consolation' else f'{prize_type.capitalize()}'
                    messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                    return redirect(request.path)

                # For bulk mode prizes, each amount corresponds to multiple tickets (up to 3)
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
                            # For 2nd and 3rd, add place field from places array if available (normal mode)
                            place = None
                            if prize_type in ['2nd', '3rd'] and i < len(places) and places[i]:
                                place = places[i]

                            PrizeEntry.objects.create(
                                lottery_result=lottery_result,
                                prize_type=prize_type,
                                prize_amount=current_amount,
                                ticket_number=ticket,
                                place=place
                            )
            else:
                # For 1st prize only - check for tickets without amounts
                for i, ticket in enumerate(ticket_numbers):
                    if ticket.strip():  # If there's a ticket number
                        amount = prize_amounts[i] if i < len(prize_amounts) else ''
                        if not amount or amount.strip() == '' or amount.strip() == '0':
                            prize_name = f'{prize_type.capitalize()}'
                            messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                            return redirect(request.path)

                # Original logic for 1st prize only
                for i, (amount, ticket) in enumerate(zip(prize_amounts, ticket_numbers)):
                    if amount and ticket:
                        place = places[i] if i < len(places) and prize_type in ['1st'] else None
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
        # Sort flags for 4th-10th prizes
        lottery_result.sort_4th_prize = cleaned_post.get('sort_4th_prize') == 'on'
        lottery_result.sort_5th_prize = cleaned_post.get('sort_5th_prize') == 'on'
        lottery_result.sort_6th_prize = cleaned_post.get('sort_6th_prize') == 'on'
        lottery_result.sort_7th_prize = cleaned_post.get('sort_7th_prize') == 'on'
        lottery_result.sort_8th_prize = cleaned_post.get('sort_8th_prize') == 'on'
        lottery_result.sort_9th_prize = cleaned_post.get('sort_9th_prize') == 'on'
        lottery_result.sort_10th_prize = cleaned_post.get('sort_10th_prize') == 'on'
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


            # Handle special logic for 2nd, 3rd, consolation and 4th-10th prizes (bulk mode with no place)
            bulk_mode_prizes = ['2nd', '3rd', 'consolation', '4th', '5th', '6th', '7th', '8th', '9th', '10th']

            if prize_type in bulk_mode_prizes:
                # For bulk mode prizes, check if there are tickets without corresponding amounts
                has_tickets = any(ticket.strip() for ticket in ticket_numbers)
                has_valid_amounts = any(amount and amount.strip() and amount.strip() != '0' for amount in prize_amounts)

                if has_tickets and not has_valid_amounts:
                    prize_name = 'Consolation' if prize_type == 'consolation' else f'{prize_type.capitalize()}'
                    messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                    return redirect(request.path)

                # For bulk mode prizes, each amount corresponds to multiple tickets (up to 3)
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
                            # For 2nd and 3rd, add place field from places array if available (normal mode)
                            place = None
                            if prize_type in ['2nd', '3rd'] and i < len(places) and places[i]:
                                place = places[i]

                            PrizeEntry.objects.create(
                                lottery_result=lottery_result,
                                prize_type=prize_type,
                                prize_amount=current_amount,
                                ticket_number=ticket,
                                place=place
                            )
            else:
                # For 1st prize only - check for tickets without amounts
                for i, ticket in enumerate(ticket_numbers):
                    if ticket.strip():  # If there's a ticket number
                        amount = prize_amounts[i] if i < len(prize_amounts) else ''
                        if not amount or amount.strip() == '' or amount.strip() == '0':
                            prize_name = f'{prize_type.capitalize()}'
                            messages.error(request, f'⚠️ No prize amount entered! Please enter the prize amount for {prize_name} prize before saving.')
                            return redirect(request.path)

                # Original logic for 1st prize only
                for i, (amount, ticket) in enumerate(zip(prize_amounts, ticket_numbers)):
                    if amount and ticket:
                        place = places[i] if i < len(places) and prize_type in ['1st'] else None
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


#<-----------------LIVE SCRAPING API ENDPOINTS----------------->
@csrf_protect
@staff_member_required
@require_POST
def start_live_scraping_view(request):
    """
    API endpoint to start live scraping for a Kerala Lottery URL
    """
    try:
        # Parse JSON request body
        data = json.loads(request.body)
        url = data.get('url', '').strip()

        if not url:
            return JsonResponse({
                'success': False,
                'error': 'URL is required'
            }, status=400)

        # Validate URL is from supported lottery websites
        from .services.scraper_factory import ScraperFactory

        if not ScraperFactory.is_supported_url(url):
            supported = ', '.join(ScraperFactory.get_supported_domains())
            return JsonResponse({
                'success': False,
                'error': f'Only the following websites are supported: {supported}'
            }, status=400)

        # Start scraping using service
        from results.services.live_lottery_scraper import LiveScraperService
        result = LiveScraperService.start_scraping(url)

        if result['success']:
            return JsonResponse({
                'success': True,
                'session_id': result['session_id'],
                'lottery_result_id': result['lottery_result_id'],
                'message': result['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['message']
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in start_live_scraping: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@csrf_protect
@staff_member_required
@require_POST
def stop_live_scraping_view(request):
    """
    API endpoint to stop an active scraping session
    """
    try:
        # Parse JSON request body
        data = json.loads(request.body)
        session_id = data.get('session_id')

        if not session_id:
            return JsonResponse({
                'success': False,
                'error': 'Session ID is required'
            }, status=400)

        # Stop scraping using service
        from results.services.live_lottery_scraper import LiveScraperService
        result = LiveScraperService.stop_scraping(session_id)

        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['message']
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in stop_live_scraping: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@csrf_protect
@staff_member_required
def get_live_status_view(request, result_id):
    """
    API endpoint to get live scraping status for a lottery result
    """
    try:
        from results.services.live_lottery_scraper import LiveScraperService
        status = LiveScraperService.get_session_status(result_id)

        return JsonResponse(status)

    except Exception as e:
        logger.error(f"Error in get_live_status: {str(e)}", exc_info=True)
        return JsonResponse({
            'has_session': False,
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
def poll_active_sessions_view(request):
    """
    API endpoint to poll all active scraping sessions
    Called by external cron service (Cron-Job.org) every 1-2 minutes

    Security: Requires Bearer token authentication (CSRF exempt for external API calls)
    Safety: Includes request locking and timeout protection

    Returns:
        JSON response with success status and message
    """
    from django.conf import settings
    from django.db import transaction, DatabaseError
    from results.models import LiveScrapingSession
    import signal
    import time

    # Check for API token authentication
    auth_header = request.headers.get('Authorization', '')
    expected_token = getattr(settings, 'SCRAPER_API_TOKEN', None)

    if not expected_token:
        logger.error("SCRAPER_API_TOKEN not configured in settings")
        return JsonResponse({
            'success': False,
            'error': 'API token not configured on server'
        }, status=500)

    if auth_header != f'Bearer {expected_token}':
        logger.warning(f"Unauthorized polling attempt with token: {auth_header[:20]}...")
        return JsonResponse({
            'success': False,
            'error': 'Unauthorized - Invalid or missing token'
        }, status=401)

    # Database-based locking to prevent concurrent polling
    # Uses a special "lock" session record
    lock_key = 'polling_lock'
    lock_acquired = False

    try:
        with transaction.atomic():
            # Try to create a lock record (will fail if already exists)
            from django.utils import timezone
            try:
                # Check if lock exists and is recent (less than 2 minutes old)
                existing_lock = LiveScrapingSession.objects.filter(
                    scraping_url=lock_key,
                    is_active=True
                ).first()

                if existing_lock:
                    # Check if lock is stale (older than 2 minutes)
                    time_diff = (timezone.now() - existing_lock.last_polled_at).total_seconds()
                    if time_diff < 120:
                        return JsonResponse({
                            'success': False,
                            'message': 'Another polling is in progress',
                            'locked_since': existing_lock.last_polled_at.isoformat()
                        }, status=429)
                    else:
                        # Stale lock, delete it
                        logger.warning(f"Removing stale polling lock from {existing_lock.last_polled_at}")
                        existing_lock.delete()

                # Create new lock
                lock_session = LiveScrapingSession.objects.create(
                    lottery_result=None,
                    scraping_url=lock_key,
                    is_active=True,
                    status='scraping',
                    last_polled_at=timezone.now()
                )
                lock_acquired = True
                logger.info("Polling lock acquired")

            except Exception as lock_error:
                logger.error(f"Failed to acquire lock: {lock_error}")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to acquire polling lock'
                }, status=503)

        # Set timeout to prevent long-running requests
        def timeout_handler(signum, frame):
            raise TimeoutError("Polling exceeded 45 second timeout")

        # Only set timeout on Unix-like systems (not Windows)
        timeout_supported = hasattr(signal, 'SIGALRM')
        if timeout_supported:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(45)  # 45 second timeout

        start_time = time.time()

        try:
            # Call the polling service (same logic as management command)
            from results.services.live_lottery_scraper import LiveScraperService

            logger.info("Starting poll cycle for active sessions")
            LiveScraperService.poll_active_sessions()

            elapsed = time.time() - start_time
            logger.info(f"Polling completed successfully in {elapsed:.2f} seconds")

            # Cancel timeout
            if timeout_supported:
                signal.alarm(0)

            return JsonResponse({
                'success': True,
                'message': f'Polling completed successfully in {elapsed:.2f}s',
                'timestamp': timezone.now().isoformat()
            })

        except TimeoutError:
            logger.error("Polling timeout after 45 seconds")
            return JsonResponse({
                'success': False,
                'error': 'Polling timeout - took longer than 45 seconds'
            }, status=408)

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Polling error after {elapsed:.2f}s: {e}", exc_info=True)

            # Cancel timeout
            if timeout_supported:
                signal.alarm(0)

            return JsonResponse({
                'success': False,
                'error': f'Polling failed: {str(e)}',
                'elapsed_seconds': elapsed
            }, status=500)

    finally:
        # Always release the lock
        if lock_acquired:
            try:
                LiveScrapingSession.objects.filter(scraping_url=lock_key).delete()
                logger.info("Polling lock released")
            except Exception as cleanup_error:
                logger.error(f"Failed to release lock: {cleanup_error}")


