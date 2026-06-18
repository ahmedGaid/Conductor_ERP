"""CRM API routes."""
from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    # Campaigns
    path("campaigns", views.CampaignListCreateView.as_view(), name="campaign-list"),
    path("campaigns/<uuid:campaign_id>", views.CampaignDetailView.as_view(), name="campaign-detail"),
    path("campaigns/<uuid:campaign_id>/status", views.CampaignStatusView.as_view(), name="campaign-status"),
    # Leads
    path("leads", views.LeadListCreateView.as_view(), name="lead-list"),
    path("leads/<uuid:lead_id>/status", views.LeadStatusView.as_view(), name="lead-status"),
    path("leads/<uuid:lead_id>/convert", views.LeadConvertView.as_view(), name="lead-convert"),
    # Opportunities
    path("opportunities", views.OppListCreateView.as_view(), name="opp-list"),
    path("opportunities/<uuid:opp_id>", views.OppDetailView.as_view(), name="opp-detail"),
    path("opportunities/<uuid:opp_id>/stage", views.OppStageView.as_view(), name="opp-stage"),
    path("opportunities/<uuid:opp_id>/win", views.OppWinView.as_view(), name="opp-win"),
    path("opportunities/<uuid:opp_id>/lose", views.OppLoseView.as_view(), name="opp-lose"),
    # Activities
    path("activities", views.ActivityListCreateView.as_view(), name="activity-list"),
    path("activities/<uuid:activity_id>/complete", views.ActivityCompleteView.as_view(), name="activity-complete"),
    # Tickets
    path("tickets", views.TicketListCreateView.as_view(), name="ticket-list"),
    path("tickets/<uuid:ticket_id>", views.TicketDetailView.as_view(), name="ticket-detail"),
    path("tickets/<uuid:ticket_id>/start", views.TicketStartView.as_view(), name="ticket-start"),
    path("tickets/<uuid:ticket_id>/resolve", views.TicketResolveView.as_view(), name="ticket-resolve"),
    path("tickets/<uuid:ticket_id>/close", views.TicketCloseView.as_view(), name="ticket-close"),
    path("tickets/<uuid:ticket_id>/escalate", views.TicketEscalateView.as_view(), name="ticket-escalate"),
    path("tickets-run-escalations", views.TicketRunEscalationsView.as_view(), name="ticket-run-escalations"),
]
