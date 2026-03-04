from django.contrib import admin
from scoring.models import TokenScore


@admin.register(TokenScore)
class TokenScoreAdmin(admin.ModelAdmin):
    list_display = ["token", "score", "created_at"]
    list_filter = ["score"]
    search_fields = ["token__symbol"]
