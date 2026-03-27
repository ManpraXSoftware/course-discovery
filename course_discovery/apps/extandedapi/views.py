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
import requests
import os
from django.http import JsonResponse  
from django.views import View
from django.utils import timezone
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




class MXCustomSearch(APIView):
    """
    Custom search based on the courses.
    URL = {}/extandedapi/mx-custom-course-search/?page=1&page_size=1&q=water
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

    def get_translated_title(self, content_type, related_obj, language):
        """
        Helper to get translated title for program or course.
        Falls back to English, then original.
        """
        # Adjust content_type for course_run if necessary
        
        try:
            fk_field = f'{content_type}_title_id'
            master = MultiLingualDiscovery.objects.filter(
                content_type=content_type,
                **{fk_field: related_obj.id}
            ).last()
            if master:
                try:
                    translated = master.get_translation(language)
                    return translated.title
                except TranslationDoesNotExist:
                    # Fallback to master's default title (assuming English)
                    return master.title or related_obj.title
            return related_obj.title
        except Exception:
            return related_obj.title

    def get_translated_tag(self, tag_name, language):
        """
        Helper to get translated tag name.
        Falls back to English/master, then original.
        """
        try:
            tag_translation = MultiLingualDiscoveryTranslation.objects.filter(title=tag_name).last()
            if tag_translation:
                try:
                    translated_tag = MultiLingualDiscoveryTranslation.objects.filter(
                        master_id=tag_translation.master_id,
                        language_code=language
                    ).first()
                    if translated_tag:
                        return translated_tag.title
                    else:
                        # Fallback to the found translation (assuming English)
                        return tag_translation.title
                except Exception:
                    return tag_name
            return tag_name
        except Exception:
            return tag_name

    def get_program_details(self, course_key, language):
        programs_dict = OrderedDict()
        try:
            course = Course.objects.get(key=course_key)
            programs = Program.objects.filter(courses=course)
            if programs:
                translated_titles = []
                program_uuids = []
                translated_tags_list = []
                for program in programs:
                    trans_title = self.get_translated_title('program', program, language)
                    translated_titles.append(trans_title)
                    program_uuids.append(program.uuid)
                    trans_tags = [
                        self.get_translated_tag(tag.name, language)
                        for tag in program.program_topics.all()
                    ]
                    translated_tags_list.append(OrderedDict({
                        "program_name": trans_title,
                        "program_id": program.uuid,
                        "tags": trans_tags
                    }))

                programs_dict['programs'] = translated_titles
                programs_dict['program_id'] = program_uuids
                programs_dict['tags'] = translated_tags_list

            return programs_dict
        except Course.DoesNotExist:
            programs_dict = None
            return programs_dict

    def get(self, request):
        # Get query parameter 'q' from request
        query = request.GET.get('q', '')
        page_size = request.GET.get('page_size', '10')  
        page = request.GET.get('page', '1')  
        language = request.headers.get('Accept-Language', 'en')  # Default to 'en'
        MX_SEARCH_BASE_URL = settings.MX_SEARCH_BASE_URL
        LMS_URL = settings.LMS_URL

        # language = 'en'  

        # Call internal course search API
        api_url = f"{MX_SEARCH_BASE_URL}/mx-search-course/?page_size={page_size}&page={page}&lang={language}&q={query}"
        log.info("search API request via Mobile {}".format(api_url))
        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Raise exception for bad status codes
            api_data = response.json()
        except requests.RequestException as e:
            return Response({"count": 0,"next": None,"previous": None,"results": []}, status=status.HTTP_200_OK)

        # Ensure the response has the expected structure
        if api_data.get('status') != 'success':
            return Response({"count": 0,"next": None,"previous": None,"results": []}, status=status.HTTP_200_OK)

        # Process the results
        results = api_data.get('results', [])
        username = request.user.username
        for course in results:

        # Translate course name
            try:
                # import pdb; pdb.set_trace()

                course_run = CourseRun.objects.get(key=course['course_id'])

                course['course_name'] = self.get_translated_title('course', course_run, language)
            except CourseRun.DoesNotExist:
                # Keep original if no translation or course not found
                pass

            program_details = self.get_program_details(course['course_key'], language)
            course['program_details'] = program_details
            course['is_enroll'] = False 
            if program_details and 'program_id' in program_details:
                for program_uuid in program_details['program_id']:
                    check_program_url = (
                        f"{LMS_URL}/explore-courses/get-program-enrollment/"
                        f"?username={username}&program_uuid={program_uuid}"
                    )
                    try:
                        resp = requests.get(check_program_url)
                        resp.raise_for_status()
                        data = resp.json()

                        # ✅ Fix: match your API shape
                        if data.get("status") is True:
                            if data.get("is_enrolled") == "enrolled":
                                course['is_enroll'] = True
                                break
                    except requests.RequestException:
                        pass
        # Generate next and previous URLs
        current_page = api_data.get('page', 1)
        total_pages = api_data.get('total_pages', 1)
        base_url = request.build_absolute_uri('/extandedapi/mx-custom-course-search/')
        next_url = None
        previous_url = None

        # Construct next URL if not on the last page
        if current_page < total_pages:
            next_url = f"{base_url}?page={current_page + 1}&page_size={page_size}&q={query}"

        # Construct previous URL if not on the first page
        if current_page > 1:
            previous_url = f"{base_url}?page={current_page - 1}&page_size={page_size}&q={query}"

        # 
        # Construct final response
        final_response = OrderedDict()
        final_response["count"] = len(results)
        final_response["next"] = next_url
        final_response["previous"] = previous_url
        final_response["results"] = results

        return Response(final_response, status=status.HTTP_200_OK)

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
        orgs = {x.key:x.name.upper() for x in orgs_obj}

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

from parler.models import TranslationDoesNotExist
class GetCourseDetail(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # URL - {DISCOVERY_URL}/extandedapi/getcoursedetail/?course_id=course-v1%3AManprax%2BVE_TIK_MATH_G8_P2_CH08%2B2021
        course_run_key = request.GET.get('course_id')
        
        if not course_run_key:
            return Response(
                {
                    "status": "fail",
                    "message": "course_id is required",
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch the CourseRun and its associated Course
            course_run = CourseRun.objects.select_related('course').get(key=course_run_key)
            course = course_run.course
            
            # Fetch programs related to the course
            programs = Program.objects.filter(courses=course)
            
            if not programs.exists():
                # return Response(
                #     {
                #         "status": "fail",
                #         "message": "No programs found for the given course_id",
                #     },
                #     status=status.HTTP_404_NOT_FOUND
                # )
                pass

            # Get all available languages from MultiLingualDiscovery translations
            available_languages = MultiLingualDiscoveryTranslation.objects.values('language_code').distinct()
            available_languages = [lang['language_code'] for lang in available_languages]

            response_data = []
            for program in programs:
                # Fetch translated tags
                tags_data = []
                for tag in program.program_topics.all():
                    tag_translations = []
                    try:
                        tag_translation = MultiLingualDiscoveryTranslation.objects.filter(
                            title=tag.name
                        ).last()
                        if tag_translation:
                            for language in available_languages:
                                try:
                                    translated_tag = MultiLingualDiscovery.objects.language(language).filter(
                                        Q(content_type='Tag') & Q(id=tag_translation.master.id)
                                    ).first()
                                    if translated_tag and translated_tag.title not in tag_translations:
                                        tag_translations.append(translated_tag.title)
                                except TranslationDoesNotExist:
                                    continue
                            if not tag_translations:  # Fallback to default
                                tag_translations.append(tag_translation.title)
                    except MultiLingualDiscoveryTranslation.DoesNotExist:
                        tag.name not in tag_translations and tag_translations.append(tag.name)
                    tags_data.append({
                        "name": tag.name,
                        "tag_translations": tag_translations
                    })

                # Fetch translated program data
                program_translations = []
                program_translation = MultiLingualDiscoveryTranslation.objects.filter(
                    title=program.title
                ).last()
                if program_translation:
                    for language in available_languages:
                        try:
                            translated_program = MultiLingualDiscovery.objects.language(language).filter(
                                Q(content_type='Program') & Q(id=program_translation.master.id)
                            ).first()
                            if translated_program and translated_program.title not in program_translations:
                                program_translations.append(translated_program.title)
                        except TranslationDoesNotExist:
                            continue
                    if not program_translations:  # Fallback to default
                        program_translation.title not in program_translations and program_translations.append(program_translation.title)

                # Fetch subject names
                subjects_data = []
                for subject in program.program_subjects.all():
                    subject_translations = []
                    subject_translation = subject.translations.first()
                    if subject_translation:
                        for language in available_languages:
                            try:
                                translated_subject = subject.translations.get(language_code=language)
                                translated_subject.name not in subject_translations and subject_translations.append(translated_subject.name)
                            except TranslationDoesNotExist:
                                continue
                        if not subject_translations:  # Fallback to default
                            subject_translations.append(subject_translation.name)

                    subjects_data.append({
                        "name": subject.name,
                        "subject_translations": subject_translations
                    })

                # Construct program response
                program_data = {
                    "program_name": program.title,
                    "program_uuid": str(program.uuid),
                    "subjects": subjects_data,
                    "program_language": program.program_language,
                    "tags": tags_data,
                    "subtitle": program.subtitle,
                    "translated_program": program_translations
                }
                response_data.append(program_data)
            
            # Fetch course translation
            course_translations = []
            course_translation = MultiLingualDiscoveryTranslation.objects.filter(
                title=course.title
            ).last()
            if course_translation:
                for language in available_languages:
                    try:
                        translated_course = MultiLingualDiscovery.objects.language(language).filter(
                            Q(content_type='Course') & Q(id=course_translation.master.id)
                        ).first()
                        if translated_course:
                            translated_course.title not in course_translations and course_translations.append(translated_course.title)
                    except TranslationDoesNotExist:
                        continue
                if not course_translations:  # Fallback to default
                    course_translations.append(course_translation.title)
            return Response(
                {
                    "status": "success",
                    "message": "Course and program details retrieved successfully",
                    "course": {
                        "translated_course": course_translations,
                        "short_description": course_run.short_description_override,
                        "course_key": course.key,
                        "course_lang": course_run.language.code if course_run.language else "en"
                    },
                    "programs": response_data
                },
                status=status.HTTP_200_OK
            )

        except CourseRun.DoesNotExist:
            return Response(
                {
                    "status": "fail",
                    "message": f"No CourseRun found for key: {course_run_key}",
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "status": "fail",
                    "message": f"An error occurred: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        


class GetProgramCourseDetail(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # URL - {Discovery}/extandedapi/getprogramcoursedetail/?course_id=course-v1%3AManprax%2Bmx_course_01%2B2024_01
        course_run_key = request.GET.get('course_id')
        
        if not course_run_key:
            return Response(
                {
                    "status": "fail",
                    "message": "course_id is required",
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch the CourseRun and its associated Course
            course_run = CourseRun.objects.select_related('course').get(key=course_run_key)
            course = course_run.course
            
            # Fetch programs related to the course
            programs = Program.objects.filter(courses=course, status="active")
            if not programs.exists():
                return Response(
                    {
                        "status": "fail",
                        "message": "No programs found for the given course_id",
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            response_data = []
            program_uuids = [str(program.uuid) for program in programs]
            response_data = getProgramCourseDetail(program_uuids)
        
            
            return Response(
                {
                    "status": "success",
                    "message": "Course and program details retrieved successfully",
                    "programs": response_data if response_data else []
                },
                status=status.HTTP_200_OK
            )

        except CourseRun.DoesNotExist:
            return Response(
                {
                    "status": "fail",
                    "message": f"No CourseRun found for key: {course_run_key}",
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "status": "fail",
                    "message": f"An error occurred: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

def getProgramCourseDetail(program_uuids):
    try:
        programs = Program.objects.filter(uuid__in=program_uuids)
        # Get all available languages from MultiLingualDiscoveryTranslation
        available_languages = MultiLingualDiscoveryTranslation.objects.values('language_code').distinct()
        available_languages = [lang['language_code'] for lang in available_languages]

        response_data = []
        for program in programs:
            # Fetch translated tags
            tags_data = []
            for tag in program.program_topics.all():
                tag_translations = []
                try:
                    # Find translations by matching tag name and master_id
                    tag_translation = MultiLingualDiscoveryTranslation.objects.filter(
                        title=tag.name
                    ).last()
                    if tag_translation:
                        for language in available_languages:
                            try:
                                translated_tag = MultiLingualDiscoveryTranslation.objects.filter(
                                    master_id=tag_translation.master_id,
                                    language_code=language
                                ).first()
                                if translated_tag and translated_tag.title not in tag_translations:
                                    tag_translations.append(translated_tag.title)
                            except TranslationDoesNotExist:
                                continue
                        if not tag_translations:  # Fallback to default
                            tag_translations.append(tag_translation.title)
                    else:
                        # tag_translations.append(tag.name)
                        tag.name not in tag_translations and tag_translations.append(tag.name)
                except MultiLingualDiscoveryTranslation.DoesNotExist:
                    # tag_translations.append(tag.name)
                    tag.name not in tag_translations and tag_translations.append(tag.name)
                tags_data.append({
                    "name": tag.name,
                    "tag_translations": tag_translations
                })

            # Fetch translated program data
            program_translations = []
            try:
                # program_translation = MultiLingualDiscoveryTranslation.objects.filter(
                #     master_id=program.id
                # ).last()

                program_translation = MultiLingualDiscovery.objects.filter(
                                Q(content_type='Program') & Q(program_title__id=program.id)
                            ).first()
                
                if program_translation:
                    for language in available_languages:
                        try:
                            translated_program = MultiLingualDiscoveryTranslation.objects.filter(
                                master_id=program_translation.id,
                                language_code=language
                            ).first()
                            if translated_program and translated_program.title not in program_translations:
                                program_translations.append(translated_program.title)
                        except TranslationDoesNotExist:
                            continue
                    if not program_translations:  # Fallback to default
                        program_translations.append(program_translation.title)
                else:
                    # program_translations.append(program.title)
                    program.title not in program_translations and program_translations.append(program.title)
            except MultiLingualDiscovery.DoesNotExist:
                # program_translations.append(program.title)
                program.title not in program_translations and program_translations.append(program.title)


            # Fetch subjects with translations
            subjects_data = []
            for subject in program.program_subjects.all():
                subject_translations = []
                try:
                    subject_translation = subject.translations.first()
                    if subject_translation:
                        for language in available_languages:
                            try:
                                translated_subject = subject.translations.get(language_code=language)
                                if translated_subject.name not in subject_translations:
                                    subject_translations.append(translated_subject.name)
                            except TranslationDoesNotExist:
                                continue
                        if not subject_translations:  # Fallback to default
                            subject_translations.append(subject_translation.name)
                    else:
                        # subject_translations.append(subject.name)
                        subject.name not in subject_translations and subject_translations.append(subject.name)
                except AttributeError:
                    # subject_translations.append(subject.name)
                    subject.name not in subject_translations and subject_translations.append(subject.name)

                subjects_data.append({
                    "name": subject.name,
                    "subject_translations": subject_translations
                })

            # Fetch courses related to the program
            courses_data = []
            for course in program.courses.all():
                try:
                    course_run = CourseRun.objects.filter(course=course).order_by('-start').first()
                    if not course_run:
                        log.warning(f"No CourseRun found for course {course.title} in program {program.uuid}")
                        continue
                    course_translations = []
                    try:

                        # course_translation = MultiLingualDiscoveryTranslation.objects.filter(
                        #     master_id=course.id
                        # ).last()

                        course_translation = MultiLingualDiscovery.objects.filter(
                                Q(content_type='Course') & Q(course_title__id=course.id)
                            ).first()
                        
                        if course_translation:
                            for language in available_languages:
                                try:
                                    translated_course = MultiLingualDiscoveryTranslation.objects.filter(
                                        master_id=course_translation.id,
                                        language_code=language
                                    ).first()
                                    if translated_course and translated_course.title not in course_translations:
                                        course_translations.append(translated_course.title)
                                
                                except TranslationDoesNotExist:
                                    continue
                            if not course_translations:  # Fallback to default
                                course_translations.append(course_translation.title)
                        else:
                            # course_translations.append(course.title)
                            course.title not in course_translations and course_translations.append(course.title)
                    except MultiLingualDiscovery.DoesNotExist:
                        # course_translations.append(course.title)
                        course.title not in course_translations and course_translations.append(course.title)

                    courses_data.append({
                        "course_title": course.title,
                        "course_id": str(course_run.key),
                        "translated_course": course_translations,
                        "short_description": course_run.short_description_override or "",
                    })
                except Exception as e:
                    log.error(f"Error processing course {course.title} for program {program.uuid}: {str(e)}")
                    continue

            program_lang_name = dict(settings.LANGUAGES).get(program.program_language, "English") if program.program_language else "English"

            # Construct program response
            program_data = {
                "program_name": program.title,
                "program_uuid": str(program.uuid),
                "program_language": program.program_language or "en",
                "program_lang_name": program_lang_name,
                "authoring_org": program.authoring_organizations.first().name if program.authoring_organizations and program.authoring_organizations.first() else "",
                "tags": tags_data,
                "translated_program": program_translations,
                "subjects": subjects_data,
                "courses": courses_data,
                "subtitle": program.subtitle or "",
                "banner_image_url": program.banner_image.url,
                # "card_image": program.card_image.card.url if program.card_image else "",
                # "card_image_url": program.card_image_url or ""
            }
            response_data.append(program_data)
        return response_data
    except Exception as e:
        log.error(f"Error in getProgramCourseDetail for UUIDs {program_uuids}: {str(e)}")
        return []
    


from edx_elasticsearch_dsl_extensions.management.commands.mx_index_contents import Command as  MXReindexCommand

class ReindexProgramByUIDView(View):
    def get(self, request, uuid):
        try:
            # Check if the program exists
            program = Program.objects.filter(uuid=uuid).first()
            if not program:
                log.error(f"No Program found with UUID: {uuid}")
                return JsonResponse({"status": "error", "message": f"No Program found with UUID: {uuid}"}, status=404)

            # Initialize reindex command
            reindex_command = MXReindexCommand()
            LMS_URL = getattr(settings, 'LMS_URL', "")
            source_id = 'reindex_program_by_uid_view'
            file_dir = '/'.join(os.path.dirname(__file__).split('/')[:4])

            # Get and validate course run keys using a for loop
            course_keys = []
            invalid_keys = []
            today = timezone.now()
            
            for course in program.courses.all():
                course_runs = CourseRun.objects.filter(course=course, start__lt=today, start__isnull=False)
                for course_run in course_runs:
                    if course_run.key:
                        course_keys.append(course_run.key)
                    else:
                        invalid_keys.append(course_run.id)
                        log.warning(f"CourseRun with ID {course_run.id} has no valid key")

            # Reindex each course run individually
            course_success = True
            failed_keys = []
            for key in course_keys:
                try:
                    # # Pass one course run key at a time
                    success = reindex_command.reindex_courses(
                        course_id=str(key),  
                        batch_size=1,
                        file_dir=file_dir,
                        LMS_URL=LMS_URL,
                        source_id=source_id
                    )
                    if not success:
                        log.error(f"Failed to reindex course run with key: {key}")
                        failed_keys.append(key)
                        course_success = False
                    else:
                        log.info(f"Successfully reindexed course run with key: {key}")
         
                except Exception as e:
                    log.error(f"Error in reindexing its course runs: {str(e)}")
                    invalid_keys.append(key)
                    course_success = False

            if invalid_keys:
                log.warning(f"Invalid or missing course run keys: {invalid_keys}")
            if failed_keys:
                log.warning(f"Failed to reindex course run keys: {failed_keys}")

            # Combine results
            if course_success:
                log.info(f"Successfully triggered reindexing for program UUID: {uuid} with {len(course_keys)} courses")
                return JsonResponse({
                    "status": "success",
                    "message": f"Successfully triggered reindexing for program UUID: {uuid} with {len(course_keys)} courses",
                    "invalid_keys": invalid_keys,
                    "failed_keys": failed_keys
                }, status=202)
            else:
                log.error(f"Failed to trigger reindexing for program UUID: {uuid} ")
                return JsonResponse({
                    "status": "error",
                    "message": f"Failed to trigger reindexing for program UUID: {uuid}",
                    "invalid_keys": invalid_keys,
                    "failed_keys": failed_keys
                }, status=500)

        except Exception as e:
            log.error(f"Error in reindexing program UUID {uuid} : {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"Error in reindexing program : {str(e)}",
                "invalid_keys": invalid_keys if 'invalid_keys' in locals() else [],
                "failed_keys": failed_keys if 'failed_keys' in locals() else []
            }, status=500)