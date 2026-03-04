from django.contrib import admin
from behaviour.models import TradeEvent


@admin.register(TradeEvent)
class TradeEventAdmin(admin.ModelAdmin):
    list_display = ["token", "wallet", "side", "amount", "timestamp"]
    list_filter = ["side"]
    search_fields = ["wallet", "token__symbol"]
