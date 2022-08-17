from django.db import models
from course_discovery.apps.course_metadata.models import *
from parler.models import TranslatableModel, TranslatedFieldsModel
from parler.fields import TranslatedField
from django.utils.translation import gettext as _

CONTENT_TYPE = (
    ('program','Program'),
    ('course','Course'),
    ('tag','Tag')
)

class MultiLingualDiscovery(TranslatableModel):
    content_type = models.CharField(choices=CONTENT_TYPE,max_length=20,verbose_name="Content Type")
    program_title = models.ForeignKey(to=Program,on_delete=models.CASCADE,null=True,blank=True,related_name="multilingual_program",verbose_name="Program Title")
    course_title = models.ForeignKey(to=CourseRun,on_delete=models.CASCADE,null=True,blank=True,related_name="multilingual_course",verbose_name="Course Title")
    title = TranslatedField()
    short_description = TranslatedField()
    full_description = TranslatedField()


    class Meta:
        verbose_name = _("MultiLingualDiscovery")

    def clean(self):
        if self.content_type == 'program' and self.program_title is None:
            raise ValidationError('Program key is required for the program type of content.')
        elif self.content_type == 'course' and self.course_title is None:
            raise ValidationError('Course key is required for the program type of content.')

    def __str__(self):
        return self.title


class MultiLingualDiscoveryTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(MultiLingualDiscovery,on_delete=models.CASCADE, related_name='translations', null=True)
    title = models.CharField(max_length=255, blank=False, null=False, verbose_name="Title")
    short_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Short Description")
    full_description = models.TextField(blank=True, null=True, verbose_name="Full Description")


    class Meta:
        verbose_name = _("MultiLingualDiscovery translation")




