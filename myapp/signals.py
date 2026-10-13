# myapp/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models

from .models import InstallmentPayment


@receiver(post_save, sender=InstallmentPayment)
@receiver(post_delete, sender=InstallmentPayment)
def update_total_paid(sender, instance, **kwargs):
    payment = instance.payment

    total = payment.installments.aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    payment.total_paid = total
    payment.save(update_fields=['total_paid'])
