from rest_framework import serializers
from course_discovery.apps.course_metadata.models import Course

class GetProgramCourseSerializer(serializers.ModelSerializer):
    course_id = serializers.SerializerMethodField()

    def get_course_id(self, obj):
        if obj.canonical_course_run:
            return obj.canonical_course_run.key
        elif obj.card_image_url:
            return 'course-v1'+obj.card_image_url.split("type")[0].split("asset-v1")[1][0:-1]
        else:
            return ''

    class Meta:
        model = Course
        fields = ('canonical_course_run', 'course_id')