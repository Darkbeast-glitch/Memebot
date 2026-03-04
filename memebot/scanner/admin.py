from django.contrib import admin
from scanner.models import Token, PairSnapshot


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ["symbol", "name", "mint", "source", "is_rejected", "alert_sent", "created_at"]
    list_filter = ["source", "is_rejected", "alert_sent"]
    search_fields = ["symbol", "name", "mint"]


@admin.register(PairSnapshot)
class PairSnapshotAdmin(admin.ModelAdmin):
    list_display = ["token", "pair_address", "dex_id", "liquidity_usd", "volume_24h", "traders_1h", "captured_at"]
    list_filter = ["dex_id"]
    search_fields = ["token__symbol", "pair_address"]
