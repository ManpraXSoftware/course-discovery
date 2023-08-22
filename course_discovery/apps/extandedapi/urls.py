from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^get-program-topics/$', GetProgramTopics.as_view(), name='get_program_topics'),
    url(r'^custom-course-search/$', CustomSearch.as_view(), name='custom_course_search'),
    url(r'^getprogramtags/$', GetProgramTags.as_view(), name='getprogramtags'),
    url(r'^getprogramcourses/$',GetProgramCourses.as_view(),name='getprogramcourses'),
    url(r'^getprograms/$',GetAllPrograms.as_view(),name='getprograms'),
    url(r'^getprogram/$',GetProgram.as_view(),name='getprogram'),
    url(r'^gettag/$',GetTag.as_view(),name='gettag'),
    url(r'^getcoursereports/$',GetCourseReportsData.as_view(),name='getcoursereports'),
    url(r'^getreportsfilters/$',GetReportsFilterData.as_view(),name='getreportsfilters'),
]