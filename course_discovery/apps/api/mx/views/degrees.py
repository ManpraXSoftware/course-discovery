from rest_framework import status, viewsets

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from course_discovery.apps.api import  serializers
from course_discovery.apps.course_metadata.models import Degree, Video, Curriculum, IconTextPairing
from django.core.paginator import Paginator
from django.db.models import Q
from taggit.models import Tag
from course_discovery.apps.core.models import Partner

class DegreeViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.DegreeDataSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Degree.objects.all().order_by('-id')

    def get_serializer_class(self):
        if self.action=='create':
            return serializers.CreateDegreeSerializer
        else:
          return self.serializer_class


    def list(self,request):
        search = self.request.query_params.get("q", None)
        queryset = self.queryset
        if search and self.request.query_params.get("status", '') != '':
            status_list = self.request.query_params.get("status").split(",")
            queryset = queryset.filter(status__in=status_list).filter(Q(title__icontains=search)|Q(subtitle=search))
        elif search:
            queryset = queryset.filter(Q(title__icontains=search)|Q(subtitle=search))
        elif self.request.query_params.get("status", '') != '':
          status_list = self.request.query_params.get("status").split(",")
          queryset = queryset.filter(status__in=status_list)
        page = self.request.query_params.get("page",1)
        page_size = self.request.query_params.get("page_size",10)
        paginator = Paginator(queryset, page_size)
        paginated_data = paginator.page(page)
        serializer = self.get_serializer(paginated_data.object_list, many=True)
        return Response({"results":serializer.data,"per_page":paginated_data.paginator.per_page,
              "num_pages":paginated_data.paginator.num_pages,'count':paginated_data.paginator.count},status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        partner = Partner.objects.first()
        request.data._mutable = True
        request.data['partner'] = partner.id
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
          serializer.save()
          return Response([],status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk, partial=True):
        program = Degree.objects.get(id=pk)
        request.data._mutable = True
        if request.data.get('video_url', ''):
           videos = Video.objects.filter(src=request.data['video_url'])
           if videos:
              request.data['video'] = videos[0].id
           else:
              video = Video.objects.create(src=request.data['video_url'])
              request.data['video'] = video.id
        else:
          request.data['video']= ''
        serializer =  self.get_serializer(program, data=request.data, partial=True)
        if serializer.is_valid():
          serializer.save()
          if request.data.getlist("labels"):
            program.labels.clear()
            if request.data.getlist('labels')[0] != '':
              program.labels.add(*Tag.objects.filter(id__in=request.data.getlist("labels")))
          return Response(self.get_serializer(program).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk):
        program = Degree.objects.get(uuid=pk)
        serializer =  self.get_serializer(program)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class VideoViewSet(viewsets.ModelViewSet):
   serializer_class = serializers.VideoSerializer
   permission_classes = (IsAuthenticated,)
   queryset = Video.objects.all()
   
class CurriculumViewSet(viewsets.ModelViewSet):
  serializer_class = serializers.DegreeCurriculumSerializer
  permission_classes = (IsAuthenticated,)
  queryset = Curriculum.objects.filter(is_active=True)
  
  def list(self,request):
    queryset = self.queryset
    degree_id = self.request.query_params.get("degree", None)
    if degree_id:
      queryset = self.queryset.filter(program__id=degree_id)
    serializer = self.get_serializer(queryset, many=True)
    return Response(serializer.data,status=status.HTTP_200_OK)
  
  
class QuickfactViewSet(viewsets.ModelViewSet):
  serializer_class = serializers.DegreeIconTextPairingSerializer
  permission_classes = (IsAuthenticated,)
  queryset = IconTextPairing.objects.all()
  
  def list(self,request):
    queryset = self.queryset
    degree_id = self.request.query_params.get("degree", None)
    if degree_id:
      queryset = self.queryset.filter(degree__id=degree_id)
    serializer = serializers.CustomDegreeIconTextPairingSerializer(queryset, many=True)
    return Response(serializer.data,status=status.HTTP_200_OK)