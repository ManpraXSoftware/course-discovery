from django.conf.urls import url
from django.urls import path
from .views import *

urlpatterns = [
    path('discovery-translation',GetDiscoveryTranslations.as_view(),name='disocvery-translation'),
    path('getkeydata',GetKeyData.as_view(),name='getkeydata'),
    path('update_multilingual_course',UpdateMultilingualCourse.as_view(),name='update_multilingual_course')

    
    # url(r'^get-program-topics/$', GetProgramTopics.as_view(), name='get_program_topics'),
]