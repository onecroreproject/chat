from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import FileAttachment


@login_required
def files_home_view(request):
    """View all uploaded files."""
    files = FileAttachment.objects.filter(uploaded_by=request.user)

    from teams.models import Team
    user_teams = Team.objects.filter(memberships__user=request.user)

    from chat.models import Notification
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'files/files_home.html', {
        'files': files,
        'user_teams': user_teams,
        'unread_notifs': unread_notifs,
    })


@login_required
@require_POST
def upload_file_view(request):
    """Upload a file and return its URL."""
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided.'}, status=400)

    uploaded_file = request.FILES['file']

    # File size limit: 25MB
    if uploaded_file.size > 25 * 1024 * 1024:
        return JsonResponse({'error': 'File too large. Max 25MB.'}, status=400)

    attachment = FileAttachment.objects.create(
        file=uploaded_file,
        original_name=uploaded_file.name,
        file_size=uploaded_file.size,
        file_type=uploaded_file.content_type or '',
        uploaded_by=request.user,
    )

    return JsonResponse({
        'success': True,
        'file': {
            'id': attachment.id,
            'name': attachment.original_name,
            'url': attachment.get_file_url(),
            'size': attachment.get_size_display(),
            'type': attachment.file_type,
            'is_image': attachment.is_image(),
            'icon': attachment.get_icon(),
        }
    })


@login_required
def delete_file_view(request, file_id):
    """Delete a file."""
    try:
        attachment = FileAttachment.objects.get(id=file_id, uploaded_by=request.user)
        attachment.file.delete()
        attachment.delete()
        return JsonResponse({'success': True})
    except FileAttachment.DoesNotExist:
        return JsonResponse({'error': 'File not found.'}, status=404)
