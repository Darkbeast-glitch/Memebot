from django.urls import path
from dashboard.views import token_list, dashboard_stats

urlpatterns = [
    path("tokens/", token_list, name="token-list"),
    path("stats/", dashboard_stats, name="dashboard-stats"),
]
