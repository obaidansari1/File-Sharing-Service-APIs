from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import File, Folder


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']

class FileSerializer(serializers.ModelSerializer):
    thumbnail_file = serializers.FileField(read_only=True)

    resized_file = serializers.FileField(read_only=True)
    class Meta:
        model = File
        fields = ['id', 'user', 'file', 'filename', 'folder', 'uploaded_at', 'download_count', 'thumbnail_file',
            'resized_file', 'processing_status']
        read_only_fields = ['id', 'user', 'uploaded_at', 'download_count', 'thumbnail_file',
            'resized_file', 'processing_status']
