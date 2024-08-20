from django.contrib import admin
from course_update_scripts.models import ImageUpload

class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_full_image_url',)

admin.site.register(ImageUpload, ImageUploadAdmin)
