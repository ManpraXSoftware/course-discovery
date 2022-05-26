from django.db import reset_queries
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery
from rest_framework.response import Response
from rest_framework import status
from course_discovery.apps.course_metadata.models import *

class GetDiscoveryTranslations(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        content_type = request.GET.get('type')
        result = MultiLingualDiscovery.objects.filter(content_type=content_type)
        final_response = [
            {
                "content_type":res.content_type,
                "course_key": res.course_key.course.key if res.course_key else None,
                "program_key":res.program_key.uuid if res.program_key else None,
                "title":res.title if res.title else None,
                "short_description":res.short_description if res.short_description else None,
                "full_description":res.full_description if res.full_description else None
            } for res in result]
        return Response(final_response,status=status.HTTP_200_OK)

class GetKeyData(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        key = request.GET.get('key')
        key_type = request.GET.get('type')
        if key_type == 'course':
            try:
                courserun = CourseRun.objects.get(pk=key)
                response = {
                    "title":courserun.course.title,
                    "short_description":courserun.course.short_description,
                    "full_description":courserun.course.full_description
                }
                return Response(response,status=status.HTTP_200_OK)
            except Course.DoesNotExist:
                response = {
                    "status":False,
                    "message":"Course not exists."
                }
        elif key_type == 'program':
            try:
                program = Program.objects.get(id=key)
                response = {
                    "title":program.title,
                    "short_description":program.subtitle,
                    "full_description":program.overview
                }
                return Response(response,status=status.HTTP_200_OK)
            except Program.DoesNotExist:
                response = {
                    "status":False,
                    "message":"Program not exists."
                }
        else:
            response = {
                "status":False,
                "message":"Requested data not available."
            }
        return Response(response,status=status.HTTP_400_BAD_REQUEST)