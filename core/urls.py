from django.urls import path
from . import views

urlpatterns = [
    path("reports/", views.ReportCreateView.as_view()),
    path("reports/<str:tracking_code>/", views.ReportTrackView.as_view()),
    path("alerts/", views.AlertListView.as_view()),
    path("alerts/<int:pk>/", views.AlertDetailView.as_view()),
    path("feed/", views.FeedListView.as_view()),
    path("prices/", views.PriceListView.as_view()),
]
