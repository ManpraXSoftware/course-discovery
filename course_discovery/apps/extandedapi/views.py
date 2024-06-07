import imp
from unittest import result
from rest_framework.response import Response
from django.conf import settings
from elasticsearch import Elasticsearch
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from course_discovery.apps.course_metadata.models import Program, Course, CourseRun, SubjectTranslation, Organization, Subject
from course_discovery.apps.api.v1.views.search import CourseSearchViewSet, AggregateSearchViewSet
from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery,MultiLingualDiscoveryTranslation
from rest_framework import status
from collections import OrderedDict
from itertools import chain
import logging as log
from django.db.models import Q
import json
import pymongo
from .serialializers import GetProgramCourseSerializer

# pylint: disable=attribute-defined-outside-init
class GetProgramTopics(APIView):
    """ GET Program Based Topics View."""
    permission_classes = (IsAuthenticated,)
    
    def get(self, request):
        subject_name_param = request.GET.get('subject_name')
        sub = SubjectTranslation.objects.filter(name=subject_name_param)

        try:
            sub_id = sub[0].master.id
            sub_en = Subject.objects.language('en').get(id=sub_id)
            sub_name = sub_en.name
            
        except Exception as e:
            sub_name = subject_name_param
        
        # import pdb;pdb.set_trace()
        body = {
            "query": {"bool": {
                "must": [
                        { "match": {
                            "content_type": "program"
                            }
                        },
                        {"match": {
                            "program_subjects": sub_name
                            }
                        }
                        ]
                    }
                },
            "facets" : {
                "tags" : { "terms" : {"field" : "program_topics_exact"} }
                }
            }
        alias = settings.HAYSTACK_CONNECTIONS['default']['INDEX_NAME']
        
        # index = '{alias}_20160621_000000'.format(alias=alias)

        host = settings.HAYSTACK_CONNECTIONS['default']['URL']
        
        connection = Elasticsearch(host)
        index_value = connection.indices.get_alias(name=alias)
        es_response = connection.search(index=[i for i in index_value.keys()][0], body=body)

        

        try:
            accept_language = request.headers['Accept-Language']
            if not accept_language or accept_language=='en':
                return Response(es_response['facets']['tags'])
        except KeyError:
            return Response(es_response['facets']['tags'])

        
        
        tag = MultiLingualDiscovery.objects.language('en').filter(Q(content_type='Tag')).active_translations(title__in=[i['term'] for i in es_response['facets']['tags']['terms']])

        converted_tag = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Tag')).active_translations(title__in=[i.title for i in tag])


        # data = tag.__dict__
        # import pdb;pdb.set_trace()
        data = {}
        for j in range(len(converted_tag)):
            if tag[j].title != converted_tag[j].title:
                data[tag[j].title] = converted_tag[j].title
            else:
                data[tag[j].title] = ''
        
        for i in range(len(es_response['facets']['tags']['terms'])):

            if es_response['facets']['tags']['terms'][i]['term'] in data:
                 es_response['facets']['tags']['terms'][i]['converted_term'] = data[es_response['facets']['tags']['terms'][i]['term']]
            else:
                es_response['facets']['tags']['terms'][i]['converted_term'] = ''


        return Response(es_response['facets']['tags'])

class CustomSearch(APIView):
    """
    Custom search based on the courses.

    1. Query parameter (q).

    2. Internal course_search api called to get the data.

    3. After getting result appending program_details to the dict and returning in the following format.

        final_response = {
                "count" : total count of the dict,
                "next" : next url,
                "previous" : previous url,
                "results" : dict type result
            }
    """
    permission_classes = (IsAuthenticated,)
    def get_program_details(self,course_key):
        programs_dict = OrderedDict()
        try:
            course = Course.objects.get(key=course_key)
            programs = Program.objects.filter(courses=course)
            if programs:
                programs_dict['programs'] = [program.title for program in programs]
                programs_dict['program_id'] = [program.uuid for program in programs]
                # for program in programs:
                programs_dict['tags'] = [OrderedDict({
                    "program_name":program.title,
                    "program_id":program.uuid,
                    "tags":[tags.name for tags in program.program_topics.all()] })for program in programs]
              
            return programs_dict
        except Course.DoesNotExist:
            programs_dict = None
            return programs_dict

    def get(self,request):
        programs_details = None
        content = CourseSearchViewSet.as_view({'get': 'list'})(request._request)
        for x in content.data['results']:
            programs_details = self.get_program_details(x['key'])
            x['program_details'] = programs_details
        final_response = OrderedDict()
        final_response["count"] = len(content.data['results'])
        final_response["next"] = content.data['next'] if content.data['next'] else None
        final_response["previous"] = content.data['previous'] if content.data['previous'] else None
        final_response["results"] = content.data['results']
        return Response(final_response,status=status.HTTP_200_OK)      

# Extract all programs and detials based on prorgrma uuid and extract the resume program data based on course block id
class GetProgramTags(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        prog_uuids = request.GET.get('uuids')
        p = prog_uuids.split(',')
        log.info('here the prog_uuids are {}'.format(len(p)))
        resume_data = request.GET.get('resume_data')
        accept_language = request.GET.get('accept_language')
        log.info("Resume data received: {}".format(resume_data))
        log.info("Program UUIDS: {}".format(prog_uuids))
        tags = list()
        if prog_uuids:
            for prog_id in prog_uuids.split(','):
                try:
                    program = Program.objects.get(uuid=prog_id)
                    log.info("Enrolled Program: {}".format(program.title))
                    converted_program = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Program')).active_translations(title=program.title)
                    response = {
                        "program_uuid":prog_id,
                        "program_title":program.title,
                        "converted_program_title":converted_program[0].title if converted_program.count() else program.title,
                        "tags":[],
                        "program_course_details":[{
                            "course_id" : course_det.canonical_course_run.key,
                            "course_name" : course_det.title,
                        } for course_det in program.courses.all()]
                    }
                    all_tag_names = {tag.name for tag in program.program_topics.all()}
                    for tag in all_tag_names:
                        tags_data = {}
                        converted_tag = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Tag')).active_translations(title=tag)
                        tags_data["tag_title"]= tag
                        tags_data["converted_tag_title"]= converted_tag[0].title if converted_tag.count() else tag
                        response['tags'].append(tags_data)
                    tags.append(response)
                except Program.DoesNotExist:
                    print("Program not found with uuid: %s",prog_id)
                except Exception as e:
                   print("Error occured due to: %s",e)
            if resume_data:
                resume_str = resume_data.replace(' ','+')
                resume_data = resume_str.split(',')
                log.info("Resume data received {}".format(resume_data))
                temp_course_id = resume_data[0].replace('course-v1:','')
                course_key = '+'.join(temp_course_id.split('+')[0:len(temp_course_id.split('+'))-1])
                course = Course.objects.get(key=course_key)
                programs = Program.objects.filter(courses=course)
                log.info("Course related programs: {}".format(programs))
                resume_course_programs = filter(lambda x:str(x.uuid) in prog_uuids.split(','), programs)
                log.info("Resume course programs: {}".format(resume_course_programs))
                resume_prog_uuid = [str(prog.uuid) for prog in resume_course_programs]
                for prog in tags:
                    if prog['program_uuid'] in resume_prog_uuid:
                        converted_course_name = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Course')).active_translations(title=course.title)
                        prog['resume_program'] = {
                            "course_id": resume_data[0],
                            "course_name": course.title,
                            "converted_course_name":converted_course_name[0].title if converted_course_name.count() else course.title,
                            "block_id": resume_data[-1],
                        }
        # import pdb;pdb.set_trace()
        return Response(tags,status=status.HTTP_200_OK)

class GetAllPrograms(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        programs = Program.objects.all()
        result = dict()
        for program in programs:
            result[str(program.uuid)] = list(chain(*program.courses.all().values_list('key')))
        return Response(result,status=status.HTTP_200_OK)

class GetProgramCoursesDetail(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        try:
            log.info("_____________________ request parameters are {}______________".format(request.GET))
            if 'program_uuid' in request.GET:
                log.info("_____________________program_uuid of program whose courses are being fetched {}______________".format(request.GET['program_uuid']))
                program = Program.objects.filter(uuid=request.GET['program_uuid']).first()
                log.info("___________ fetched program is {}".format(program))
            
            else:
                log.info("_____________________program_uuid is not provided in the url______________")
                return Response({'message':'program_uuid not given in request url'},status=400)
            
            # import pdb;pdb.set_trace()

            if program is None:
                log.info("_____________________program_uuid is invalid______________")
                return Response({'message':'program_uuid is invalid'},status=400)
            
            result = dict()
            result["id"] = request.GET['program_uuid']
            result["data"]= list()
            from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery
            from course_discovery.apps.course_metadata.models import CourseRun
            language = request.GET['language'] if 'language' in request.GET else 'en'
            for course in program.courses.all():
                data = dict()
                if course.canonical_course_run:
                    log.info("_________ course {} having canonical_course_run it's key is {}".format(course,course.canonical_course_run.key))
                    data['key'] = course.canonical_course_run.key
                    data['title'] = course.title
                    # converted_title = MultiLingualDiscovery.objects.filter(content_type='course',course_title=CourseRun.objects.filter(key=course.canonical_course_run.key).first()).language(language).first()
                    # converted_title = MultiLingualDiscovery.objects.filter(content_type='course',course_title=course.canonical_course_run).language(language).first()
                    converted_title = MultiLingualDiscovery.objects.filter(content_type='course', course_title__key=course.canonical_course_run.key).language(language).first()
                    data['converted_title'] = converted_title.title if converted_title else ''
                    result["data"].append(data)
                elif course.card_image_url:
                    courseKey = str('course')+course.card_image_url.split('asset')[1].split('type')[0][0:-1]
                    log.info("_________ course {} having card_image_url it's key is {}".format(course,courseKey))
                    data['key'] = courseKey
                    data['title'] = course.title
                    # converted_title = MultiLingualDiscovery.objects.filter(content_type='course',course_title=CourseRun.objects.filter(key=courseKey).first()).language(language).first()
                    converted_title = MultiLingualDiscovery.objects.filter(content_type='course', course_title__key=courseKey).language(language).first()
                    data['converted_title'] = converted_title.title if converted_title else ''
                    result["data"].append(data)
                    
                else:
                    log.info("_________ course {} neither having card_image_url nor canonical_course_run".format(course))
                    continue
            
            return Response(result,status=status.HTTP_200_OK)
        except Exception as e:
            log.info("error in getting course of program is {}".format(e))
            return Response({'error':'error ocurred while getting courses{}'.format(e)},status=500)


        

class GetProgramCourses(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        
        try:
            log.info("_____________________ request parameters are {}______________".format(request.GET))
            if 'program_uuid' in request.GET and not 'course_id' in request.GET:
                log.info("_____________________program_uuid of program whose courses are being fetched {}______________".format(request.GET['program_uuid']))
                program = Program.objects.filter(uuid=request.GET['program_uuid']).first()
                log.info("___________ fetched program is {}".format(program))
            elif 'course_id' in request.GET:
                log.info("_____________________course_id of course whose fellow courses are being fetched {}______________".format(request.GET['course_id']))
                course_id = request.GET['course_id']
                key = course_id.replace(' ','+').split(':')[1].split('+')
                # program = Program.objects.filter(courses__canonical_course_run__key__in=[course_id.replace(' ', '+')]).first()
                program = Program.objects.filter(courses__key__in=[str(key[0])+str('+')+str(key[1])]).first()
                log.info("___________ fetched programs for course {} are {}".format(course_id,program))
            result = list()
            for course in program.courses.all():
                # import pdb;pdb.set_trace()
                # course.course_runs.core_filters['course'].key
                if course.canonical_course_run:
                    log.info("_________ course {} having canonical_course_run it's key is {}".format(course,course.canonical_course_run.key))
                    result.append(course.canonical_course_run.key)
                elif course.card_image_url:
                    courseKey = str('course')+course.card_image_url.split('asset')[1].split('type')[0][0:-1]
                    log.info("_________ course {} having card_image_url it's key is {}".format(course,courseKey))
                    result.append(courseKey)
                else:
                    log.info("_________ course {} neither having card_image_url nor canonical_course_run".format(course))
                    continue
            
            return Response(result,status=status.HTTP_200_OK)

        except Exception as e:
            log.info("error in getting course of program is {}".format(e))
            return Response({'error':'error ocurred while getting courses{}'.format(e)},status=status.HTTP_500_Internal_Server_Error)
class GetProgram(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        program_uuid = request.GET.get('program_uuid')
        program = Program.objects.filter(uuid=program_uuid)
        program_title = program[0].title if len(program) else 0
        result = list()
        result.append(program_title)
        return Response(result,status=status.HTTP_200_OK)

class GetProgramAndtags(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        program_uuid = request.GET.get('program_uuid')
        program = Program.objects.filter(uuid=program_uuid).first()
        result = dict()
        if program:
            result['program_title'] = program.title
            result['topics'] = [topic.name for topic in program.program_topics.all()]
        # import pdb;pdb.set_trace()
        return Response(result,status=status.HTTP_200_OK)

class GetProgramUsingCourseId(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        if 'course_id' in request.GET:
            course_id = request.GET['course_id']
            key = course_id.replace(' ','+').split(':')[1].split('+')
            # program = Program.objects.filter(courses__canonical_course_run__key=course_id.replace(' ','+')).first()
            program = Program.objects.filter(courses__key=str(key[0])+str('+')+str(key[1])).first()
            result = dict()
            if program:
                
                topics = []
                
                for topic in program.program_topics.all():
                    topics.append(topic.name)
                
                result['topics'] = topics
                result['program_title'] = program.title
                # result['course_title'] = program.courses.filter(canonical_course_run__key=course_id.replace(' ','+')).first().title
                result['course_title'] = program.courses.filter(key=str(key[0])+str('+')+str(key[1])).first().title
                
            
            return Response(result,status=status.HTTP_200_OK)

        else:
            Response(result,status=HTTP_500_Internal_Server_Error)

class GetCoursePrograms(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        if 'course_id' in request.GET:
            course_id = request.GET['course_id']
            # programs = Program.objects.filter(courses__canonical_course_run__key=course_id.replace(' ','+')).values('uuid')
            key = course_id.replace(' ','+').split(':')[1].split('+')
            programs = Program.objects.filter(courses__key=str(key[0])+str('+')+str(key[1])).values('uuid')
            # import pdb;pdb.set_trace()
            result = list()
            if programs:
                result = [str(uuid['uuid']) for uuid in programs]
                
            return Response(result,status=status.HTTP_200_OK)

        else:
            Response(result,status=HTTP_500_Internal_Server_Error)


class GetTag(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        language = request.GET.get('language')
        tagname = request.GET.get('topicname')
        result = list()
        try:
            tag_id = MultiLingualDiscoveryTranslation.objects.filter(title=tagname).last().master.id
            converted_tag = MultiLingualDiscovery.objects.language(language).filter(Q(content_type='Tag', id=tag_id))
        except:
            converted_tag = MultiLingualDiscovery.objects.language(language).filter(Q(content_type='Tag')).active_translations(title=tagname)
        if converted_tag and converted_tag[0].title:
            result.append(converted_tag[0].title)
        result.append(tagname)
        
        return Response(result,status=status.HTTP_200_OK)

class GetCourseReportsData(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        courses = CourseRun.objects.all()
        result = list()
        for course in courses:
            courses_data = dict()
            tags = list()
            subjects = list()
            orgs = list()
            courses_data['course_id'] = course.key
            courses_data['course_name'] = course.title_override
            courses_data['start_date'] = course.start
            courses_data['end_date'] = course.end
            programs = Program.objects.filter(courses=course.course)
            courses_data['programs'] = ','.join([prog.title for prog in programs])
            for program in programs:
                program_tag = program.program_topics.all()
                program_subject = program.program_subjects.all()
                program_org = program.authoring_organizations.all()
                tags.extend([tag.name for tag in program_tag])
                subjects.extend([sub.name for sub in program_subject])
                orgs.extend([org.key for org in program_org])
            courses_data['tags'] = ','.join(tags)
            courses_data['subjects'] = ','.join(subjects)
            courses_data['organizations'] = ','.join(orgs)
            result.append(courses_data)
        return Response(result,status=status.HTTP_200_OK)

class GetReportsFilterData(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        result = dict()

        programs_obj = Program.objects.all()
        programs = {prog.title:prog.title.upper() for prog in programs_obj}

        orgs_obj = Organization.objects.filter(name__isnull=False)
        orgs = {x.name:x.name.upper() for x in orgs_obj}

        subjects_obj = SubjectTranslation.objects.filter(language_code='en')
        subjects = {sub.name:sub.name.upper() for sub in subjects_obj}

        courses = CourseRun.objects.all()
        courses = {course.title_override:course.title_override.upper() for course in courses}

        result['programs']=programs
        result['orgs']=orgs
        result['subjects']=subjects
        result['courses']=courses

        return Response(result,status=status.HTTP_200_OK)
    

class GetProgramDetails(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        program_uuid = request.GET.get("program_uuid")
        program = Program.objects.get(uuid=program_uuid)
        program_courses = program.courses.all()
        return Response(GetProgramCourseSerializer(program_courses, many=True).data,status=status.HTTP_200_OK)


class GetProgramTags2(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self,request):
        prog_uuids = request.GET.get('uuids')
        p = prog_uuids.split(',')
        log.info('here the prog_uuids are {}'.format(len(p)))
        resume_data = request.GET.get('resume_data')
        accept_language = request.GET.get('accept_language')
        log.info("Resume data received: {}".format(resume_data))
        log.info("Program UUIDS: {}".format(prog_uuids))
        tags = list()
        if prog_uuids:
            for prog_id in prog_uuids.split(','):
                try:
                    program = Program.objects.get(uuid=prog_id)
                    log.info("Enrolled Program: {}".format(program.title))
                    converted_program = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Program')).active_translations(title=program.title)
                    response = {
                        "program_uuid":prog_id,
                        "program_title":program.title,
                        "converted_program_title":converted_program[0].title if converted_program.count() else program.title,
                        "tags":[]
                    }
                    log.info("---------program response--{}".format(response))
                    all_tag_names = {tag.name for tag in program.program_topics.all()}
                    for tag in all_tag_names:
                        tags_data = {}
                        converted_tag = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Tag')).active_translations(title=tag)
                        tags_data["tag_title"]= tag
                        tags_data["converted_tag_title"]= converted_tag[0].title if converted_tag.count() else tag
                        response['tags'].append(tags_data)
                    tags.append(response)
                except Program.DoesNotExist:
                    log.info("Program not found with uuid: {}".format(prog_id))
                except Exception as e:
                   log.info("Error occured due to: {}".format(e))
            if resume_data:
                resume_str = resume_data.replace(' ','+')
                resume_data = resume_str.split(',')
                log.info("Resume data received {}".format(resume_data))
                temp_course_id = resume_data[0].replace('course-v1:','')
                course_key = '+'.join(temp_course_id.split('+')[0:len(temp_course_id.split('+'))-1])
                course = Course.objects.get(key=course_key)
                programs = Program.objects.filter(courses=course)
                log.info("Course related programs: {}".format(programs))
                resume_course_programs = filter(lambda x:str(x.uuid) in prog_uuids.split(','), programs)
                log.info("Resume course programs: {}".format(resume_course_programs))
                resume_prog_uuid = [str(prog.uuid) for prog in resume_course_programs]
                for prog in tags:
                    if prog['program_uuid'] in resume_prog_uuid:
                        converted_course_name = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Course')).active_translations(title=course.title)
                        prog['resume_program'] = {
                            "course_id": resume_data[0],
                            "course_name": course.title,
                            "converted_course_name":converted_course_name[0].title if converted_course_name.count() else course.title,
                            "block_id": resume_data[-1],
                        }
        # import pdb;pdb.set_trace()
        return Response(tags,status=status.HTTP_200_OK)
    
    
class GetProgramTopics2(APIView):
    """ GET Program Based Topics View."""
    permission_classes = (IsAuthenticated,)
    
    def get(self, request):
        subject_name_param = request.GET.get('subject_name')
        sub = SubjectTranslation.objects.filter(name=subject_name_param)

        try:
            sub_id = sub[0].master.id
            sub_en = Subject.objects.language('en').get(id=sub_id)
            sub_name = sub_en.name
            
        except Exception as e:
            sub_name = subject_name_param
        
        # import pdb;pdb.set_trace()
        body = {
            "query": {"bool": {
                "must": [
                        { "match": {
                            "content_type": "program"
                            }
                        },
                        {"match": {
                            "program_subjects": sub_name
                            }
                        }
                        ]
                    }
                },
            "facets" : {
                "tags" : { "terms" : {"field" : "program_topics_exact"} }
                }
            }
        alias = settings.HAYSTACK_CONNECTIONS['default']['INDEX_NAME']
        
        # index = '{alias}_20160621_000000'.format(alias=alias)

        host = settings.HAYSTACK_CONNECTIONS['default']['URL']
        
        connection = Elasticsearch(host)
        index_value = connection.indices.get_alias(name=alias)
        es_response = connection.search(index=[i for i in index_value.keys()][0], body=body)

        

        try:
            accept_language = request.headers['Accept-Language']
            if not accept_language or accept_language=='en':
                for i in range(len(es_response['facets']['tags']['terms'])):
                    es_response['facets']['tags']['terms'][i]['original_term'] = es_response['facets']['tags']['terms'][i]['term']
                return Response(es_response['facets']['tags'])
        except KeyError:
            return Response(es_response['facets']['tags'])

        

        tag = MultiLingualDiscovery.objects.language('en').filter(Q(content_type='Tag')).active_translations(title__in=[i['term'] for i in es_response['facets']['tags']['terms']])

        converted_tag = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Tag')).active_translations(title__in=[i.title for i in tag])


        # data = tag.__dict__
        # import pdb;pdb.set_trace()
        data = {}
        for j in range(len(converted_tag)):
            data[tag[j].title] = converted_tag[j].title
            # if tag[j].title != converted_tag[j].title:
            #     data[tag[j].title] = converted_tag[j].title
            # else:
            #     data[tag[j].title] = ''
        
        for i in range(len(es_response['facets']['tags']['terms'])):
            if es_response['facets']['tags']['terms'][i]['term'] in data:
                es_response['facets']['tags']['terms'][i]['original_term'] = es_response['facets']['tags']['terms'][i]['term']
                es_response['facets']['tags']['terms'][i]['term'] = data[es_response['facets']['tags']['terms'][i]['term']]
            else:
                es_response['facets']['tags']['terms'][i]['original_term'] = es_response['facets']['tags']['terms'][i]['term']
            # else:
            #     es_response['facets']['tags']['terms'][i]['term'] = es_response['facets']['tags']['terms'][i]['term']

    
        return Response(es_response['facets']['tags'])