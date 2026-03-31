"""
Views for Procurements API
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Category, Procurement, Participant
from .serializers import (
    CategorySerializer, ProcurementListSerializer, ProcurementDetailSerializer,
    ProcurementCreateSerializer, ParticipantSerializer, JoinProcurementSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing categories"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        parent = self.request.query_params.get('parent')
        if parent:
            queryset = queryset.filter(parent_id=parent)
        elif parent == '':
            queryset = queryset.filter(parent__isnull=True)
        return queryset


class ProcurementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing procurements.

    Endpoints:
    - GET /api/procurements/ - list all procurements (with filters)
    - POST /api/procurements/ - create new procurement
    - GET /api/procurements/{id}/ - get procurement details
    - PUT /api/procurements/{id}/ - update procurement
    - DELETE /api/procurements/{id}/ - delete procurement
    - GET /api/procurements/{id}/participants/ - list participants
    - POST /api/procurements/{id}/join/ - join a procurement
    - POST /api/procurements/{id}/leave/ - leave a procurement
    - GET /api/procurements/user/{user_id}/ - get user's procurements
    - POST /api/procurements/{id}/check_access/ - check user access
    """
    queryset = Procurement.objects.select_related('category', 'organizer')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'city']
    ordering_fields = ['created_at', 'deadline', 'target_amount', 'current_amount']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProcurementListSerializer
        if self.action == 'create':
            return ProcurementCreateSerializer
        return ProcurementDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        # Filter by city
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Filter by organizer
        organizer = self.request.query_params.get('organizer')
        if organizer:
            queryset = queryset.filter(organizer_id=organizer)

        # Filter active only
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(status=Procurement.Status.ACTIVE)

        return queryset

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get list of participants for a procurement"""
        procurement = self.get_object()
        participants = procurement.participants.filter(is_active=True)
        serializer = ParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a procurement"""
        procurement = self.get_object()

        if not procurement.can_join:
            return Response(
                {'error': 'Cannot join this procurement'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = JoinProcurementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['user_id']

        # Check if already participating
        if procurement.participants.filter(user_id=user_id, is_active=True).exists():
            return Response(
                {'error': 'Already participating in this procurement'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create participant
        participant = Participant.objects.create(
            procurement=procurement,
            user_id=user_id,
            quantity=serializer.validated_data['quantity'],
            amount=serializer.validated_data['amount'],
            notes=serializer.validated_data.get('notes', ''),
            status=Participant.Status.PENDING
        )

        return Response(
            ParticipantSerializer(participant).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a procurement"""
        procurement = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        participant = procurement.participants.filter(user_id=user_id, is_active=True).first()
        if not participant:
            return Response(
                {'error': 'Not participating in this procurement'},
                status=status.HTTP_400_BAD_REQUEST
            )

        participant.is_active = False
        participant.status = Participant.Status.CANCELLED
        participant.save()

        return Response({'message': 'Successfully left the procurement'})

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def user_procurements(self, request, user_id=None):
        """Get procurements for a specific user"""
        # Get organized procurements
        organized = self.get_queryset().filter(organizer_id=user_id)

        # Get participated procurements
        participating_ids = Participant.objects.filter(
            user_id=user_id, is_active=True
        ).values_list('procurement_id', flat=True)
        participating = self.get_queryset().filter(id__in=participating_ids)

        organized_data = ProcurementListSerializer(organized, many=True).data
        participating_data = ProcurementListSerializer(participating, many=True).data

        # Add user's amount for participating procurements
        for proc_data in participating_data:
            participant = Participant.objects.filter(
                procurement_id=proc_data['id'],
                user_id=user_id,
                is_active=True
            ).first()
            if participant:
                proc_data['my_amount'] = str(participant.amount)
                proc_data['my_quantity'] = str(participant.quantity)

        return Response({
            'organized': organized_data,
            'participating': participating_data
        })

    @action(detail=True, methods=['post'])
    def check_access(self, request, pk=None):
        """Check if user has access to procurement chat"""
        procurement = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # User has access if they are organizer or participant
        has_access = (
            procurement.organizer_id == int(user_id) or
            procurement.participants.filter(user_id=user_id, is_active=True).exists()
        )

        if has_access:
            return Response({'access': True})
        return Response(
            {'access': False, 'error': 'No access to this procurement'},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update procurement status"""
        procurement = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Procurement.Status.choices):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        procurement.status = new_status
        procurement.save(update_fields=['status', 'updated_at'])

        return Response({
            'status': procurement.status,
            'status_display': procurement.status_display
        })


class ParticipantViewSet(viewsets.ModelViewSet):
    """ViewSet for managing participants"""
    queryset = Participant.objects.select_related('user', 'procurement')
    serializer_class = ParticipantSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by procurement
        procurement = self.request.query_params.get('procurement')
        if procurement:
            queryset = queryset.filter(procurement_id=procurement)

        # Filter by user
        user = self.request.query_params.get('user')
        if user:
            queryset = queryset.filter(user_id=user)

        return queryset

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update participant status"""
        participant = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Participant.Status.choices):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        participant.status = new_status
        participant.save(update_fields=['status', 'updated_at'])

        return Response(ParticipantSerializer(participant).data)
