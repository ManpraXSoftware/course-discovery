

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from course_discovery.apps.api import serializers
from course_discovery.apps.core.models import Partner

class PartnersViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.PartnerSerializer
    queryset = Partner.objects.all()
