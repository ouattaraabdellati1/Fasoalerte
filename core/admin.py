from django.contrib import admin
from .models import IncidentReport, NationalAlert, PriceCeiling, StatusEvent


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
