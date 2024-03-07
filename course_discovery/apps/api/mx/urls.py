""" API mx URLs. """
from rest_framework import routers
from django.urls import path


from course_discovery.apps.api.mx.views.course_runs import MxCourseRunViewSet
from course_discovery.apps.api.mx.views.sync_course import SyncCourse
app_name = 'mx'


urlpatterns = [path('sync_course/<course_id>/', SyncCourse.as_view(), name='sync_course'),
               ]

router = routers.SimpleRouter()
router.register(r'course_runs', MxCourseRunViewSet, basename='course_run')

urlpatterns += router.urls
