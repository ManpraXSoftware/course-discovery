from django.urls import path
from .views import *

urlpatterns = [
    path('', update_scripts, name="update_scripts"),
    path('course-sync', discovery_views, name="course_sync"),
    path('update-index', update_indexCmd, name='update_indexCmd'),
    path('update-mx-index-contents', update_mx_index_contentsCmd, name='update_mx_index_contentsCmd')

    
]