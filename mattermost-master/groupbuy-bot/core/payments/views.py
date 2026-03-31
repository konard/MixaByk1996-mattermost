"""
Views for Payments API
"""
import hashlib
import hmac
import json
from decimal import Decimal
from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import Payment, Transaction
from .serializers import (
    PaymentSerializer, CreatePaymentSerializer,
    TransactionSerializer, WebhookPayloadSerializer
)
from users.models import User


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments.

    Endpoints:
    - GET /api/payments/ - list payments
    - POST /api/payments/ - create a payment
    - GET /api/payments/{id}/ - get payment details
    - GET /api/payments/{id}/status/ - get payment status
    - POST /api/payments/webhook/ - handle YooKassa webhook
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        payment_type = self.request.query_params.get('payment_type')
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)

        payment_status = self.request.query_params.get('status')
        if payment_status:
            queryset = queryset.filter(status=payment_status)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new payment (deposit)"""
        serializer = CreatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['user_id']
        amount = serializer.validated_data['amount']
        description = serializer.validated_data.get('description', f'Deposit {amount} RUB')

        # Create payment record
        payment = Payment.objects.create(
            user_id=user_id,
            payment_type=Payment.PaymentType.DEPOSIT,
            amount=amount,
            description=description,
            status=Payment.Status.PENDING
        )

        # In production, call YooKassa API here
        # For now, simulate a confirmation URL
        payment.confirmation_url = f"https://yookassa.ru/checkout/payments/v2/contract?orderId={payment.id}"
        payment.external_id = f"yookassa_{payment.id}_{int(datetime.now().timestamp())}"
        payment.save()

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get payment status"""
        payment = self.get_object()
        return Response({
            'id': payment.id,
            'status': payment.status,
            'status_display': payment.status_display,
            'amount': str(payment.amount),
            'paid_at': payment.paid_at,
            'created_at': payment.created_at
        })

    @action(detail=False, methods=['post'])
    def webhook(self, request):
        """Handle YooKassa webhook"""
        # In production, verify signature
        # signature = request.headers.get('X-YooKassa-Signature')

        try:
            event_type = request.data.get('event')
            payment_object = request.data.get('object', {})
            external_id = payment_object.get('id')

            if not external_id:
                return Response(
                    {'error': 'Missing payment ID'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment = Payment.objects.filter(external_id=external_id).first()
            if not payment:
                return Response(
                    {'error': 'Payment not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if event_type == 'payment.succeeded':
                self._process_successful_payment(payment, payment_object)
            elif event_type == 'payment.canceled':
                payment.status = Payment.Status.CANCELLED
                payment.save()
            elif event_type == 'refund.succeeded':
                self._process_refund(payment, payment_object)

            return Response({'status': 'ok'})

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def simulate_success(self, request, pk=None):
        """Simulate successful payment (for testing)"""
        payment = self.get_object()

        if payment.status != Payment.Status.PENDING:
            return Response(
                {'error': 'Payment is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )

        self._process_successful_payment(payment, {})

        return Response({
            'status': 'success',
            'payment': PaymentSerializer(payment).data
        })

    def _process_successful_payment(self, payment, payment_object):
        """Process a successful payment"""
        with db_transaction.atomic():
            payment.status = Payment.Status.SUCCEEDED
            payment.paid_at = timezone.now()
            payment.save()

            # Update user balance
            user = payment.user
            user.balance += payment.amount
            user.save()

            # Create transaction record
            Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TransactionType.DEPOSIT,
                amount=payment.amount,
                balance_after=user.balance,
                payment=payment,
                description=f'Deposit: {payment.description}'
            )

    def _process_refund(self, payment, refund_object):
        """Process a refund"""
        with db_transaction.atomic():
            refund_amount = Decimal(refund_object.get('amount', {}).get('value', 0))

            payment.status = Payment.Status.REFUNDED
            payment.save()

            # Update user balance
            user = payment.user
            user.balance -= refund_amount
            user.save()

            # Create transaction record
            Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TransactionType.WITHDRAWAL,
                amount=-refund_amount,
                balance_after=user.balance,
                payment=payment,
                description=f'Refund: {payment.description}'
            )


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing transactions.

    Endpoints:
    - GET /api/payments/transactions/ - list transactions
    - GET /api/payments/transactions/{id}/ - get transaction details
    - GET /api/payments/transactions/summary/ - get transaction summary
    """
    queryset = Transaction.objects.select_related('user', 'payment', 'procurement')
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary for a user"""
        user_id = request.query_params.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transactions = self.get_queryset().filter(user_id=user_id)

        # Calculate totals
        deposits = transactions.filter(
            transaction_type=Transaction.TransactionType.DEPOSIT
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        withdrawals = transactions.filter(
            transaction_type__in=[
                Transaction.TransactionType.WITHDRAWAL,
                Transaction.TransactionType.PROCUREMENT_JOIN
            ]
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        refunds = transactions.filter(
            transaction_type=Transaction.TransactionType.PROCUREMENT_REFUND
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        user = User.objects.filter(id=user_id).first()

        return Response({
            'user_id': int(user_id),
            'current_balance': str(user.balance) if user else '0',
            'total_deposited': str(abs(deposits)),
            'total_withdrawn': str(abs(withdrawals)),
            'total_refunded': str(abs(refunds)),
            'transaction_count': transactions.count()
        })


# Import models for aggregation
from django.db import models
