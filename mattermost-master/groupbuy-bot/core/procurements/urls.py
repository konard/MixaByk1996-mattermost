"""
URL configuration for Procurements API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProcurementViewSet, ParticipantViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'participants', ParticipantViewSet, basename='participant')
router.register(r'', ProcurementViewSet, basename='procurement')

urlpatterns = [
    path('', include(router.urls)),
]
