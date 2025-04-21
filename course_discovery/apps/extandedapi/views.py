from rest_framework.response import Response
from django.conf import settings
from elasticsearch import Elasticsearch
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from course_discovery.apps.course_metadata.models import Program, Course, CourseRun, SubjectTranslation, Organization, Subject
from course_discovery.apps.api.v1.views.search import CourseSearchViewSet
from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery,MultiLingualDiscoveryTranslation
from rest_framework import status
from collections import OrderedDict
from itertools import chain
import logging as log
from django.db.models import Q
from .serialializers import GetProgramCourseSerializer,GetCourseProgramSerializer
import logging

LANGUAGES = [
    ('en', 'English'),
    ('rtl', 'Right-to-Left Test Language'),
    ('eo', 'Dummy Language (Esperanto)'),  # Dummy languaged used for testing

    ('am', 'አማርኛ'),  # Amharic
    ('ar', 'العربية'),  # Arabic
    ('az', 'azərbaycanca'),  # Azerbaijani
    ('bg-bg', 'български (България)'),  # Bulgarian (Bulgaria)
    ('bn-bd', 'বাংলা (বাংলাদেশ)'),  # Bengali (Bangladesh)
    ('bn-in', 'বাংলা (ভারত)'),  # Bengali (India)
    ('bn', 'বাংলা (ভারত)'),  # Bengali (India)
    ('bs', 'bosanski'),  # Bosnian
    ('ca', 'Català'),  # Catalan
    ('ca@valencia', 'Català (València)'),  # Catalan (Valencia)
    ('cs', 'Čeština'),  # Czech
    ('cy', 'Cymraeg'),  # Welsh
    ('da', 'dansk'),  # Danish
    ('de-de', 'Deutsch (Deutschland)'),  # German (Germany)
    ('el', 'Ελληνικά'),  # Greek
    ('en-uk', 'English (United Kingdom)'),  # English (United Kingdom)
    ('en@lolcat', 'LOLCAT English'),  # LOLCAT English
    ('en@pirate', 'Pirate English'),  # Pirate English
    ('es-419', 'Español (Latinoamérica)'),  # Spanish (Latin America)
    ('es-ar', 'Español (Argentina)'),  # Spanish (Argentina)
    ('es-ec', 'Español (Ecuador)'),  # Spanish (Ecuador)
    ('es-es', 'Español (España)'),  # Spanish (Spain)
    ('es-mx', 'Español (México)'),  # Spanish (Mexico)
    ('es-pe', 'Español (Perú)'),  # Spanish (Peru)
    ('et-ee', 'Eesti (Eesti)'),  # Estonian (Estonia)
    ('eu-es', 'euskara (Espainia)'),  # Basque (Spain)
    ('fa', 'فارسی'),  # Persian
    ('fa-ir', 'فارسی (ایران)'),  # Persian (Iran)
    ('fi-fi', 'Suomi (Suomi)'),  # Finnish (Finland)
    ('fil', 'Filipino'),  # Filipino
    ('fr', 'Français'),  # French
    ('gl', 'Galego'),  # Galician
    ('gu', 'ગુજરાતી'),  # Gujarati
    ('he', 'עברית'),  # Hebrew
    ('hi', 'हिन्दी'),  # Hindi
    ('hr', 'hrvatski'),  # Croatian
    ('hu', 'magyar'),  # Hungarian
    ('hy-am', 'Հայերեն (Հայաստան)'),  # Armenian (Armenia)
    ('id', 'Bahasa Indonesia'),  # Indonesian
    ('it-it', 'Italiano (Italia)'),  # Italian (Italy)
    ('ja-jp', '日本語 (日本)'),  # Japanese (Japan)
    ('kk-kz', 'қазақ тілі (Қазақстан)'),  # Kazakh (Kazakhstan)
    ('km-kh', 'ភាសាខ្មែរ (កម្ពុជា)'),  # Khmer (Cambodia)
    ('kn', 'ಕನ್ನಡ'),  # Kannada
    ('ko-kr', '한국어 (대한민국)'),  # Korean (Korea)
    ('lt-lt', 'Lietuvių (Lietuva)'),  # Lithuanian (Lithuania)
    ('ml', 'മലയാളം'),  # Malayalam
    ('mn', 'Монгол хэл'),  # Mongolian
    ('mr', 'मराठी'),  # Marathi
    ('ms', 'Bahasa Melayu'),  # Malay
    ('nb', 'Norsk bokmål'),  # Norwegian Bokmål
    ('ne', 'नेपाली'),  # Nepali
    ('nl-nl', 'Nederlands (Nederland)'),  # Dutch (Netherlands)
    ('or', 'ଓଡ଼ିଆ'),  # Oriya
    ('pl', 'Polski'),  # Polish
    ('pt-br', 'Português (Brasil)'),  # Portuguese (Brazil)
    ('pt-pt', 'Português (Portugal)'),  # Portuguese (Portugal)
    ('ro', 'română'),  # Romanian
    ('ru', 'Русский'),  # Russian
    ('si', 'සිංහල'),  # Sinhala
    ('sk', 'Slovenčina'),  # Slovak
    ('sl', 'Slovenščina'),  # Slovenian
    ('sq', 'shqip'),  # Albanian
    ('sr', 'Српски'),  # Serbian
    ('sv', 'svenska'),  # Swedish
    ('sw', 'Kiswahili'),  # Swahili
    ('ta', 'தமிழ்'),  # Tamil
    ('te', 'తెలుగు'),  # Telugu
    ('th', 'ไทย'),  # Thai
    ('tr-tr', 'Türkçe (Türkiye)'),  # Turkish (Turkey)
    ('uk', 'Українська'),  # Ukranian
    ('ur', 'اردو'),  # Urdu
    ('vi', 'Tiếng Việt'),  # Vietnamese
    ('uz', 'Ўзбек'),  # Uzbek
    ('zh-cn', '中文 (简体)'),  # Chinese (China)
    ('zh-hk', '中文 (香港)'),  # Chinese (Hong Kong)
    ('zh-tw', '中文 (台灣)'),  # Chinese (Taiwan)
]

LANGUAGE_DICT = dict(LANGUAGES)

# pylint: disable=attribute-defined-outside-init
# class GetProgramTopics(APIView):
#     """ GET Program Based Topics View."""
#     permission_classes = (IsAuthenticated,)
    
#     def get(self, request):
#         subject_name_param = request.GET.get('subject_name')
#         sub = SubjectTranslation.objects.filter(name=subject_name_param)

#         try:
#             sub_id = sub[0].master.id
#             sub_en = Subject.objects.language('en').get(id=sub_id)
#             sub_name = sub_en.name
            
#         except Exception as e:
#             sub_name = subject_name_param
        
#         body = {
#             "query": {"bool": {
#                 "must": [
#                         { "match": {
#                             "content_type": "program"
#                             }
#                         },
#                         {"match": {
#                             "program_subjects": sub_name
#                             }
#                         }
#                         ]
#                     }
#                 },
#             "facets" : {
#                 "tags" : { "terms" : {"field" : "program_topics_exact"} }
#                 }
#             }
#         alias = settings.HAYSTACK_CONNECTIONS['default']['INDEX_NAME']
        
#         host = settings.HAYSTACK_CONNECTIONS['default']['URL']
        
#         connection = Elasticsearch(host)
#         index_value = connection.indices.get_alias(name=alias)
#         es_response = connection.search(index=[i for i in index_value.keys()][0], body=body)

        

#         try:
#             accept_language = request.headers['Accept-Language']
#             if not accept_language or accept_language=='en':
#                 return Response(es_response['facets']['tags'])
#         except KeyError:
#             return Response(es_response['facets']['tags'])

        
        
#         tag = MultiLingualDiscovery.objects.language('en').filter(Q(content_type='Tag')).active_translations(title__in=[i['term'] for i in es_response['facets']['tags']['terms']])

#         converted_tag = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Tag')).active_translations(title__in=[i.title for i in tag])

#         data = {}
#         for j in range(len(converted_tag)):
#             if tag[j].title != converted_tag[j].title:
#                 data[tag[j].title] = converted_tag[j].title
#             else:
#                 data[tag[j].title] = ''
        
#         for i in range(len(es_response['facets']['tags']['terms'])):

#             if es_response['facets']['tags']['terms'][i]['term'] in data:
#                  es_response['facets']['tags']['terms'][i]['converted_term'] = data[es_response['facets']['tags']['terms'][i]['term']]
#             else:
#                 es_response['facets']['tags']['terms'][i]['converted_term'] = ''


#         return Response(es_response['facets']['tags'])

class GetProgramTopics(APIView):
    """ GET Program Based Topics View."""
    permission_classes = (IsAuthenticated,)
    
    def get(self, request):
        subject_name_param = request.GET.get('subject_name')
        sub = SubjectTranslation.objects.filter(name=subject_name_param)
        res = {"total":0, "terms":[], "missing": 0,"_type": "terms", "other": 0}
        try:
            if sub:
                sub_id = sub[0].master.id
                sub_en = Subject.objects.language('en').get(id=sub_id)
                sub_name = sub_en.name
            else:
                return Response(res)
            
        except Exception as e:
            sub_name = subject_name_param

        for program in sub_en.program_subjects.all():
            for topic in program.program_topics.all(): 
                term = {
                "converted_term": "",
                "count": 1,
                "term": topic.name
            }
                if term not in res['terms']:
                    res['terms'].append(term)
                    res['total'] = res['total']+1
        try:
            accept_language = request.headers['Accept-Language']
            # accept_language = 'ml'
            if not accept_language or accept_language=='en':
                return Response(res)
        except KeyError:
            return Response(res)
        tag = MultiLingualDiscovery.objects.language('en').filter(Q(content_type='Tag')).active_translations(title__in=[i['term'] for i in res['terms']])

        converted_tag = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Tag')).active_translations(
            title__in=[i.title for i in tag],
        )

        data = {}
        for j in range(len(converted_tag)):
            # import pdb; pdb.set_trace()

            # if converted_tag[j].get_current_language() != 'en-gb,en-us;q=0.9,en;q=0.8' and converted_tag[j].get_current_language() != 'en':
            #     data[tag[j].title] = converted_tag[j].title

            data[tag[j].title] = converted_tag[j].title

        for i in range(len(res['terms'])):
            if res['terms'][i]['term'] in data:
                res['terms'][i]['converted_term'] = data[res['terms'][i]['term']]
            else:
                res['terms'][i]['converted_term'] = res['terms'][i]['term']

       
    
        return Response(res)
    
#    For ml


# (Pdb) tag[j].__dict__
# {'_translations_cache': defaultdict(<class 'dict'>, {<class 'course_discovery.apps.mx_multilingual_discovery.models.MultiLingualDiscoveryTranslation'>
# : {'en': <MultiLingualDiscoveryTranslation: #1, en, master: #1>}}), 
# '_current_language': 'en', '_state': <django.db.models.base.ModelState object at 0x7f4aef6966f0>, 'id': 1, 'content_type': 'tag', 'program_title_id': None, 'course_title_id': None}
# (Pdb) converted_tag[j].__dict__

# {'_translations_cache': defaultdict(<class 'dict'>, {<class 'course_discovery.apps.mx_multilingual_discovery.models.MultiLingualDiscoveryTranslation'>: 
# {'ml': <MultiLingualDiscoveryTranslation: #2, ml, master: #1>}}), '_current_language': 'ml', '_state': <django.db.models.base.ModelState object at 0x7f4aef6db680>, 'id': 1, 'content_type': 'tag', 'program_title_id': None, 'course_title_id': None}


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
        language = request.headers['Accept-Language']
        for x in content.data['results']:
            programs_details = self.get_program_details(x['key'])
            x['program_details'] = programs_details
        content.data['results'] = list(filter(lambda data:(data['course_runs'][0]['language']=='en' or data['course_runs'][0]['language']== language), content.data['results']))
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
            
            if program is None:
                log.info("_____________________program_uuid is invalid______________")
                return Response({'message':'program_uuid is invalid'},status=400)
            
            result = dict()
            result["id"] = request.GET['program_uuid']
            result["data"]= list()
            lang_dict = LANGUAGE_DICT
            from course_discovery.apps.mx_multilingual_discovery.models import MultiLingualDiscovery
            from course_discovery.apps.course_metadata.models import CourseRun
            language = request.GET['language'] if 'language' in request.GET else 'en'
            for course in program.courses.all():
                data = dict()
                try:
                    course_run = CourseRun.objects.filter(course__id= course.id).first()
                    data["created"] = course_run.start
                except:
                    data["created"] = course.created
                
            
                if course.canonical_course_run:
                    log.info("_________ course {} having canonical_course_run it's key is {}".format(course,course.canonical_course_run.key))
                    data['key'] = course.canonical_course_run.key
                    data['title'] = course.title
                    converted_title = MultiLingualDiscovery.objects.filter(content_type='course', course_title__key=course.canonical_course_run.key).language(language).first()
                    data['converted_title'] = converted_title.title if converted_title else ''
                    
                    try:
                        data['language'] = course.canonical_course_run.language.code
                        data['language_name'] = lang_dict[course.canonical_course_run.language.code]

                    except:
                        data['language'] = "en"
                        data['language_name'] = lang_dict["en"]

                    result["data"].append(data)
                elif course.card_image_url:
                    courseKey = str('course')+course.card_image_url.split('asset')[1].split('type')[0][0:-1]
                    log.info("_________ course {} having card_image_url it's key is {}".format(course,courseKey))
                    data['key'] = courseKey
                    data['title'] = course.title
                    converted_title = MultiLingualDiscovery.objects.filter(content_type='course', course_title__key=courseKey).language(language).first()
                    data['converted_title'] = converted_title.title if converted_title else ''
                    
                    try:
                        data['language'] = course.canonical_course_run.language.code
                        data['language_name'] = lang_dict[course.canonical_course_run.language.code]
                    except:
                        data['language'] = "en"
                        data['language_name'] = lang_dict["en"]
                    result["data"].append(data)
                    
                else:
                    log.info("_________ course {} neither having card_image_url nor canonical_course_run".format(course))
                    continue
            log.info("data before sorting {}".format(result['data']))
            filter_data = filter(lambda data :( data.get("language")=="en" or data.get("language")==language),result['data'])
            sorted_data = sorted(filter_data, key=lambda d: d['created'])
            result['data'] = sorted_data
            
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
                program = Program.objects.filter(courses__key__in=[str(key[0])+str('+')+str(key[1])]).first()
                log.info("___________ fetched programs for course {} are {}".format(course_id,program))
            result = list()
            for course in program.courses.all():
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
        return Response(result,status=status.HTTP_200_OK)

class GetProgramUsingCourseId(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        if 'course_id' in request.GET:
            course_id = request.GET['course_id']
            key = course_id.replace(' ','+').split(':')[1].split('+')
            program = Program.objects.filter(courses__key=str(key[0])+str('+')+str(key[1])).first()
            result = dict()
            if program:
                
                topics = []
                
                for topic in program.program_topics.all():
                    topics.append(topic.name)
                
                result['topics'] = topics
                result['program_title'] = program.title
                result['course_title'] = program.courses.filter(key=str(key[0])+str('+')+str(key[1])).first().title
                
            
            return Response(result,status=status.HTTP_200_OK)

        else:
            Response(result,status=status.HTTP_500_Internal_Server_Error)

class GetCoursePrograms(APIView):
    permission_classes = (AllowAny,)
    def get(self,request):
        if 'course_id' in request.GET:
            course_id = request.GET['course_id']
            key = course_id.replace(' ','+').split(':')[1].split('+')
            programs = Program.objects.filter(courses__key=str(key[0])+str('+')+str(key[1])).values('uuid')
            result = list()
            if programs:
                result = [str(uuid['uuid']) for uuid in programs]
                
            return Response(result,status=status.HTTP_200_OK)

        else:
            Response(result,status=status.HTTP_500_Internal_Server_Error)


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

        courses_obj = CourseRun.objects.all()
        # courses = {course.title_override:course.title_override.upper() for course in courses}
        courses = {}
        for course in courses_obj:
            if course.title_override:
                courses[course.title_override] = course.title_override.upper()
            else:
                logging.warning(f"CourseRun with key={course.key} has title_override=None")

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
                        "tags":[],
                        "program_language": program.program_language,
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
                course_lang = "en"
                if course.canonical_course_run and course.canonical_course_run.language:
                    course_lang = course.canonical_course_run.language.code
                for prog in tags:
                    if prog['program_uuid'] in resume_prog_uuid:
                        converted_course_name = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Course')).active_translations(title=course.title)
                        prog['resume_program'] = {
                            "course_id": resume_data[0],
                            "course_name": course.title,
                            "converted_course_name":converted_course_name[0].title if converted_course_name.count() else course.title,
                            "block_id": resume_data[-1],
                            "course_language":course_lang

                        }
        return Response(tags,status=status.HTTP_200_OK)
    
    
class GetProgramTopics2(APIView):
    """ GET Program Based Topics View."""
    permission_classes = (IsAuthenticated,)
    
    def get(self, request):
        subject_name_param = request.GET.get('subject_name')
        sub = SubjectTranslation.objects.filter(name=subject_name_param)
        res = {"total":0, "terms":[]}
        try:
            if sub:
                sub_id = sub[0].master.id
                sub_en = Subject.objects.language('en').get(id=sub_id)
                sub_name = sub_en.name
            else:
                return Response(res)
            
        except Exception as e:
            sub_name = subject_name_param

        for program in sub_en.program_subjects.all():
            for topic in program.program_topics.all(): 
                term = {
                "original_term": topic.name,
                "count": 1,
                "term": topic.name,
                "topic_id": topic.id
            }
                if term not in res['terms']:
                    res['terms'].append(term)
                    res['total'] = res['total']+1
        try:
            accept_language = request.headers['Accept-Language']
            if not accept_language or accept_language=='en':
                return Response(res)
        except KeyError:
            return Response(res)

        tag = MultiLingualDiscovery.objects.language('en').filter(Q(content_type='Tag')).active_translations(title__in=[i['term'] for i in res['terms']])

        converted_tag = MultiLingualDiscovery.objects.language(accept_language).filter(Q(content_type='Tag')).active_translations(title__in=[i.title for i in tag])

        data = {}
        for j in range(len(converted_tag)):
            data[tag[j].title] = converted_tag[j].title

        for i in range(len(res['terms'])):
            if res['terms'][i]['term'] in data:
                res['terms'][i]['original_term'] = res['terms'][i]['term']
                res['terms'][i]['term'] = data[res['terms'][i]['term']]
            else:
                res['terms'][i]['original_term'] = res['terms'][i]['term']
    
        return Response(res)
    
    
class GetCouseProgramDetail(APIView):
    permission_classes = (AllowAny,)
    
    def get(self, request):
        course_id = self.request.query_params.get("course_id", None)
        course_key = course_id.replace(" ", "+")
        course_title = Course.objects.get(canonical_course_run__key=course_key).title
        programs = Program.objects.filter(courses__canonical_course_run__key=course_key)
        serializer = GetCourseProgramSerializer(programs, many=True)
        # return Response({"data":serializer.data}, status=status.HTTP_200_OK)
        return Response({"data":serializer.data, "course_title":course_title}, status=status.HTTP_200_OK)
    
    

class Getdetaillangbased(APIView):
    permission_classes = ()
    def get(self,request):
        language = request.GET.get('language', 'en')
        subject_uuid = request.GET.get('subject_uuid', '')
        program_uuid = request.GET.get('program_uuid', '')
        topic_id = request.GET.get('topic_id', '')
        tag = request.GET.get('topic', '')
        param = {}
        if subject_uuid:
            try:
                subject =  Subject.objects.language(language).get(uuid=subject_uuid)
            except:
                subject =  Subject.objects.language('en').get(uuid=subject_uuid)

            param = {
                    "subject_name": subject.name,
                    "subject_uuid": subject.uuid
                }
            
        if program_uuid:
            try:
                program =  Program.objects.get(uuid=program_uuid)
                converted_program = MultiLingualDiscovery.objects.language(language).filter(Q(content_type='Program', program_title__id=program.id)).active_translations().first()
                program_title = converted_program.title if converted_program else program.title
                authoring_organizations = program.authoring_organizations.first()
                org_name = authoring_organizations.name if authoring_organizations else ""

                param.update({
                    "program_title": program_title,
                    "program_banner_url": program.banner_image.url,
                    "org_name": org_name
                })
            except Exception as e:
                log.error(f"An error occurred: {e}")
                pass

        if topic_id and program_uuid:
            try:
                program_tag = program.program_topics.filter(id=topic_id).first()
                tag_name = program_tag.name
                converted_tag = MultiLingualDiscovery.objects.language(language).filter(Q(content_type='Tag')).active_translations(title=tag_name).first()
                tag_title = converted_tag.title if converted_tag else tag_name

                param.update({
                    "tag_title": tag_title,
                })
            except Exception as e:
                log.error(f"An error occurred: {e}")
                pass
        
        if topic_id and not program_uuid:
            try:
                # import pdb; pdb.set_trace()
                tag_name = subject.program_subjects.filter(program_topics__id=topic_id).values_list('program_topics__name', flat=True).first()
                if tag_name: 
                    converted_tag = MultiLingualDiscovery.objects.language(language).filter(Q(content_type='Tag')).active_translations(title=tag_name).first()
                    tag_title = converted_tag.title if converted_tag else tag_name
                    param.update({
                        "tag_title": tag_title,
                    })
                    
            except Exception as e:
                log.error(f"An error occurred: {e}")
                pass

         
        return Response(param,status=status.HTTP_200_OK)
    