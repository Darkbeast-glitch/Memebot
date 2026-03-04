from django.urls import path
from dashboard.views import token_list

urlpatterns = [
    path("tokens/", token_list, name="token-list"),
]
