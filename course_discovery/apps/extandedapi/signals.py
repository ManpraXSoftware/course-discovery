# import requests
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from course_discovery.apps.course_metadata.models import Program, CourseRun, Subject
# from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery, MultiLingualDiscoveryTranslation
# from django.db import transaction
# from django.conf import settings
# import logging

# logger = logging.getLogger(__name__)

# # Replace with your actual API endpoint URL


# LMS_URL = getattr(settings, 'LMS_URL', "")


# def trigger_reindex_for_courses(courses, source_id):
#     """
#     Helper function to trigger reindexing for all CourseRun keys associated with a list of courses.
#     """
#     for course in courses:
#         course_runs = CourseRun.objects.filter(course=course)
#         for course_run in course_runs:
#             payload = {"course_id": str(course_run.key)}
#             try:
#                 response = requests.post(LMS_URL+'/explore-courses/api/v1/mx_reindex_course_by_id/', json=payload, timeout=60)
                
#                 if response.status_code == 202:
#                     logger.info(f"Successfully triggered reindexing for CourseRun {course_run.key} from {source_id}")
#                 else:
#                     logger.error(
#                         f"Failed to trigger reindexing for CourseRun {course_run.key} from {source_id}: "
#                         f"Status {response.status_code}, Response {response.text}"
#                     )
#             except requests.RequestException as e:
#                 logger.error(
#                     f"Failed to call reindex API for CourseRun {course_run.key} from {source_id}: {str(e)}"
#                 )


# @receiver(post_save, sender=Program)
# def reindex_courses_on_program_save(sender, instance, **kwargs):
#     """
#     Trigger reindexing by calling the API for all CourseRun keys associated with a program's courses when the program is saved.
#     """
#     logger.info(f"Program post_save signal triggered for program {instance.uuid}, created={kwargs.get('created')}")
#     def process_program():
#         try:
#             trigger_reindex_for_courses(instance.courses.all(), f"program {instance.uuid}")
#         except Exception as e:
#             logger.error(f"Failed to process reindexing for program {instance.uuid}: {str(e)}")
#     transaction.on_commit(process_program)



# @receiver(post_save, sender=Subject)
# def reindex_courses_on_subject_save(sender, instance, **kwargs):
#     """
#     Trigger reindexing by calling the API for all CourseRun keys associated with programs linked to the subject when the subject is saved.
#     """
#     logger.info(f"Subject post_save signal triggered for subject {instance.uuid}, created={kwargs.get('created')}")
#     def process_subject():
#         try:
#             programs = Program.objects.filter(program_subjects=instance)
#             logger.info(f"Found {programs.count()} programs for subject {instance.uuid}")
#             for program in programs:
#                 trigger_reindex_for_courses(program.courses.all(), f"subject {instance.uuid} via program {program.uuid}")
#         except Exception as e:
#             logger.error(f"Failed to process reindexing for subject {instance.uuid}: {str(e)}")
#     transaction.on_commit(process_subject)

# @receiver(post_save, sender=MultiLingualDiscovery)
# def reindex_courses_on_multilingual_save(sender, instance, **kwargs):
#     """
#     Trigger reindexing by calling the API based on MultiLingualDiscovery content_type:
#     - 'program': For all CourseRun keys in the linked program's courses.
#     - 'course': For the linked CourseRun key.
#     - 'tag': For all CourseRun keys in programs where the title matches a program_topics tag.
#     """
#     logger.info(f"MultiLingualDiscovery post_save signal triggered for id {instance.id}, content_type={instance.content_type}, created={kwargs.get('created')}")
#     def process_multilingual():
#         try:
#             if instance.content_type == 'program' and instance.program_title:
#                 logger.info(f"Processing program content_type for program {instance.program_title.uuid}")
#                 trigger_reindex_for_courses(instance.program_title.courses.all(), f"multilingual program {instance.program_title.uuid}")
#             elif instance.content_type == 'course' and instance.course_title:
#                 logger.info(f"Processing course content_type for CourseRun {instance.course_title.key}")
#                 payload = {"course_id": str(instance.course_title.key)}
#                 try:
#                     response = requests.post(LMS_URL+'/explore-courses/api/v1/mx_reindex_course_by_id/', json=payload, timeout=60)
                    
#                     if response.status_code == 202:
#                         logger.info(f"Successfully triggered reindexing for CourseRun {instance.course_title.key} from multilingual course {instance.id}")
#                     else:
#                         logger.error(
#                             f"Fainstanceiled to trigger reindexing for CourseRun {instance.course_title.key} from multilingual course {instance.id}: "
#                             f"Status {response.status_code}, Response {response.text}"
#                         )
#                 except requests.RequestException as e:
#                     logger.error(
#                         f"Failed to call reindex API for CourseRun {instance.course_title.key} from multilingual course {instance.id}: {str(e)}"
#                     )
#             elif instance.content_type == 'tag' and instance.title:
#                 logger.info(f"Processing tag content_type with title {instance.title}")
#                 multilingual = MultiLingualDiscovery.objects.get(id=instance.id)

#                 programs = Program.objects.filter(program_topics__name=multilingual.title)
#                 logger.info(f"Found {programs.count()} programs for tag {multilingual.title}")
#                 for program in programs:
#                     trigger_reindex_for_courses(program.courses.all(), f"multilingual tag {multilingual.title} via program {program.uuid}")
#         except Exception as e:
#             logger.error(f"Failed to process reindexing for multilingual discovery {instance.id}: {str(e)}")
#     transaction.on_commit(process_multilingual)


import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from course_discovery.apps.course_metadata.models import Program, CourseRun, Subject
from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery
from django.db import transaction
from django.conf import settings
import logging
from extandedapi.views import getProgramCourseDetail

logger = logging.getLogger(__name__)

LMS_URL = getattr(settings, 'LMS_URL', "")

def trigger_reindex_for_courses(courses, source_id):
    """
    Helper function to trigger reindexing for all CourseRun keys associated with a list of courses.
    """
    for course in courses:
        course_runs = CourseRun.objects.filter(course=course)
        for course_run in course_runs:
            payload = {"course_id": str(course_run.key)}
            try:
                response = requests.post(LMS_URL+'/explore-courses/api/v1/mx_reindex_course_by_id/', json=payload, timeout=60)
                if response.status_code == 202:
                    logger.info(f"Successfully triggered reindexing for CourseRun {course_run.key} from {source_id}")
                else:
                    logger.error(
                        f"Failed to trigger reindexing for CourseRun {course_run.key} from {source_id}: "
                        f"Status {response.status_code}, Response {response.text}"
                    )
            except requests.RequestException as e:
                logger.error(
                    f"Failed to call reindex API for CourseRun {course_run.key} from {source_id}: {str(e)}"
                )

def trigger_reindex_for_program(uuids, source_id):
    """
    Trigger reindexing for a list of program UUIDs.
    """
    try:
        program_details = getProgramCourseDetail(uuids)
        if not program_details:
            logger.warning(f"No program details found for UUIDs {uuids} from {source_id}")
            return
        payload = {"programs": program_details}  
        response = requests.post(
            f'{LMS_URL}/explore-courses/api/v1/mx_reindex_programs_batch/',
            json=payload,
            timeout=120
        )
        if response.status_code == 202:
            logger.info(f"Successfully triggered reindexing for program batch from {source_id}")
        else:
            logger.error(f"Failed to trigger reindexing for program batch from {source_id}: Status {response.status_code}, Response {response.text}")
    except Exception as e:
        logger.error(f"Failed to trigger reindexing for programs {uuids} from {source_id}: {str(e)}")

@receiver(post_save, sender=Program)
def reindex_courses_on_program_save(sender, instance, **kwargs):
    """
    Trigger reindexing for all CourseRun keys and the program itself when a program is saved.
    """
    logger.info(f"Program post_save signal triggered for program {instance.uuid}, created={kwargs.get('created')}")
    def process_program():
        try:
            # Reindex courses
            trigger_reindex_for_courses(instance.courses.all(), f"program {instance.uuid}")
            # Reindex the program itself
            trigger_reindex_for_program([str(instance.uuid)], f"program {instance.uuid}")
        except Exception as e:
            logger.error(f"Failed to process reindexing for program {instance.uuid}: {str(e)}")
    transaction.on_commit(process_program)

@receiver(post_save, sender=Subject)
def reindex_courses_on_subject_save(sender, instance, **kwargs):
    """
    Trigger reindexing for all CourseRun keys and programs linked to the subject when the subject is saved.
    """
    logger.info(f"Subject post_save signal triggered for subject {instance.uuid}, created={kwargs.get('created')}")
    def process_subject():
        try:
            programs = Program.objects.filter(program_subjects=instance)
            logger.info(f"Found {programs.count()} programs for subject {instance.uuid}")
            program_uuids = [str(program.uuid) for program in programs]
            for program in programs:
                trigger_reindex_for_courses(program.courses.all(), f"subject {instance.uuid} via program {program.uuid}")
            if program_uuids:
                trigger_reindex_for_program(program_uuids, f"subject {instance.uuid}")
        except Exception as e:
            logger.error(f"Failed to process reindexing for subject {instance.uuid}: {str(e)}")
    transaction.on_commit(process_subject)

@receiver(post_save, sender=MultiLingualDiscovery)
def reindex_courses_on_multilingual_save(sender, instance, **kwargs):
    """
    Trigger reindexing based on MultiLingualDiscovery content_type:
    - 'program': For all CourseRun keys in the linked program and the program itself.
    - 'course': For the linked CourseRun key.
    - 'tag': For all CourseRun keys and programs where the title matches a program_topics tag.
    """
    logger.info(f"MultiLingualDiscovery post_save signal triggered for id {instance.id}, content_type={instance.content_type}, created={kwargs.get('created')}")
    def process_multilingual():
        try:
            if instance.content_type == 'program' and instance.program_title:
                logger.info(f"Processing program content_type for program {instance.program_title.uuid}")
                trigger_reindex_for_courses(instance.program_title.courses.all(), f"multilingual program {instance.program_title.uuid}")
                trigger_reindex_for_program([str(instance.program_title.uuid)], f"multilingual program {instance.program_title.uuid}")
            elif instance.content_type == 'course' and instance.course_title:
                logger.info(f"Processing course content_type for CourseRun {instance.course_title.key}")
                payload = {"course_id": str(instance.course_title.key)}
                try:
                    response = requests.post(LMS_URL+'/explore-courses/api/v1/mx_reindex_course_by_id/', json=payload, timeout=60)
                    if response.status_code == 202:
                        logger.info(f"Successfully triggered reindexing for CourseRun {instance.course_title.key} from multilingual course {instance.id}")
                    else:
                        logger.error(
                            f"Failed to trigger reindexing for CourseRun {instance.course_title.key} from multilingual course {instance.id}: "
                            f"Status {response.status_code}, Response {response.text}"
                        )
                    # multilingual = MultiLingualDiscovery.objects.get(id=instance.id)
                    programs = Program.objects.filter(courses__id=instance.course_title.id)
                    logger.info(f"Found {programs.count()} programs for courses {instance.course_title}")
                    program_uuids = [str(program.uuid) for program in programs]
                    if program_uuids:
                        trigger_reindex_for_program(program_uuids, f"multilingual tag {instance.course_title}")
                        logger.info(f"Successfully triggered reindexing for Program {program_uuids} from multilingual course {instance.id}")
                        
                except requests.RequestException as e:
                    logger.error(
                        f"Failed to call reindex API for CourseRun {instance.course_title.key} from multilingual course {instance.id}: {str(e)}"
                    )
            elif instance.content_type == 'tag' and instance.title:
                logger.info(f"Processing tag content_type with title {instance.title}")
                multilingual = MultiLingualDiscovery.objects.get(id=instance.id)
                programs = Program.objects.filter(program_topics__name=multilingual.title)
                logger.info(f"Found {programs.count()} programs for tag {multilingual.title}")
                program_uuids = [str(program.uuid) for program in programs]
                for program in programs:
                    trigger_reindex_for_courses(program.courses.all(), f"multilingual tag {multilingual.title} via program {program.uuid}")
                if program_uuids:
                    trigger_reindex_for_program(program_uuids, f"multilingual tag {multilingual.title}")
        except Exception as e:
            logger.error(f"Failed to process reindexing for multilingual discovery {instance.id}: {str(e)}")
    transaction.on_commit(process_multilingual)