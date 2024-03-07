from course_discovery.apps.course_metadata.data_loaders.api import CoursesApiDataLoader
from course_discovery.apps.core.models import Partner
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


class SyncCourse(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id, *args, **kwargs):
        partner = Partner.objects.get(id=1)
        url = f"{partner.courses_api_url}courses/{course_id}"
        max_workers = 1
        loader = CoursesApiDataLoader(partner, url, max_workers)
        try:
            res = loader._make_request(1)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            loader.process_single_course_run(res)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"course": course_id}, status=status.HTTP_200_OK)
