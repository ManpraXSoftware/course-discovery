from course_discovery.apps.api.v1.views.course_runs import CourseRunViewSet, writable_request_wrapper
from course_discovery.apps.course_metadata.models import CourseRun, Course, CourseRunType, CourseType
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from course_discovery.apps.course_metadata.utils import ensure_draft_world
from rest_framework import status
from course_discovery.apps.api.mx.serializers import MxCourseRunWithProgramsSerializer
from course_discovery.apps.course_metadata.data_loaders.api import CoursesApiDataLoader
from course_discovery.apps.core.models import Partner
import logging
from course_discovery.apps.course_metadata.choices import CourseRunStatus
from course_discovery.apps.api.utils import reviewable_data_has_changed
from django.utils.translation import gettext as _


log = logging.getLogger(__name__)


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

    # pylint: disable=arguments-differ
    def update(self, request, **kwargs):
        # return super().update(request,**kwargs)
        # logging to help debug error around course url slugs incrementing
        log.info('The raw course run data coming from publisher is {}.'.format(
            request.data))  # lint-amnesty, pylint: disable=logging-format-interpolation

        # Update one, or more, fields for a course run.
        course_run = self.get_object()
        course_run = ensure_draft_world(course_run)  # always work on drafts
        partial = kwargs.pop('partial', False)
        # Sending draft=False triggers the review process for unpublished courses
        # Don't let draft parameter trickle down
        draft = request.data.pop('draft', True)
        prices = request.data.pop('prices', {})
        upgrade_deadline_override = request.data.pop('upgrade_deadline_override', None) \
            if self.request.user.is_staff else None
        if request.data.get('tags'):
            course_run.tags.clear()
            [course_run.tags.add(t) for t in request.data.get('tags')]
        serializer = self.get_serializer(
            course_run, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Handle staff update on course run in review with valid status transition
        if (request.user.is_staff and course_run.in_review and 'status' in request.data and
                request.data['status'] in CourseRunStatus.INTERNAL_STATUS_TRANSITIONS):
            return self.handle_internal_review(request, serializer)

        # Handle regular non-internal update
        # Status management is handled in the model
        request.data.pop('status', None)
        # Status management is handled in the model
        serializer.validated_data.pop('status', None)
        # Disallow patch or put if the course run is in review.
        if course_run.in_review:
            return Response(
                _('Course run is in review. Editing disabled.'),
                status=status.HTTP_403_FORBIDDEN
            )
        # Disallow internal review fields when course run is not in review
        for key in request.data.keys():
            if key in CourseRun.INTERNAL_REVIEW_FIELDS:
                return Response(
                    _('Invalid parameter'),
                    status=status.HTTP_400_BAD_REQUEST
                )

        changed_fields = reviewable_data_has_changed(
            course_run,
            serializer.validated_data.items(),
            CourseRun.STATUS_CHANGE_EXEMPT_FIELDS
        )
        response = self._update_course_run(course_run, draft, bool(changed_fields),
                                           serializer, request, prices, upgrade_deadline_override,)

        self.update_course_run_image_in_studio(course_run)

        return response
