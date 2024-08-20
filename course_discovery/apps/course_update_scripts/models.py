from django.db import models
from course_discovery.apps.course_metadata.utils import UploadToFieldNamePath
from django.core.validators import FileExtensionValidator



class ImageUpload (models.Model):

    get_full_image_url = models.ImageField(
        upload_to=UploadToFieldNamePath(populate_from='id', path='media/subject/new_image_url'),
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['png'])]
    )
    
    @property
    def image_url(self):
        if self.get_full_image_url:
            return self.get_full_image_url.url

        return None