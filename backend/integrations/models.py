"""
Integration model — external service connections.

Future enhancements: OAuth flows, sync status, webhooks.
"""

from django.db import models


class IntegrationStatus(models.TextChoices):
    CONNECTED = "connected", "Connected"
    DISCONNECTED = "disconnected", "Disconnected"
    PENDING = "pending", "Pending"


class Integration(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=IntegrationStatus.choices,
        default=IntegrationStatus.DISCONNECTED,
    )
    # Future: credentials, last_synced_at, config JSON
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
