import logging
import requests
from django.core.management.base import BaseCommand
from course_discovery.apps.course_metadata.models import CourseRun, Program
from extandedapi.views import getProgramCourseDetail
from django.conf import settings
import os
import json
from django.core.cache import cache
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.utils import timezone
# from django.core.exceptions import MultipleObjectsReturned

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Triggers reindexing of courses or programs in MX Search App'
    # python manage.py mx_index_contents --index_type="course"
    def add_arguments(self, parser):
        parser.add_argument('--course_id', type=str, help='Specific course ID to reindex (optional)', default=None)
        parser.add_argument('--batch_size', type=int, help='Number of items per batch', default=50)
        parser.add_argument('--index_type', type=str, choices=['course', 'program', None], help='Type of data to index (course, program, or none for both)', default=None)
        parser.add_argument('--program_uuid', type=str, help='Specific program UUID to reindex (optional)', default=None)
    
    def update_json_status(self, status, file_dir):
        filepath = os.path.join(file_dir, 'command_status.json')
        curr_datetime_utc = datetime.now()
        delta = relativedelta(hours=5, minutes=30)
        ist_time = curr_datetime_utc + delta
        try:
            with open(filepath, "r+") as jsonFile:
                data = json.load(jsonFile)
                data['update_mx_index_contents_status'] = status
                data['update_mx_index_contents_timestamp'] = ist_time.strftime('%a, %d %b %Y %H:%M:%S') + ' IST'
                jsonFile.seek(0)
                json.dump(data, jsonFile)
                jsonFile.truncate()
        except Exception as e:
            logger.error(f"Failed to update JSON file at {filepath}: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Failed to update JSON file: {str(e)}"))

    def reindex_courses(self, course_id, batch_size, file_dir, LMS_URL, source_id):
        today = timezone.now()
        if course_id:
            course_runs = CourseRun.objects.filter(key=course_id, start__lt=today, start__isnull=False)
            if not course_runs.exists():
                logger.error(f"No CourseRun found with ID: {course_id}")
                self.stdout.write(self.style.ERROR(f"No CourseRun found with ID: {course_id}"))
                self.update_json_status(False, file_dir)
                cache.set('update_mx_index_contents_status', False)
                return False
        else:
            # course_runs = CourseRun.objects.filter(start__lt=today, start__isnull=False)
            course_runs = (
                    CourseRun.objects.filter(
                        start__lt=today,
                        start__isnull=False,
                        course__programs__isnull=False
                    )
                    .distinct()
                )
        items = [str(course_run.key) for course_run in course_runs]
        endpoint = 'mx_reindex_courses_batch'
        payload_key = "course_ids"
        all_success = True

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            payload = {payload_key: batch}
            try:
                logger.info(f"Triggering reindex for batch of {len(batch)} courses")
                response = requests.post(
                    f'{LMS_URL}/explore-courses/api/v1/{endpoint}/',
                    json=payload,
                    timeout=120
                )
                if response.status_code == 202:
                    logger.info(f"Successfully triggered reindexing for course {len(batch)} batch from {source_id}")
                    self.stdout.write(self.style.SUCCESS(f"Successfully triggered reindexing for course {len(batch)} batch "))
                else:
                    logger.error(f"Failed to trigger reindexing for course batch: Status {response.status_code}, Response {response.text}")
                    self.stdout.write(self.style.ERROR(f"Failed to trigger reindexing for course batch: Status {response.status_code}"))
                    all_success = False
            except requests.RequestException as e:
                logger.error(f"Failed to call reindex API for course batch: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Failed to call reindex API for course batch: {str(e)}"))
                all_success = False
        return all_success

    def cleanup_stale_courses(self):
        MX_SEARCH_BASE_URL = getattr(settings, 'MX_SEARCH_BASE_URL', "")
        try:
            stale_keys = list(
                CourseRun.objects.filter(course__programs__isnull=True)
                .values_list('course__key', flat=True)
                .distinct()
            )
            if not stale_keys:
                logger.info("No stale courses found to clean up.")
                return
            logger.info(f"Found {len(stale_keys)} stale course_keys to delete from index: {stale_keys}")
            response = requests.post(
                f'{MX_SEARCH_BASE_URL}/api/delete_courses_batch/',
                json={"course_keys": stale_keys},
                timeout=60
            )
            if response.status_code == 200:
                deleted = response.json().get("deleted", 0)
                logger.info(f"Cleanup deleted {deleted} stale documents from index.")
                self.stdout.write(self.style.SUCCESS(f"Cleanup: deleted {deleted} stale ES documents for {len(stale_keys)} course_keys"))
            else:
                logger.error(f"Cleanup failed: Status {response.status_code}, Response {response.text}")
                self.stdout.write(self.style.ERROR(f"Cleanup failed: Status {response.status_code}"))
        except Exception as e:
            logger.error(f"Error in cleanup_stale_courses: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Cleanup error: {str(e)}"))

    def handle(self, *args, **options):
        course_id = options['course_id']
        batch_size = options['batch_size']
        index_type = options['index_type']
        program_uuid = options['program_uuid']
        LMS_URL = getattr(settings, 'LMS_URL', "")
        source_id = 'course_discovery_command'

        file_dir_curr = os.path.dirname(__file__)
        file_dir = '/'.join(file_dir_curr.split('/')[:4])
        self.update_json_status(True, file_dir)

        all_success = True
        types_to_index = ['course', 'program'] if not index_type else [index_type]

        for idx_type in types_to_index:
            if idx_type == 'course':
                success = self.reindex_courses(course_id, batch_size, file_dir, LMS_URL, source_id)
                all_success = all_success and success
            # elif idx_type == 'program':
            #     success = self.reindex_programs(program_uuid, 10, file_dir, LMS_URL, source_id)
            #     all_success = all_success and success

        if all_success:
            self.update_json_status(False, file_dir)
            cache.set('update_mx_index_contents_status', False)
            self.stdout.write(self.style.SUCCESS(f"Indexing Run Successfully for {', '.join(types_to_index)}"))
        else:
            self.update_json_status(False, file_dir)
            cache.set('update_mx_index_contents_status', False)
            self.stdout.write(self.style.ERROR(f"Indexing Run Failed for one or more types: {', '.join(types_to_index)}"))

        self.cleanup_stale_courses()