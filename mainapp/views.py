from django.shortcuts import render
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import FileSerializer, RegisterSerializer
from rest_framework.permissions import IsAuthenticated
from .models import File
from django.shortcuts import get_object_or_404
from .serializers import *
from filegate.pagination import filePagination

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

@api_view(['GET', 'DELETE'])
def download_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if request.method == 'DELETE':
        if not request.user.is_authenticated or file_obj.user != request.user:
            return Response(
                {"error": "You don't have permission to delete this file"},
                status=status.HTTP_403_FORBIDDEN
            )
        file_obj.delete()
        return Response(
            {"message": "File deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    
    # GET - download file (no auth required)
    file_obj.download_count += 1
    file_obj.save()
    return FileResponse(file_obj.file, as_attachment=True, filename=file_obj.filename)

@api_view(['GET'])
def preview_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    # Check if file is a text file
    text_extensions = ['.txt', '.csv', '.json', '.xml', '.html', '.css', '.js', '.py', '.java', '.cpp', '.c', '.md', '.log']
    file_extension = '.' + file_obj.filename.split('.')[-1].lower() if '.' in file_obj.filename else ''
    
    if file_extension in text_extensions:
        try:
            # Read text file content
            with file_obj.file.open('r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return Response({
                "filename": file_obj.filename,
                "content": content,
                "preview_url": request.build_absolute_uri(f"/api/files/{file_obj.id}/")
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to read file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # For document files (PDF, Word), images, videos, etc., return the preview URL
    preview_url = request.build_absolute_uri(f"/api/files/{file_obj.id}/")
    return Response({
        "filename": file_obj.filename,
        "preview_url": preview_url
    }) 

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_files(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    files = File.objects.filter(user=request.user)
    paginator = filePagination()
    result_page = paginator.paginate_queryset(files, request)
    serializer = FileSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)