from django.contrib import admin
from .models import AuditLog, FeedItem, IncidentReport, NationalAlert, PriceCeiling, StatusEvent


class StatusEventInline(admin.TabularInline):
    model = StatusEvent
    extra = 0


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ("tracking_code", "category", "urgency", "city", "status", "assigned_unit", "created_at")
    list_filter = ("status", "urgency", "category", "city")
    search_fields = ("tracking_code", "description", "location_hint")
    readonly_fields = ("tracking_code", "created_at")
    inlines = [StatusEventInline]


@admin.register(NationalAlert)
class NationalAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "regions", "is_published", "published_at", "expires_at")
    list_filter = ("level", "is_published")


@admin.register(PriceCeiling)
class PriceCeilingAdmin(admin.ModelAdmin):
    list_display = ("product", "unit", "max_price_fcfa", "previous_price_fcfa", "updated_at")


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "category", "source", "is_published", "published_at")
    list_filter = ("kind", "category", "is_published")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Lecture seule : on ne modifie ni ne supprime jamais le journal."""
    list_display = ("at", "user_name", "action", "detail")
    list_filter = ("action",)
    search_fields = ("user_name", "detail")

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
