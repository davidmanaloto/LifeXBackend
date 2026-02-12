import json
from django.utils.deprecation import MiddlewareMixin
from blockchain.models import AuditLog

class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log sensitive operations (POST, PUT, DELETE).
    """
    def process_response(self, request, response):
        if request.user.is_authenticated and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Avoid logging login/logout specifically here if they are handled in views
            # but capture all other data modifications
            
            # Filter matches for sensitive endpoints
            path = request.path
            if '/api/auth/' in path:
                return response
            
            # Basic action mapping
            action_map = {
                'POST': 'CREATE',
                'PUT': 'UPDATE',
                'PATCH': 'PARTIAL_UPDATE',
                'DELETE': 'DELETE'
            }
            
            action = action_map.get(request.method, 'UNKNOWN')
            
            # Simple resource extraction
            parts = [p for p in path.split('/') if p]
            resource_type = parts[1] if len(parts) > 1 else 'general'
            resource_id = parts[2] if len(parts) > 2 else ''
            
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=f"{action}_{resource_type.upper()}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=f"Path: {path} | Status: {response.status_code}",
                    ip_address=self.get_client_ip(request)
                )
            except Exception:
                # Silently fail audit logging to not interrupt user flow
                pass
                
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
