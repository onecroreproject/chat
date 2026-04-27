from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Max, Count, Subquery, OuterRef
from django.utils import timezone
from accounts.models import CustomUser
from .models import ChatMessage, Notification
import json


@login_required
def home_view(request):
    """Main chat home - shows recent conversations."""
    # Get all users the current user has chatted with
    sent_to = ChatMessage.objects.filter(
        sender=request.user,
        receiver__isnull=False
    ).values_list('receiver', flat=True).distinct()

    received_from = ChatMessage.objects.filter(
        receiver=request.user,
        sender__isnull=False
    ).values_list('sender', flat=True).distinct()

    chat_user_ids = set(list(sent_to) + list(received_from))

    conversations = []
    for uid in chat_user_ids:
        other_user = CustomUser.objects.get(id=uid)
        last_msg = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=other_user) |
            Q(sender=other_user, receiver=request.user)
        ).order_by('-timestamp').first()

        unread_count = ChatMessage.objects.filter(
            sender=other_user,
            receiver=request.user,
            seen=False
        ).count()

        conversations.append({
            'user': other_user,
            'last_message': last_msg,
            'unread_count': unread_count,
        })

    # Sort by last message timestamp
    conversations.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else timezone.now(), reverse=True)

    # Get user's teams for sidebar
    from teams.models import Team
    user_teams = Team.objects.filter(memberships__user=request.user)

    # Get unread notification count
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'chat/home.html', {
        'conversations': conversations,
        'user_teams': user_teams,
        'unread_notifs': unread_notifs,
    })


@login_required
def chat_room_view(request, user_id):
    """View 1:1 chat with another user."""
    other_user = get_object_or_404(CustomUser, id=user_id)

    # Mark messages as seen
    ChatMessage.objects.filter(
        sender=other_user,
        receiver=request.user,
        seen=False
    ).update(seen=True)

    messages_list = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')[:200]

    # Get recent conversations for sidebar
    sent_to = ChatMessage.objects.filter(
        sender=request.user, receiver__isnull=False
    ).values_list('receiver', flat=True).distinct()
    received_from = ChatMessage.objects.filter(
        receiver=request.user
    ).values_list('sender', flat=True).distinct()
    chat_user_ids = set(list(sent_to) + list(received_from))

    conversations = []
    for uid in chat_user_ids:
        u = CustomUser.objects.get(id=uid)
        last_msg = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=u) |
            Q(sender=u, receiver=request.user)
        ).order_by('-timestamp').first()
        unread = ChatMessage.objects.filter(sender=u, receiver=request.user, seen=False).count()
        conversations.append({'user': u, 'last_message': last_msg, 'unread_count': unread})
    conversations.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else timezone.now(), reverse=True)

    from teams.models import Team
    user_teams = Team.objects.filter(memberships__user=request.user)
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'chat/chat_room.html', {
        'other_user': other_user,
        'messages': messages_list,
        'conversations': conversations,
        'user_teams': user_teams,
        'unread_notifs': unread_notifs,
    })


@login_required
def get_messages_api(request, user_id):
    """API: Get messages for a 1:1 chat."""
    other_user = get_object_or_404(CustomUser, id=user_id)

    messages_qs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')[:200]

    messages_data = []
    for msg in messages_qs:
        messages_data.append({
            'id': msg.id,
            'sender_id': msg.sender.id,
            'sender_name': msg.sender.get_display_name(),
            'sender_avatar': msg.sender.get_profile_image_url(),
            'message': msg.message,
            'file_url': msg.get_file_url() or '',
            'file_name': msg.get_file_name() or '',
            'is_image': msg.is_image(),
            'is_video': msg.is_video(),
            'is_deleted': msg.is_deleted,
            'edited_at': msg.edited_at.isoformat() if msg.edited_at else None,
            'timestamp': msg.timestamp.isoformat(),
            'seen': msg.seen,
            'delivered': msg.delivered,
        })

    return JsonResponse({'messages': messages_data})


@login_required
@require_POST
def edit_message_api(request, message_id):
    """API: Edit a message."""
    msg = get_object_or_404(ChatMessage, id=message_id, sender=request.user)
    if msg.is_deleted:
        return JsonResponse({'error': 'Cannot edit deleted message.'}, status=400)
    
    data = json.loads(request.body)
    new_text = data.get('message', '').strip()
    if not new_text:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)
    
    msg.message = new_text
    msg.edited_at = timezone.now()
    msg.save()
    
    return JsonResponse({'success': True, 'message': msg.message, 'edited_at': msg.edited_at.isoformat()})


@login_required
@require_POST
def delete_message_api(request, message_id):
    """API: Soft delete a message."""
    msg = get_object_or_404(ChatMessage, id=message_id, sender=request.user)
    msg.is_deleted = True
    msg.message = "This message was deleted"
    msg.save()
    return JsonResponse({'success': True})


@login_required
def mark_seen_api(request, user_id):
    """API: Mark messages from a user as seen."""
    other_user = get_object_or_404(CustomUser, id=user_id)
    ChatMessage.objects.filter(
        sender=other_user,
        receiver=request.user,
        seen=False
    ).update(seen=True)
    return JsonResponse({'success': True})


@login_required
def search_messages_api(request):
    """API: Search messages."""
    query = request.GET.get('q', '')
    chat_user_id = request.GET.get('user_id', '')

    if not query:
        return JsonResponse({'messages': []})

    filters = Q(message__icontains=query) & (
        Q(sender=request.user) | Q(receiver=request.user)
    )

    if chat_user_id:
        filters &= (
            Q(sender_id=chat_user_id, receiver=request.user) |
            Q(sender=request.user, receiver_id=chat_user_id)
        )

    messages_qs = ChatMessage.objects.filter(filters).order_by('-timestamp')[:50]

    results = [{
        'id': m.id,
        'sender_name': m.sender.get_display_name(),
        'message': m.message,
        'timestamp': m.timestamp.isoformat(),
        'chat_user_id': m.receiver.id if m.sender == request.user else m.sender.id,
    } for m in messages_qs if m.receiver]

    return JsonResponse({'messages': results})


@login_required
def get_notifications_api(request):
    """API: Get user notifications."""
    notifs = Notification.objects.filter(user=request.user)[:30]
    data = [{
        'id': n.id,
        'type': n.notif_type,
        'title': n.title,
        'body': n.body,
        'link': n.link,
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat(),
    } for n in notifs]

    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread_count': unread_count})


@login_required
def mark_notification_read_api(request, notif_id):
    """API: Mark a notification as read."""
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'success': True})


@login_required
def start_chat_view(request, user_id):
    """Start or continue a chat with a user."""
    other_user = get_object_or_404(CustomUser, id=user_id)
    return redirect('chat:chat_room', user_id=other_user.id)


@login_required
def activity_view(request):
    """View recent activity and notifications."""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    # Simulate some activities if notifications are empty for a better UI experience
    activities = [
        {'type': 'login', 'title': 'New Login', 'body': 'Logged in from a new device', 'time': timezone.now()},
        {'type': 'team', 'title': 'Team Sync', 'body': 'Marketing team reached 10 members', 'time': timezone.now() - timezone.timedelta(hours=2)},
    ]
    
    return render(request, 'chat/activity.html', {
        'notifications': notifications,
        'activities': activities,
        'active_tab': 'activity'
    })


import calendar
from datetime import datetime

@login_required
def calendar_view(request):
    """View team calendar and events."""
    now = datetime.now()
    month_name = now.strftime('%B %Y')
    today = now.day
    
    # Get days of the week
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Get dates for the current month
    month_calendar = calendar.monthcalendar(now.year, now.month)
    
    # Flatten the calendar and convert 0s (days not in current month) to empty strings
    flat_dates = []
    for week in month_calendar:
        for day in week:
            flat_dates.append(str(day) if day != 0 else "")
            
    return render(request, 'chat/calendar.html', {
        'month_name': month_name,
        'days': days,
        'dates': flat_dates,
        'today': str(today),
        'active_tab': 'calendar'
    })
