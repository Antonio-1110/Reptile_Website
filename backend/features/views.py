from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .switches import all_switches


class FeatureSwitches(APIView):
    """Which parts of the site are switched on, e.g. {"auctions": false}, so the frontend can hide the rest."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(all_switches())
