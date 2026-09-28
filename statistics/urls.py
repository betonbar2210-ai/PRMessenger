from django.urls import path

from statistics.apps import StatisticsConfig
from statistics.views import StatisticsView

app_name = StatisticsConfig.name

urlpatterns = [
    path("", StatisticsView.as_view(), name="statistics"),
]
