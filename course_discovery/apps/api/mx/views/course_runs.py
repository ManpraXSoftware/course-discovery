from course_discovery.apps.api.v1.views.course_runs import CourseRunViewSet, writable_request_wrapper
from course_discovery.apps.course_metadata.models import CourseRun, Course, CourseRunType, CourseType
from django.db import models
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from course_discovery.apps.course_metadata.utils import ensure_draft_world
from rest_framework import status
from course_discovery.apps.api.mx.serializers import MxCourseRunWithProgramsSerializer
from course_discovery.apps.course_metadata.data_loaders.api import CoursesApiDataLoader
from course_discovery.apps.core.models import Partner


class MxCourseRunViewSet(CourseRunViewSet):
    serializer_class = MxCourseRunWithProgramsSerializer

    def pull_from_studio(self, course_id):
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

    @writable_request_wrapper
    def create_run_helper(self, run_data: dict, request=None):
        # These are both required to be part of self because when we call self.get_serializer, it tries
        # to set these two variables as part of the serializer context. When the endpoint is hit directly,
        # self.request should exist, but when this function is called from the Course POST endpoint in courses.py
        # we have to manually set these values.
        if not hasattr(self, 'request'):
            self.request = request  # pylint: disable=attribute-defined-outside-init
        if not hasattr(self, 'format_kwarg'):
            self.format_kwarg = None  # pylint: disable=attribute-defined-outside-init

        # Set a pacing default when creating (studio requires this to be set, even though discovery does not)
        run_data.setdefault('pacing_type', 'instructor_paced')

        # Guard against externally setting the draft state
        run_data.pop('draft', None)

        prices = run_data.pop('prices', {})

        # Grab any existing course run for this course (we'll use it when talking to studio to form basis of rerun)
        course_key = run_data.get('course', None)  # required field
        if not course_key:
            raise ValidationError({'course': ['This field is required.']})

        # Before creating the serializer we need to ensure the course has draft rows as expected
        # The serializer will attempt to retrieve the draft version of the Course
        # course = Course.objects.filter_drafts().get(key=course_key)
        course, course_created = Course.objects.get_or_create(
            key=course_key, draft=True, partner_id=1, type=CourseType.objects.get(
                slug=CourseType.EMPTY))
        course = ensure_draft_world(course)
        old_course_run_key = run_data.pop('rerun', None)

        if not run_data.get('run_type'):
            run_data['run_type'] = CourseRunType.objects.get(
                slug=CourseRunType.EMPTY).uuid
        if not run_data.get('start'):
            run_data['start'] = "2030-01-01T00:00:00.000Z"

        serializer = self.get_serializer(data=run_data)
        serializer.is_valid(raise_exception=True)

        # Save run to database
        course_run = serializer.save(draft=True)

        course_run.update_or_create_seats(course_run.type, prices)

        # Set canonical course run if needed (done this way to match historical behavior - but shouldn't this be
        # updated *each* time we make a new run?)
        if not course.canonical_course_run:
            course.canonical_course_run = course_run
            course.save()
        elif not old_course_run_key:
            # On a rerun, only set the old course run key to the canonical key if a rerun hasn't been provided
            # This will prevent a breaking change if users of this endpoint don't choose to provide a key on rerun
            old_course_run_key = course.canonical_course_run.key

        if old_course_run_key:
            old_course_run = CourseRun.objects.filter_drafts().get(key=old_course_run_key)
            course_run.language = old_course_run.language
            course_run.min_effort = old_course_run.min_effort
            course_run.max_effort = old_course_run.max_effort
            course_run.weeks_to_complete = old_course_run.weeks_to_complete
            course_run.save()
            course_run.staff.set(old_course_run.staff.all())
            course_run.transcript_languages.set(
                old_course_run.transcript_languages.all())

        # And finally, push run to studio
        # self.push_to_studio(self.request, course_run,
        #                     create=True, old_course_run_key=old_course_run_key)
        # And finally, pull and update from studio
        self.pull_from_studio(course_run.key)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
