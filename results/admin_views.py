# this my admin_views.py

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.contrib.admin import site
from django.contrib.admin.sites import AdminSite
from .models import Lottery, LotteryResult, PrizeEntry


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
        # Validate required fields
        lottery_id = request.POST.get('lottery')
        date = request.POST.get('date')
        draw_number = request.POST.get('draw_number')
        
        if not all([lottery_id, date, draw_number]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('results:add_result')
        
        # Create lottery result
        lottery_result = LotteryResult.objects.create(
            lottery_id=lottery_id,
            date=date,
            draw_number=draw_number,
            is_published=request.POST.get('is_published') == 'on'
        )
        
        # Process prize entries
        prize_types = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', 'consolation']
        
        for prize_type in prize_types:
            prize_amounts = request.POST.getlist(f'{prize_type}_prize_amount[]')
            ticket_numbers = request.POST.getlist(f'{prize_type}_ticket_number[]')
            places = request.POST.getlist(f'{prize_type}_place[]')
            
            for i, (amount, ticket) in enumerate(zip(prize_amounts, ticket_numbers)):
                if amount and ticket:
                    place = places[i] if i < len(places) and prize_type in ['1st', '2nd', '3rd'] else None
                    PrizeEntry.objects.create(
                        lottery_result=lottery_result,
                        prize_type=prize_type,
                        prize_amount=amount,
                        ticket_number=ticket,
                        place=place
                    )
        
        messages.success(request, f'Lottery result for {lottery_result} has been created successfully.')
        return redirect('admin:results_lotteryresult_changelist')
    
    except Exception as e:
        messages.error(request, f'Error creating lottery result: {str(e)}')
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
    try:
        lottery_result = LotteryResult.objects.get(id=result_id)
    except LotteryResult.DoesNotExist:
        messages.error(request, "Lottery result not found.")
        return redirect('admin:results_lotteryresult_changelist')
    
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
        'prize_entries_json': prize_entries_json,
        'is_edit_mode': True,
    }
    return render(request, 'admin/lottery_add_result.html', context)

@csrf_protect
@staff_member_required
def handle_edit_form_submission(request, lottery_result):
    """Handle the form submission for editing lottery results."""
    try:
        # Validate required fields
        lottery_id = request.POST.get('lottery')
        date = request.POST.get('date')
        draw_number = request.POST.get('draw_number')
        
        if not all([lottery_id, date, draw_number]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('results:edit_result', result_id=lottery_result.id)
        
        # Update lottery result
        lottery_result.lottery_id = lottery_id
        lottery_result.date = date
        lottery_result.draw_number = draw_number
        lottery_result.is_published = request.POST.get('is_published') == 'on'
        lottery_result.save()
        
        # Delete existing prize entries
        lottery_result.prizes.all().delete()
        
        # Process prize entries
        prize_types = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', 'consolation']
        
        for prize_type in prize_types:
            prize_amounts = request.POST.getlist(f'{prize_type}_prize_amount[]')
            ticket_numbers = request.POST.getlist(f'{prize_type}_ticket_number[]')
            places = request.POST.getlist(f'{prize_type}_place[]')
            
            for i, (amount, ticket) in enumerate(zip(prize_amounts, ticket_numbers)):
                if amount and ticket:
                    place = places[i] if i < len(places) and prize_type in ['1st', '2nd', '3rd'] else None
                    PrizeEntry.objects.create(
                        lottery_result=lottery_result,
                        prize_type=prize_type,
                        prize_amount=amount,
                        ticket_number=ticket,
                        place=place
                    )
        
        messages.success(request, f'Lottery result for {lottery_result} has been updated successfully.')
        return redirect('admin:results_lotteryresult_changelist')
    
    except Exception as e:
        messages.error(request, f'Error updating lottery result: {str(e)}')
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