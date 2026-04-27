from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from .models import CustomUser, OTPVerification
from .forms import (
    RegisterForm, LoginForm, OTPForm,
    ForgotPasswordForm, ResetPasswordForm, ProfileEditForm
)


def register_view(request):
    """User registration with email OTP verification."""
    if request.user.is_authenticated:
        return redirect('chat:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.is_verified = False
            user.save()

            # Generate and send OTP
            otp_code = OTPVerification.generate_otp()
            OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                otp_type='registration'
            )

            # Send OTP email
            send_mail(
                'TeamSync - Verify Your Email',
                f'Your verification code is: {otp_code}\n\nThis code expires in 10 minutes.',
                settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER else 'noreply@teamsync.com',
                [user.email],
                fail_silently=False,
            )

            request.session['pending_user_id'] = user.id
            messages.success(request, 'Account created! Please verify your email with the OTP sent.')
            return redirect('accounts:verify_otp')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_otp_view(request):
    """Verify OTP for email verification."""
    user_id = request.session.get('pending_user_id')
    if not user_id:
        messages.error(request, 'No pending verification found.')
        return redirect('accounts:register')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('accounts:register')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            otp_obj = OTPVerification.objects.filter(
                user=user,
                otp_code=otp_code,
                otp_type='registration',
                is_used=False
            ).first()

            if otp_obj and otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                user.is_verified = True
                user.save()
                del request.session['pending_user_id']
                login(request, user)
                messages.success(request, 'Email verified successfully! Welcome to TeamSync.')
                return redirect('chat:home')
            else:
                messages.error(request, 'Invalid or expired OTP. Please try again.')
    else:
        form = OTPForm()

    return render(request, 'accounts/verify_otp.html', {'form': form, 'email': user.email})


def resend_otp_view(request):
    """Resend OTP for pending verification."""
    user_id = request.session.get('pending_user_id') or request.session.get('reset_user_id')
    if not user_id:
        return JsonResponse({'error': 'No pending verification.'}, status=400)

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)

    otp_type = 'password_reset' if request.session.get('reset_user_id') else 'registration'

    # Generate new OTP
    otp_code = OTPVerification.generate_otp()
    OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        otp_type=otp_type
    )

    send_mail(
        'TeamSync - New Verification Code',
        f'Your new verification code is: {otp_code}\n\nThis code expires in 10 minutes.',
        settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER else 'noreply@teamsync.com',
        [user.email],
        fail_silently=False,
    )

    return JsonResponse({'success': 'OTP resent successfully.'})


def login_view(request):
    """User login with email and password."""
    if request.user.is_authenticated:
        return redirect('chat:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)

            if user is not None:
                if not user.is_verified:
                    # Send new OTP
                    otp_code = OTPVerification.generate_otp()
                    OTPVerification.objects.create(
                        user=user,
                        otp_code=otp_code,
                        otp_type='registration'
                    )
                    send_mail(
                        'TeamSync - Verify Your Email',
                        f'Your verification code is: {otp_code}\n\nThis code expires in 10 minutes.',
                        settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER else 'noreply@teamsync.com',
                        [user.email],
                        fail_silently=False,
                    )
                    request.session['pending_user_id'] = user.id
                    messages.warning(request, 'Please verify your email first.')
                    return redirect('accounts:verify_otp')

                user.is_online = True
                user.save(update_fields=['is_online'])
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_display_name()}!')
                return redirect('chat:home')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout."""
    if request.method == 'POST':
        request.user.is_online = False
        request.user.last_seen = timezone.now()
        request.user.save(update_fields=['is_online', 'last_seen'])
        logout(request)
        messages.success(request, 'You have been logged out.')
        return redirect('accounts:login')
    return render(request, 'accounts/logout_confirm.html')


def forgot_password_view(request):
    """Forgot password - send OTP to email."""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                otp_code = OTPVerification.generate_otp()
                OTPVerification.objects.create(
                    user=user,
                    otp_code=otp_code,
                    otp_type='password_reset'
                )
                send_mail(
                    'TeamSync - Password Reset',
                    f'Your password reset code is: {otp_code}\n\nThis code expires in 10 minutes.',
                    settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER else 'noreply@teamsync.com',
                    [user.email],
                    fail_silently=False,
                )
                request.session['reset_user_id'] = user.id
                messages.success(request, 'Password reset OTP sent to your email.')
                return redirect('accounts:reset_password')
            except CustomUser.DoesNotExist:
                messages.error(request, 'No account found with this email.')
    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})


def reset_password_view(request):
    """Reset password with OTP verification."""
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'No password reset request found.')
        return redirect('accounts:forgot_password')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('accounts:forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            new_password = form.cleaned_data['new_password']

            otp_obj = OTPVerification.objects.filter(
                user=user,
                otp_code=otp_code,
                otp_type='password_reset',
                is_used=False
            ).first()

            if otp_obj and otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                user.set_password(new_password)
                user.save()
                del request.session['reset_user_id']
                messages.success(request, 'Password reset successful! Please login.')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid or expired OTP.')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form, 'email': user.email})


@login_required
def profile_view(request):
    """View user profile."""
    return render(request, 'accounts/profile.html', {'profile_user': request.user})


@login_required
def edit_profile_view(request):
    """Edit user profile."""
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def search_users_view(request):
    """Search users by username or email."""
    query = request.GET.get('q', '')
    users = []
    if query:
        users = CustomUser.objects.filter(
            models.Q(username__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query)
        ).exclude(id=request.user.id)[:20]

    results = [{
        'id': u.id,
        'username': u.username,
        'display_name': u.get_display_name(),
        'email': u.email,
        'profile_image': u.get_profile_image_url(),
        'is_online': u.is_online,
    } for u in users]

    return JsonResponse({'users': results})
