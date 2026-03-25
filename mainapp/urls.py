from .views import *
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("auth/register/", register),
    path("auth/login/", TokenObtainPairView.as_view(),name='token_obtain_pair'),
    path("auth/refresh/", TokenRefreshView.as_view(),name='token_refresh'),
    path("files/", upload_file,name='upload_file'),
    path("files/<uuid:file_id>/", download_file,name='download_file'),
    path("files/my/",my_files,name='my_files')
]