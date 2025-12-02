from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User

from .forms import (
    EmployerRegistrationForm,
    JobSeekerRegistrationForm,
    LoginForm
)

from .models import EmployerProfile, JobSeekerProfile


# -----------------------------
# Register Employer
# -----------------------------
def register_employer(request):
    if request.method == 'POST':
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # create user
            user = User.objects.create_user(username=username, password=password)

            # create employer profile
            employer_profile = form.save(commit=False)
            employer_profile.user = user
            employer_profile.save()

            messages.success(request, "Employer registered successfully!")
            return redirect('login')
    else:
        form = EmployerRegistrationForm()

    return render(request, 'accounts/register_employer.html', {'form': form})


# -----------------------------
# Register JobSeeker
# -----------------------------
def register_jobseeker(request):
    if request.method == 'POST':
        form = JobSeekerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # create user
            user = User.objects.create_user(username=username, password=password)

            # create jobseeker profile
            jobseeker_profile = form.save(commit=False)
            jobseeker_profile.user = user
            jobseeker_profile.save()

            messages.success(request, "Jobseeker registered successfully!")
            return redirect('login')
    else:
        form = JobSeekerRegistrationForm()

    return render(request, 'accounts/register_jobseeker.html', {'form': form})


# -----------------------------
# Login View
# -----------------------------
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)
                messages.success(request, "Logged in successfully!")
                return redirect('home')  # change this later for dashboard
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


# -----------------------------
# Logout View
# -----------------------------
def user_logout(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('login')
def home(request):
    return render(request, 'accounts/home.html')
