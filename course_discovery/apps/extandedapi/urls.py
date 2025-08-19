from django.urls import path
from .views import *

app_name = "extandedapi"

urlpatterns = [
    path('get-program-topics/', GetProgramTopics.as_view(), name='get_program_topics'),
    path('custom-course-search/', CustomSearch.as_view(), name='custom_course_search'),
    path('getprogramtags/', GetProgramTags.as_view(), name='getprogramtags'),
    path('getprogramcourses/',GetProgramCourses.as_view(),name='getprogramcourses'),
    path('getprogramcoursesdetail/',GetProgramCoursesDetail.as_view(),name='getprogramcoursesdetail'),
    path('getprograms/',GetAllPrograms.as_view(),name='getprograms'),
    path('getprogram/',GetProgram.as_view(),name='getprogram'),
    path('getprogramandtags/',GetProgramAndtags.as_view(),name='getprogramandtags'),
    path('getprogramusingcourseid/',GetProgramUsingCourseId.as_view(),name='getprogramusingcourseid'),
    path('getcourseprograms/',GetCoursePrograms.as_view(),name='getcourseprograms'),
    path('gettag/',GetTag.as_view(),name='gettag'),
    path('getcoursereports/',GetCourseReportsData.as_view(),name='getcoursereports'),
    path('getreportsfilters/',GetReportsFilterData.as_view(),name='getreportsfilters'),
    path('getprogramdetails/', GetProgramDetails.as_view(), name="getprogramdetails"),
    path('getprogramtags2/', GetProgramTags2.as_view(), name='getprogramtags2'),
    path('get-program-topics2/', GetProgramTopics2.as_view(), name='get_program_topics2'),
    path('getcourseprogramdetail/', GetCouseProgramDetail.as_view(), name="getcourseprogramdetail"),
    path('getdetaillangbased/',Getdetaillangbased.as_view(),name='getdetaillangbased'),

    path('getcoursedetail/',GetCourseDetail.as_view(),name='get_course_detail'),
    path('getprogramcoursedetail/',GetProgramCourseDetail.as_view(),name='get_program_detail'),

    path('mx-custom-course-search/', MXCustomSearch.as_view(), name='mx_custom_course_search'),


]
