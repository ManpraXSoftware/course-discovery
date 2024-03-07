from course_discovery.apps.api.serializers import CourseRunWithProgramsSerializer
from rest_framework import serializers
from course_discovery.apps.course_metadata.models import CourseRun, Course, CourseRunType
from course_discovery.apps.api.fields import HtmlField
from taggit.serializers import TaggitSerializer, TagListSerializerField


class MxCourseRunWithProgramsSerializer(CourseRunWithProgramsSerializer):
    end = serializers.DateTimeField(required=False)
    start = serializers.DateTimeField(required=False)
    run_type = serializers.SlugRelatedField(required=False, slug_field='uuid', source='type',
                                            queryset=CourseRunType.objects.all())
    full_description = HtmlField(
        required=False, allow_blank=True, allow_null=True)
    short_description = HtmlField(
        required=False, allow_blank=True, allow_null=True)
    outcome = HtmlField(required=False, allow_blank=True, allow_null=True)
    tags = TagListSerializerField(allow_null=True)

    class Meta(CourseRunWithProgramsSerializer.Meta):
        model = CourseRun
        fields = CourseRunWithProgramsSerializer.Meta.fields + ('tags',)
