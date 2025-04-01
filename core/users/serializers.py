"""Serializers for user creation, profile updates, and summary operations."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Summary

User = get_user_model()


class ChildRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for registering child accounts."""

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        """Meta class for ChildRegistrationSerializer."""
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'password',
            'confirm_password', 'role'
        ]
        extra_kwargs = {'role': {'read_only': True}}

    def validate(self, attrs):  # Renamed 'data' -> 'attrs' to match DRF signature.
        """Validate password confirmation."""
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError('Passwords do not match.')
        return attrs

    def create(self, validated_data):
        """Create a child user account."""
        try:
            validated_data.pop('confirm_password', None)
            validated_data['role'] = 'child'  # Enforce child role.
            parent = self.context['request'].user
            validated_data['parent'] = parent
            user = User.objects.create_user(**validated_data)
            return user
        except Exception as exc:
            raise serializers.ValidationError(str(exc))


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for retrieving and updating user profiles."""

    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'role',
            'created_at', 'profile_image'
        ]


    def update(self, instance, validated_data):
        try:
            instance.first_name = validated_data.get('first_name', instance.first_name)
            instance.last_name = validated_data.get('last_name', instance.last_name)
            instance.email = validated_data.get('email', instance.email)

            if 'profile_image' in validated_data:
                instance.profile_image = validated_data['profile_image']

            instance.save()
            return instance
        except Exception as exc:
            raise serializers.ValidationError(str(exc))

class SummarySerializer(serializers.ModelSerializer):
    """Serializer for the Summary model with read-only creator details."""

    creator = UserProfileSerializer(read_only=True)

    class Meta:
        """Meta class for SummarySerializer."""
        model = Summary
        fields = ['id', 'description', 'creator']
