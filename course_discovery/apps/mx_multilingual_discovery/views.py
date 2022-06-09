from cmath import log
from logging import exception
from traceback import print_tb
from django.db import reset_queries
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery, MultiLingualDiscoveryTranslation
from rest_framework.response import Response
from rest_framework import status
from course_discovery.apps.course_metadata.models import *
from taggit.models import Tag
import json
import os
import logging
logger = logging.getLogger()

class GetDiscoveryTranslations(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        content_type = request.GET.get('type')
        result = MultiLingualDiscovery.objects.filter(content_type=content_type)
        final_response = [
            {
                "content_type":res.content_type,
                "course_key": res.course_key.course.key if res.course_key else None,
                "program_key":res.program_key.uuid if res.program_key else None,
                "title":res.title if res.title else None,
                "short_description":res.short_description if res.short_description else None,
                "full_description":res.full_description if res.full_description else None
            } for res in result]
        return Response(final_response,status=status.HTTP_200_OK)

class GetKeyData(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        key = request.GET.get('key')
        key_type = request.GET.get('type')
        if key_type == 'course':
            try:
                courserun = CourseRun.objects.get(pk=key)
                response = {
                    "title":courserun.course.title,
                    "short_description":courserun.course.short_description,
                    "full_description":courserun.course.full_description
                }
                return Response(response,status=status.HTTP_200_OK)
            except Course.DoesNotExist:
                response = {
                    "status":False,
                    "message":"Course not exists."
                }
        elif key_type == 'program':
            try:
                program = Program.objects.get(id=key)
                response = {
                    "title":program.title,
                    "short_description":program.subtitle,
                    "full_description":program.overview
                }
                return Response(response,status=status.HTTP_200_OK)
            except Program.DoesNotExist:
                response = {
                    "status":False,
                    "message":"Program not exists."
                }
        else:
            response = {
                "status":False,
                "message":"Requested data not available."
            }
        return Response(response,status=status.HTTP_400_BAD_REQUEST)

class UpdateMultilingualCourse(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self):
        all_courses = CourseRun.objects.all()
        all_programs = Program.objects.all()
        all_tags = Tag.objects.values('name')

        # import pdb;pdb.set_trace()
        error_in_course = []
        error_in_program = []
        error_in_tags = []

        translation_file = []

        all_languages = ['hi','kn','ml','te','ta','bn']

        for current_language in all_languages:
            try:
                file = open('new_trans_'+current_language+'.json')
                json_data = json.load(file)
            except:
                translation_file.append(current_language)
                continue

            for course in all_courses:
                
                try:
                    course_name = course.course.title
                    logger.info("updating multilingual for course {} and language {}".format(course_name, current_language))
                    course_name_new = MultiLingualDiscovery.objects.language('en').filter(content_type='course').active_translations(title=course_name)
                                    
                    if not course_name_new:
                        course_name_en = MultiLingualDiscovery.objects.language('en').create(content_type='course',course_title=course,title=course_name)
                        
                    if json_data:
                        for dicts in json_data['dictionary']:
                            if course_name in dicts['translation']:
                                course_name_new = MultiLingualDiscovery.objects.language('en').filter(content_type='course').active_translations(title=course_name)
                                if course_name_new:
                                    course_name_new = course_name_new[0]
                                    course_name_new.set_current_language(current_language)
                                    course_name_new.content_type='course'
                                    course_name_new.course_title=course
                                    course_name_new.title=dicts['translation'][course_name]['value']
                                    course_name_new.save()
                                    break
                except Exception as e:
                    print(e)
                    error_in_course.append(course_name)
                    continue
            
            for program in all_programs:
            
                try:
                    program_name = program.title
                    logger.info("updating multilingual for Program {} and language {}".format(program_name,current_language))
                    program_name_new = MultiLingualDiscovery.objects.language('en').filter(content_type='program').active_translations(title=program_name)
                                    
                    if not program_name_new:
                        program_name_en = MultiLingualDiscovery.objects.language('en').create(content_type='program',program_title=program,title=program_name)
                        
                    if json_data:
                        for dicts in json_data['dictionary']:
                            if program_name in dicts['translation']:
                                program_name_new = MultiLingualDiscovery.objects.language('en').filter(content_type='program').active_translations(title=program_name)
                                if program_name_new:
                                    program_name_new = program_name_new[0]
                                    program_name_new.set_current_language(current_language)
                                    program_name_new.content_type='program'
                                    program_name_new.program_title=program
                                    program_name_new.title=dicts['translation'][program_name]['value']
                                    program_name_new.save()
                                    break
                except Exception as e:
                    print(e)
                    error_in_program.append(program_name)
                    continue
            
            for tag in all_tags:
            
                try:
                    tag_name = tag['name']
                    logger.info("updating multilingual for Tag {} and language {}".format(tag_name,current_language))

                    if tag_name:
                        tag_name_new = MultiLingualDiscovery.objects.language('en').filter(content_type='tag').active_translations(title=tag_name)

                        if not tag_name_new:            
                            tag_name_en = MultiLingualDiscovery.objects.language('en').create(content_type='tag',title=tag_name)
                        
                        if json_data:
                            for dicts in json_data['dictionary']:
                                if tag_name in dicts['translation']:
                                    tag_name_new = MultiLingualDiscovery.objects.language('en').filter(content_type='tag').active_translations(title=tag_name)
                                    if tag_name_new:
                                        tag_name_new = tag_name_new[0]
                                        tag_name_new.set_current_language(current_language)
                                        tag_name_new.content_type='tag'
                                        tag_name_new.title=dicts['translation'][tag_name]['value']
                                        tag_name_new.save()
                                        break
                except Exception as e:
                    print(e)
                    error_in_tags.append(tag_name)
                    continue

       
        response = {
                "status":True,
                "message":"All data inserted successfully",
                "Error in tags":error_in_tags,
                "Error in courses": error_in_course,
                "Translation file not available for language":translation_file,
                "Error in Programs":error_in_program
            }
        return Response(response,status=status.HTTP_200_OK)

