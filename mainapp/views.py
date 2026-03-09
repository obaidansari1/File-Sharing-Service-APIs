from django.shortcuts import render
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import RegisterSerializer
from rest_framework.permissions import IsAuthenticated
from .models import File
from django.shortcuts import get_object_or_404

# Create your views here.

@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                "message": "User registered successfully",
                "user": {
                    "id": serializer.instance.id,
                    "username": serializer.instance.username,
                    "email": serializer.instance.email,
                }
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    
    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)  
    
    file_obj = File.objects.create(
        user = request.user,
        file = uploaded_file,
        filename = uploaded_file.name
    )

    download_url = request.build_absolute_uri(
    f"/api/files/download/{file_obj.id}/"
    )

    return Response(
        {
            "message":"File uploaded successfully",
            "file_id": file_obj.id,
            "download_url": download_url
        }
    )

@api_view(['GET'])
def download_file(request, file_id):
    file_obj = get_object_or_404(File,id=file_id)
    file_obj.download_count += 1
    file_obj.save()
    return FileResponse(file_obj.file, as_attachment=True, filename=file_obj.filename) 