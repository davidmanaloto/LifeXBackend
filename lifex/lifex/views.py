from django.shortcuts import render

def landing_page(request):
    """Professional landing page"""
    return render(request, 'landing.html')

def login_view(request):
    """Login page"""
    return render(request, 'login.html')

def staff_dashboard(request):
    """Staff dashboard for Receptionist, Nurse, and Doctor"""
    return render(request, 'staff_dashboard.html')

def patient_portal(request):
    """Patient portal"""
    return render(request, 'patient_portal.html')

def admin_dashboard(request):
    """Admin dashboard"""
    return render(request, 'admin_dashboard.html')

def register_view(request):
    """Registration page"""
    return render(request, 'register.html')