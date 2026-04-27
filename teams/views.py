from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
import json

from .models import Team, Channel, Membership
from accounts.models import CustomUser
from chat.models import ChatMessage


@login_required
def teams_home_view(request):
    """Display all teams the user belongs to."""
    user_teams = Team.objects.filter(memberships__user=request.user)
    return render(request, 'teams/teams_home.html', {'teams': user_teams})


@login_required
def create_team_view(request):
    """Create a new team."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            return JsonResponse({'error': 'Team name is required.'}, status=400)

        team = Team.objects.create(
            name=name,
            description=description,
            created_by=request.user
        )

        # Add creator as admin
        Membership.objects.create(user=request.user, team=team, role='admin')

        # Create default General channel
        Channel.objects.create(team=team, name='General', is_default=True)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'team': {
                    'id': team.id,
                    'name': team.name,
                    'description': team.description,
                }
            })

        messages.success(request, f'Team "{name}" created successfully!')
        return redirect('teams:team_detail', team_id=team.id)

    return render(request, 'teams/create_team.html')


@login_required
def team_detail_view(request, team_id):
    """Redirect to the default channel of the team."""
    team = get_object_or_404(Team, id=team_id)
    membership = Membership.objects.filter(user=request.user, team=team).first()

    if not membership:
        messages.error(request, 'You are not a member of this team.')
        return redirect('teams:teams_home')

    # Get the default channel (usually 'General') or the first one available
    channel = team.channels.filter(is_default=True).first() or team.channels.first()
    if not channel:
        # Create a General channel if none exists
        channel = Channel.objects.create(team=team, name='General', is_default=True)
        
    return redirect('teams:channel', team_id=team.id, channel_id=channel.id)


@login_required
def channel_view(request, team_id, channel_id):
    """View channel conversation."""
    team = get_object_or_404(Team, id=team_id)
    channel = get_object_or_404(Channel, id=channel_id, team=team)
    membership = Membership.objects.filter(user=request.user, team=team).first()

    if not membership:
        messages.error(request, 'You are not a member of this team.')
        return redirect('teams:teams_home')

    channel_messages = ChatMessage.objects.filter(channel=channel).order_by('timestamp')[:100]
    members = Membership.objects.filter(team=team).select_related('user')
    user_teams = Team.objects.filter(memberships__user=request.user)

    return render(request, 'teams/channel.html', {
        'team': team,
        'channel': channel,
        'messages': channel_messages,
        'members': members,
        'membership': membership,
        'user_teams': user_teams,
    })


@login_required
@require_POST
def create_channel_view(request, team_id):
    """Create a new channel in a team."""
    team = get_object_or_404(Team, id=team_id)
    membership = Membership.objects.filter(user=request.user, team=team).first()

    if not membership or membership.role != 'admin':
        return JsonResponse({'error': 'Only admins can create channels.'}, status=403)

    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    name = data.get('name', '').strip()

    if not name:
        return JsonResponse({'error': 'Channel name is required.'}, status=400)

    if Channel.objects.filter(team=team, name=name).exists():
        return JsonResponse({'error': 'Channel with this name already exists.'}, status=400)

    channel = Channel.objects.create(
        team=team,
        name=name,
        description=data.get('description', '')
    )

    return JsonResponse({
        'success': True,
        'channel': {
            'id': channel.id,
            'name': channel.name,
        }
    })


@login_required
@require_POST
def add_member_view(request, team_id):
    """Add a member to the team."""
    team = get_object_or_404(Team, id=team_id)
    membership = Membership.objects.filter(user=request.user, team=team).first()

    if not membership or membership.role != 'admin':
        return JsonResponse({'error': 'Only admins can add members.'}, status=403)

    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    user_id = data.get('user_id')

    try:
        user_to_add = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)

    if Membership.objects.filter(user=user_to_add, team=team).exists():
        return JsonResponse({'error': 'User is already a member.'}, status=400)

    Membership.objects.create(user=user_to_add, team=team, role='member')

    return JsonResponse({
        'success': True,
        'member': {
            'id': user_to_add.id,
            'username': user_to_add.username,
            'display_name': user_to_add.get_display_name(),
            'profile_image': user_to_add.get_profile_image_url(),
        }
    })


@login_required
@require_POST
def remove_member_view(request, team_id):
    """Remove a member from the team."""
    team = get_object_or_404(Team, id=team_id)
    membership = Membership.objects.filter(user=request.user, team=team).first()

    if not membership or membership.role != 'admin':
        return JsonResponse({'error': 'Only admins can remove members.'}, status=403)

    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    user_id = data.get('user_id')

    if int(user_id) == request.user.id:
        return JsonResponse({'error': 'You cannot remove yourself.'}, status=400)

    member = Membership.objects.filter(user_id=user_id, team=team).first()
    if not member:
        return JsonResponse({'error': 'Member not found.'}, status=404)

    member.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def delete_channel_view(request, team_id, channel_id):
    """Delete a channel from a team."""
    team = get_object_or_404(Team, id=team_id)
    channel = get_object_or_404(Channel, id=channel_id, team=team)
    membership = Membership.objects.filter(user=request.user, team=team).first()

    if not membership or membership.role != 'admin':
        return JsonResponse({'error': 'Only admins can delete channels.'}, status=403)

    if channel.is_default:
        return JsonResponse({'error': 'Cannot delete the default channel.'}, status=400)

    channel.delete()
    return JsonResponse({'success': True})


@login_required
def get_team_channels_api(request, team_id):
    """API: Get all channels of a team."""
    team = get_object_or_404(Team, id=team_id)
    if not Membership.objects.filter(user=request.user, team=team).exists():
        return JsonResponse({'error': 'Not a member.'}, status=403)

    channels = list(team.channels.values('id', 'name', 'is_default'))
    return JsonResponse({'channels': channels})


@login_required
def get_team_members_api(request, team_id):
    """API: Get all members of a team."""
    team = get_object_or_404(Team, id=team_id)
    if not Membership.objects.filter(user=request.user, team=team).exists():
        return JsonResponse({'error': 'Not a member.'}, status=403)

    members = []
    for m in Membership.objects.filter(team=team).select_related('user'):
        members.append({
            'id': m.user.id,
            'username': m.user.username,
            'display_name': m.user.get_display_name(),
            'profile_image': m.user.get_profile_image_url(),
            'role': m.role,
            'is_online': m.user.is_online,
        })

    return JsonResponse({'members': members})
