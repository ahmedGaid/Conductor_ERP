"""Custom field definitions API — list active defs (any authenticated user, so a form can render
from truth), admin-only create/update/deactivate.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.urls import path
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import SYSTEM_ADMIN

from . import custom_fields as service
from .custom_fields import CustomFieldDef

_IsAdmin = HasAnyRole.require(SYSTEM_ADMIN)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class CustomFieldDefSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomFieldDef
        fields = [
            "id", "entity_key", "key", "label_ar", "label_en", "type",
            "required", "choices", "is_active", "position",
        ]
        read_only_fields = ["id", "is_active"]


class CustomFieldDefListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), _IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request: Request) -> Response:
        qs = service.CustomFieldDef.objects.filter(is_active=True)
        entity = request.query_params.get("entity")
        if entity:
            qs = qs.filter(entity_key=entity)
        return _envelope(CustomFieldDefSerializer(qs.order_by("position", "key"), many=True).data)

    def post(self, request: Request) -> Response:
        s = CustomFieldDefSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = service.create_custom_field_def(**s.validated_data)
        return _envelope(CustomFieldDefSerializer(d).data, status=201)


class CustomFieldDefDetailView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def patch(self, request: Request, pk: int) -> Response:
        d = get_object_or_404(CustomFieldDef, pk=pk)
        s = CustomFieldDefSerializer(d, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        updated = service.update_custom_field_def(d.pk, **s.validated_data)
        return _envelope(CustomFieldDefSerializer(updated).data)


class CustomFieldDefDeactivateView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def post(self, request: Request, pk: int) -> Response:
        d = service.deactivate_custom_field_def(pk)
        return _envelope(CustomFieldDefSerializer(d).data)


urlpatterns = [
    path("custom-fields", CustomFieldDefListCreateView.as_view(), name="custom-fields"),
    path("custom-fields/<int:pk>", CustomFieldDefDetailView.as_view(), name="custom-field-detail"),
    path(
        "custom-fields/<int:pk>/deactivate",
        CustomFieldDefDeactivateView.as_view(),
        name="custom-field-deactivate",
    ),
]
