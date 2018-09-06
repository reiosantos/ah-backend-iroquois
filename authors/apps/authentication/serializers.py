from django.contrib.auth import authenticate

from rest_framework import serializers
import re
from .models import User

import os

from django.shortcuts import get_object_or_404


class RegistrationSerializer(serializers.ModelSerializer):
    """Serializers registration requests and creates a new user."""

    # Ensure passwords are at least 8 characters long, no longer than 128
    # characters, and can not be read by the client.
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )
    # The client should not be able to send a token along with a registration
    # request. Making `token` read-only handles that for us.
    token = serializers.CharField(max_length=255, read_only=True)

    # all registration validation.
    def make_validations(self, username, email, password):

        if email is None:
            raise serializers.ValidationError(
                'An email address is required to register.'
            )

        if re.compile('[!@#$%^&*:;?><.0-9]').match(username):
            raise serializers.ValidationError(
                'Invalid Username , it contains invalid characters.'
            )
        if not re.match(r"([\w\.-]+)@([\w\.-]+)(\.[\w\.]+$)", email):
            raise serializers.ValidationError(
                'Enter a valid email address.'
            )

        if str(password).isdigit():
            raise serializers.ValidationError(
                'Enter an alphanumeric password, e.g one number and one letter.'
            )

        if password is None:
            raise serializers.ValidationError(
                'A password is required to register.'
            )

    def validate(self, data):
        # The `validate` method is where we make sure that the current
        # instance of `LoginSerializer` has "valid". In the case of logging a
        # user in, this means validating that they've provided an email
        # and password and that this combination matches one of the users in
        username = data.get('username', None)
        email = data.get('email', None)
        password = data.get('password', None)

        self.make_validations(username, email, password)

        return {
            'email': email,
            'username': username,
            'password': password,
        }

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'token']

    def create(self, validated_data):
        # Use the `create_user` method we wrote earlier to create a new user.
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):

    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)

    def check_user(self, user):
        if user is None:
            raise serializers.ValidationError(
                'A user with this email and password was not found.'
            )
        # Django provides a flag on our `User` model called `is_active`. The
        # purpose of this flag to tell us whether the user has been banned
        # or otherwise deactivated. This will almost never be the case, but
        # it is worth checking for. Raise an exception in this case.
        if not user.is_active:
            raise serializers.ValidationError(
                'This user has been deactivated.'
            )

        if not user.is_email_verified:
            raise serializers.ValidationError(
                'An account with this email is not verified.'
            )

    def validate(self, data):
        email = data.get('email', None)
        password = data.get('password', None)

        if email is None:
            raise serializers.ValidationError(
                'An email address is required to log in.'
            )

        # As mentioned above, a password is required. Raise an exception if a
        # password is not provided.
        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )
        user = authenticate(username=email, password=password)

        # If no user was found matching this email/password combination then
        # `authenticate` will return `None`. Raise an exception in this case.
        self.check_user(user)
        # The `validate` method should return a dictionary of validated data.
        # This is the data that is passed to the `create` and `update` methods
        # that we will see later on.
        return {
            'email': user.email,
            'username': user.username,
            'token': user.token,
        }


class UserSerializer(serializers.ModelSerializer):
    """Handles serialization and deserialization of User objects."""

    # Passwords must be at least 8 characters, but no more than 128 
    # characters. These values are the default provided by Django. We could
    # change them, but that would create extra work while introducing no real
    # benefit, so let's just stick with the defaults.
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'token')

        extra_kwargs = {'token': {'read_only': True}}

        # The `read_only_fields` option is an alternative for explicitly
        # specifying the field with `read_only=True` like we did for password
        # above. The reason we want to use `read_only_fields` here is because
        # we don't need to specify anything else about the field. For the
        # password field, we needed to specify the `min_length` and 
        # `max_length` properties too, but that isn't the case for the token
        # field.

    def update(self, instance, validated_data):
        """Performs an update on a User."""

        # Passwords should not be handled with `setattr`, unlike other fields.
        # This is because Django provides a function that handles hashing and
        # salting passwords, which is important for security. What that means
        # here is that we need to remove the password field from the
        # `validated_data` dictionary before iterating over it.
        password = validated_data.pop('password', None)

        for (key, value) in validated_data.items():
            # For the keys remaining in `validated_data`, we will set them on
            # the current `User` instance one at a time.
            setattr(instance, key, value)

        if password is not None:
            # `.set_password()` is the method mentioned above. It handles all
            # of the security stuff that we shouldn't be concerned with.
            instance.set_password(password)

        # Finally, after everything has been updated, we must explicitly save
        # the model. It's worth pointing out that `.set_password()` does not
        # save the model.
        instance.save()

        return instance


class InvokePasswordReset(serializers.Serializer):

    email = serializers.CharField(max_length=255)

    def validate(self, data):
        email = data.get('email', None)

        # An email is required.
        if email is None:
            raise serializers.ValidationError(
                'An email address is required.'
            )

        user = get_object_or_404(User, email=email)

        # get user token
        token = user.token

        if user is None:
            raise serializers.ValidationError(
                'A user with this email was not found.'
            )

        # call send email method here
        # email_structure(email, token)

        return {
            'email': token
        }
