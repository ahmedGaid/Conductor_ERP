"""Branch admin API — list/create/edit company branches.

Any authenticated user may read (branch pickers, filters); only System Admin may create or edit,
matching the org-preferences convention (org-wide settings, admin-gated writes).
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

from .models import Branch


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "code", "name", "is_active"]
        read_only_fields = ["id"]


class BranchListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasAnyRole.require(SYSTEM_ADMIN)()]
        return [IsAuthenticated()]

    def get(self, request: Request) -> Response:
        return _envelope(BranchSerializer(Branch.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = BranchSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        branch = Branch.objects.create(**s.validated_data)
        return _envelope(BranchSerializer(branch).data, status=201)


class BranchDetailView(APIView):
    permission_classes = [IsAuthenticated, HasAnyRole.require(SYSTEM_ADMIN)]

    def patch(self, request: Request, code: str) -> Response:
        branch = get_object_or_404(Branch, code=code)
        s = BranchSerializer(branch, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return _envelope(BranchSerializer(branch).data)


urlpatterns = [
    path("branches", BranchListCreateView.as_view(), name="branches"),
    path("branches/<str:code>", BranchDetailView.as_view(), name="branch-detail"),
]
