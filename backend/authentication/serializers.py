from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext as _
from rest_framework import serializers

Account = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Creates a new Account with a securely hashed password (via create_user)."""
    password = serializers.CharField(write_only=True)

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

    def validate_password(self, value):
        # Run with the new account's username and email: as a bare field validator, "too similar to
        # your username or email" was silently skipped. Still per-field, so these errors come back
        # together with any username or email errors.
        user = Account(username=self.initial_data.get('username', ''), email=self.initial_data.get('email', ''))
        try:
            password_validation.validate_password(value, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
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
