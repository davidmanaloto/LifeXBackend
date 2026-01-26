from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)
from . import views

urlpatterns = [
    # Landing page as root
    path('', views.landing_page, name='home'),
    
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Web Interfaces
    path('login/', views.login_view, name='login'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('patient/', views.patient_portal, name='patient_portal'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # API endpoints
    path('api/auth/', include('users.urls')),
    path('api/blockchain/', include('blockchain.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)