""" API mx URLs. """
from rest_framework import routers
from django.urls import path
from course_discovery.apps.api.mx.views.programs import ProgramViewSet, CreateProgramViewSet
from course_discovery.apps.api.mx.views.partners import PartnersViewSet
from course_discovery.apps.api.mx.views.programs import TagsList
from course_discovery.apps.api.mx.views.degrees import DegreeViewSet, VideoViewSet, CurriculumViewSet
from course_discovery.apps.api.mx.views.degrees import QuickfactViewSet

from course_discovery.apps.api.mx.views.course_runs import MxCourseRunViewSet
from course_discovery.apps.api.mx.views.sync_course import SyncCourse
app_name = 'mx'


urlpatterns = [path('sync_course/<course_id>/', SyncCourse.as_view(), name='sync_course'),
               ]

router = routers.SimpleRouter()
router.register(r'course_runs', MxCourseRunViewSet, basename='course_run')

router.register(r'program_data', CreateProgramViewSet, basename='create-program')
router.register(r'partners', PartnersViewSet, basename='partners')
router.register(r'tags', TagsList, basename='tags')
router.register(r'degree', DegreeViewSet, basename='degree')
router.register(r'videos', VideoViewSet, basename='videos')
router.register(r'curriculums', CurriculumViewSet, basename='curriculums')
router.register(r'quickfacts', QuickfactViewSet, basename='quickfacts')

urlpatterns += router.urls
