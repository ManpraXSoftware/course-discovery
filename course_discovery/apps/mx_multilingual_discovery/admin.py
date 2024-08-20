from django.contrib import admin
from .models import *
from parler.admin import TranslatableAdmin
from course_discovery.apps.course_metadata.models import *
from django import forms

class CourseChoiceField(forms.ModelChoiceField):
    # this function will return the list for the course_key FK type 
    # field to get the course key for the API hit.
     def label_from_instance(self, obj):
         
         return "{} ({})".format(obj.course.title, obj.course.canonical_course_run)

class MultilingualDiscoveryAdmin(TranslatableAdmin):
    # search_fields = ('course_title',)
    # raw_id_fields = ('course_title',)
    # autocomplete_fields = ['course_title']

    class Media:  
        # js file for the admin interface customize.  
        # path (course-discovery/course_discovery/static/js/admin/multilingual_admin.js)
        js = ('js/admin/multilingual_admin.js',)
        
    fields = ('content_type','program_title','course_title','title','short_description','full_description',)
    list_display = ['id','title','content_type','short_description','full_description']
    list_filter = ['content_type']
    autocomplete_fields = ['course_title']
    

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        kwargs['required'] = False
        if db_field.name == 'course_title':
        
            return CourseChoiceField(queryset=CourseRun.objects.all(), required=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(MultiLingualDiscovery, MultilingualDiscoveryAdmin)
