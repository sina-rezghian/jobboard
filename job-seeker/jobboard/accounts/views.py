from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import EmployerRegistrationForm, JobSeekerRegistrationForm, LoginForm
from .models import EmployerProfile, JobSeekerProfile


def register_employer(request):
    if request.method == 'POST':
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            EmployerProfile.objects.create(
                user=user,
                company_name=form.cleaned_data['company_name'],
                company_description=form.cleaned_data['company_description'],
                phone=form.cleaned_data['phone'],
                website=form.cleaned_data['website']
            )
            return redirect('login')
    else:
        form = EmployerRegistrationForm()
    return render(request, 'accounts/register_employer.html', {'form': form})


def register_jobseeker(request):
    if request.method == 'POST':
        form = JobSeekerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            JobSeekerProfile.objects.create(
                user=user,
                full_name=form.cleaned_data['full_name'],
                education=form.cleaned_data['education'],
                skills=form.cleaned_data['skills'],
                phone=form.cleaned_data['phone'],
                resume=form.cleaned_data['resume']
            )
            return redirect('login')
    else:
        form = JobSeekerRegistrationForm()
    return render(request, 'accounts/register_jobseeker.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('admin:index')  # we’ll change this later to role-based dashboard
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')
