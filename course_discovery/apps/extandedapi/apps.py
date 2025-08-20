from django.apps import AppConfig


class CourseScriptConfig(AppConfig):
    name = 'course_discovery.apps.extandedapi'
    verbose_name = 'Extanded API'

    def ready(self):
        # from extandedapi import signals
        pass