from django.core.management.base import BaseCommand
import logging
log = logging.getLogger()
from ...views import UpdateMultilingualCourse


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        
        
        response = UpdateMultilingualCourse().get()
        # import pdb;pdb.set_trace()
        if response.data['Translation file not available for language']:
            log.warning('Translation file is not available for languages {}'.format(response.data['Translation file not available for language']))
        
        if response.data['Error in courses']:
            log.warning('These courses are not available  {}'.format(response.data['course_not_available']))
        
        if response.data['Error in Programs']:
            log.warning('These Programs are not available  {}'.format(response.data['Error in Programs']))
        
        if response.data['Error in tags']:
            log.warning('These Tags are not available  {}'.format(allcourse.data['Error in tags']))
        

        if response.data['status']:
            self.stdout.write("response:- {}".format(response.data['message']))
        else:
            self.stdout.write("response:- There is problem please try again")