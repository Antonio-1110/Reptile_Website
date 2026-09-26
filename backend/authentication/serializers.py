from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext as _
from rest_framework import serializers

Account = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Creates a new Account with a securely hashed password (via create_user)."""
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Account
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'email': {'required': True}}

    def validate_username(self, value):
        if Account.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('Username already exists.'))
        return value

    def validate_email(self, value):
        if Account.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('Email already registered.'))
        return value

    def create(self, validated_data):
        return Account.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'username', 'email', 'verified_seller']
        read_only_fields = fields
