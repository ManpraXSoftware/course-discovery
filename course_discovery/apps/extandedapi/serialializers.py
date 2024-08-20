from rest_framework import serializers
from course_discovery.apps.course_metadata.models import Course, Program

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
        
class GetCourseProgramSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    
    def get_subjects(self, model):
        subjects_data = []
        subjects = model.program_subjects.all()
        for subject in subjects:
            subjects_data.append(subject.name)
        return subjects_data
    
    def get_topics(self, model):
        topics_data = []
        topics = model.program_topics.all()
        for topic in topics:
            topics_data.append(topic.name)
        return topics_data
    
    class Meta:
        model = Program
        fields = ("title","subjects", "topics")
        