from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from .serializers import (
    UserLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    StaffProvisioningSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdmin
from .utils import send_staff_invitation_email
from .models import StaffInvitation

User = get_user_model()

class UserAdminView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin can view, update or delete any user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'pk'


class StaffProvisioningView(generics.CreateAPIView):
    """
    Provision a new staff member (Admin access)
    """
    queryset = User.objects.all()
    serializer_class = StaffProvisioningSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Invitation and Email (Access user.invitation which was created in serializer)
        invitation = user.invitation
        email_sent = send_staff_invitation_email(invitation, request)
        
        return Response({
            'message': f'Staff account for {user.get_full_name()} provisioned successfully',
            'user': UserSerializer(user).data,
            'invitation_token': str(invitation.token),
            'email_status': 'Sent' if email_sent else 'Failed to send'
        }, status=status.HTTP_201_CREATED)


class StaffActivationView(APIView):
    """
    Handle staff account activation/claiming
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            invite = StaffInvitation.objects.get(token=token, is_claimed=False)
            if invite.is_expired:
                return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'email': invite.user.email,
                'name': invite.user.get_full_name(),
                'role': invite.user.role
            })
        except StaffInvitation.DoesNotExist:
            return Response({'error': 'Invalid invitation token'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, token):
        try:
            invite = StaffInvitation.objects.get(token=token, is_claimed=False)
            if invite.is_expired:
                return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            password = request.data.get('password')
            if not password:
                return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                validate_password(password, invite.user)
            except Exception as e:
                return Response({'error': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

            # Activate user
            user = invite.user
            user.set_password(password)
            user.is_active = True
            user.save()
            
            # Claim invite
            invite.is_claimed = True
            invite.save()
            
            return Response({'message': 'Account activated successfully. You can now log in.'})
            
        except StaffInvitation.DoesNotExist:
            return Response({'error': 'Invalid invitation token'}, status=status.HTTP_404_NOT_FOUND)






class UserLoginView(APIView):
    """
    Login user and return JWT tokens
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone_number = serializer.validated_data.get('phone_number')
        password = serializer.validated_data['password'].strip()
        
        user = None
        
        if email:
            email = email.lower().strip()
            # Try email auth
            user = authenticate(email=email, password=password)
            if user is None:
                user = authenticate(username=email, password=password)
        elif phone_number:
            # Try finding user by phone number first
            try:
                # We need to find the user instance to know their email/username for the authenticate method
                # because standard Django auth backend typically expects username/email
                user_obj = User.objects.get(phone_number=phone_number)
                
                # Check password manually or use authenticate if we pass the email that matches
                # Using authenticate is safer as it handles hashing, signals etc.
                user = authenticate(email=user_obj.email, password=password)
                if user is None:
                     user = authenticate(username=user_obj.email, password=password)
            except User.DoesNotExist:
                pass
        
        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    """
    Logout user by blacklisting the refresh token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Invalid token or token already blacklisted'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer


class ChangePasswordView(APIView):
    """
    Change user password
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Set new password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )


class UserListView(generics.ListAPIView):
    """
    List all users (Admin and Staff only)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Admins can see all users
        if user.role == 'ADMIN':
            return User.objects.all()
        
        # Medical Staff (Receptionist, Nurse, Doctor) can see Patients
        if user.role in ['RECEPTIONIST', 'NURSE', 'DOCTOR']:
            return User.objects.filter(role='PATIENT')
        
        # Patients can only see themselves
        return User.objects.filter(id=user.id)