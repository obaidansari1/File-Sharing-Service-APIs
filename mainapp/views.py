from django.shortcuts import render
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import FileSerializer, RegisterSerializer, FolderSerializer
from rest_framework.permissions import IsAuthenticated
from .models import File, Folder
from django.shortcuts import get_object_or_404
from .serializers import *
from filegate.pagination import filePagination
from .tasks import process_image

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

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def folders_list(request):
    """Create a new folder or list all folders for the authenticated user"""
    
    if request.method == 'POST':
        name = request.data.get('name')
        if not name or not name.strip():
            return Response(
                {"error": "Folder name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if folder already exists
        if Folder.objects.filter(user=request.user, name=name).exists():
            return Response(
                {"error": "Folder with this name already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        folder = Folder.objects.create(user=request.user, name=name)
        serializer = FolderSerializer(folder)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    # GET - list all folders for this user
    folders = Folder.objects.filter(user=request.user).order_by('-created_at')
    serializer = FolderSerializer(folders, many=True)
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_folder(request, folder_id):
    """Delete a folder and move its files to root"""
    folder = get_object_or_404(Folder, id=folder_id)
    
    if folder.user != request.user:
        return Response(
            {"error": "You don't have permission to delete this folder"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Move all files in this folder to root (folder=None)
    File.objects.filter(folder=folder).update(folder=None)
    folder.delete()
    
    return Response(
        {"message": "Folder deleted successfully"},
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    try:
        print("USER:", request.user)
        print("FILES:", request.FILES)
        print("DATA:", request.data)
        
        uploaded_file = request.FILES.get("file")
        # Try to get folder_id from data, then POST
        folder_id = request.data.get("folder_id") or request.POST.get("folder_id")

        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        folder = None
        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id)
                if folder.user != request.user:
                    return Response(
                        {"error": "You don't have permission to upload to this folder"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Folder.DoesNotExist:
                return Response(
                    {"error": "Folder not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        file_obj = File.objects.create(
            user = request.user,
            file = uploaded_file,
            filename = uploaded_file.name,
            folder = folder
        )

        process_image.delay(file_obj.id)
        
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
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            status=status.HTTP_200_OK
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
def view_file(request, file_id):
    """Serve files inline for preview (especially PDFs and videos)"""
    file_obj = get_object_or_404(File, id=file_id)
    
    filename_lower = file_obj.filename.lower()
    
    # For PDFs, serve inline
    if filename_lower.endswith('.pdf'):
        response = FileResponse(file_obj.file, as_attachment=False, filename=file_obj.filename)
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = f'inline; filename="{file_obj.filename}"'
        return response
    
    # For images, serve inline (use resized if available)
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    if any(filename_lower.endswith(ext) for ext in image_extensions):
        file_to_serve = file_obj.resized_file if file_obj.resized_file else file_obj.file
        response = FileResponse(file_to_serve, as_attachment=False, filename=file_obj.filename)
        return response
    
    # For videos, serve resized version if available
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    if any(filename_lower.endswith(ext) for ext in video_extensions):
        if file_obj.resized_file:
            response = FileResponse(file_obj.resized_file, as_attachment=False, filename=file_obj.filename)
            response['Content-Type'] = 'video/mp4'
            response['Content-Disposition'] = f'inline; filename="{file_obj.filename}"'
            return response
        else:
            # If no resized version, serve original
            response = FileResponse(file_obj.file, as_attachment=False, filename=file_obj.filename)
            response['Content-Type'] = 'video/mp4'
            response['Content-Disposition'] = f'inline; filename="{file_obj.filename}"'
            return response
    
    # For other files, redirect to download
    return Response({
        "error": "File type not supported for inline viewing",
        "download_url": request.build_absolute_uri(f"/api/files/{file_obj.id}/")
    }, status=status.HTTP_400_BAD_REQUEST) 

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_files(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    folder_id = request.query_params.get('folder_id')
    
    if folder_id:
        folder = get_object_or_404(Folder, id=folder_id)
        if folder.user != request.user:
            return Response(
                {"error": "You don't have permission to view this folder"},
                status=status.HTTP_403_FORBIDDEN
            )
        files = File.objects.filter(user=request.user, folder=folder)
    else:
        files = File.objects.filter(user=request.user, folder__isnull=True)
    
    paginator = filePagination()
    result_page = paginator.paginate_queryset(files, request)
    serializer = FileSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)
