from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .emails import email_verification_token, password_reset_token, user_from_uid

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
        if Account.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_('Email already registered.'))
        return value

    def validate_password(self, value):
        # Given the new account's username and email, so any validator that compares against them
        # works. Still per-field, so these errors come back together with any username or email errors.
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
            email_verified=False,
        )


class LoginSerializer(TokenObtainPairSerializer):
    """SimpleJWT's sign-in, where the `username` field also accepts the account's email address."""

    def validate(self, attrs):
        login = attrs.get(self.username_field, '').strip()
        # A username may itself contain "@", so an exact username match wins over an email match.
        if '@' in login and not Account.objects.filter(username=login).exists():
            usernames = list(Account.objects.filter(email__iexact=login).values_list('username', flat=True)[:2])
            if len(usernames) == 1:
                attrs[self.username_field] = usernames[0]
        return super().validate(attrs)


class GoogleSignInSerializer(serializers.Serializer):
    """`credential`: the ID token Google Identity Services hands the browser."""
    credential = serializers.CharField()


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'username', 'email', 'email_verified', 'verified_seller']
        read_only_fields = fields


class EmailLinkSerializer(serializers.Serializer):
    """The uid and token from an emailed link; `token_generator` is set by the subclass."""
    token_generator = None
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = user_from_uid(attrs['uid'])
        if user is None or not self.token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError(_('This link is invalid or has expired. Please ask for a new one.'))
        attrs['user'] = user
        return attrs


class VerifyEmailSerializer(EmailLinkSerializer):
    token_generator = email_verification_token


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(EmailLinkSerializer):
    token_generator = password_reset_token
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        try:
            password_validation.validate_password(attrs['password'], attrs['user'])
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})
        return attrs
