from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^get-program-topics/$', GetProgramTopics.as_view(), name='get_program_topics'),
    url(r'^custom-course-search/$', CustomSearch.as_view(), name='custom_course_search'),
    url(r'^getprogramtags/$', GetProgramTags.as_view(), name='getprogramtags'),
    url(r'^getprogramcourses/$',GetProgramCourses.as_view(),name='getprogramcourses'),
    url(r'^getprogramcoursesdetail/$',GetProgramCoursesDetail.as_view(),name='getprogramcoursesdetail'),
    url(r'^getprograms/$',GetAllPrograms.as_view(),name='getprograms'),
    url(r'^getprogram/$',GetProgram.as_view(),name='getprogram'),
    url(r'^getprogramandtags/$',GetProgramAndtags.as_view(),name='getprogramandtags'),
    url(r'^getprogramusingcourseid/$',GetProgramUsingCourseId.as_view(),name='getprogramusingcourseid'),
    url(r'^getcourseprograms/$',GetCoursePrograms.as_view(),name='getcourseprograms'),
    url(r'^gettag/$',GetTag.as_view(),name='gettag'),
    url(r'^getcoursereports/$',GetCourseReportsData.as_view(),name='getcoursereports'),
    url(r'^getreportsfilters/$',GetReportsFilterData.as_view(),name='getreportsfilters'),
    url(r'^getprogramdetails/$', GetProgramDetails.as_view(), name="getprogramdetails"),
    url(r'^getprogramtags2/$', GetProgramTags2.as_view(), name='getprogramtags2'),
    url(r'^get-program-topics2/$', GetProgramTopics2.as_view(), name='get_program_topics2'),
    url(r'^getcourseprogramdetail/$', GetCouseProgramDetail.as_view(), name="getcourseprogramdetail"),
]