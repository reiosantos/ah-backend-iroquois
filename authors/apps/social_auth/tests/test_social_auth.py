import json
import os
from unittest import TestCase

from django.test import Client


class Tests(TestCase):

    def setUp(self):
        self.test_client = Client()
        self.user_with_invalid_social_token = {
            "user": {
                "auth_token": "fake_fb_twitter_or_google_token"
            }
        }

        self.user_with_expired_google_token = {
            "user": {
                "auth_token": os.getenv('GOOGLE_EXPIRED_TOKEN')
            }
        }

        self.user_with_expired_facebook_token = {
            "user": {
                "auth_token": os.getenv('FACEBOOK_EXPIRED_TOKEN')
            }
        }

        self.facebook_debug_token = {
            "user": {
                "auth_token": os.getenv('FACEBOOK_DEBUG_TOKEN')
            }
        }

        self.google_debug_token = {
            "user": {
                "auth_token": os.getenv('GOOGLE_DEBUG_TOKEN'),
                "refresh_token": os.getenv('GOOGLE_DEBUG_REFRESH_TOKEN')
            }
        }

    def test_signup_with_invalid_fb_token(self):
        """ test if a user can signup with wrong facebook token """

        response = self.test_client.post("/api/social/auth/facebook/", data=json.dumps(
                self.user_with_invalid_social_token), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['auth_token'], [
            'The token is either invalid or expired. Please login again.'])

    def test_signup_with_invalid_google_token(self):
        """ test if a user can signup with wrong google token """

        response = self.test_client.post(
            "/api/social/auth/google/", data=json.dumps(
                self.user_with_invalid_social_token), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['auth_token'], [
            'The token is either invalid or expired. Please login again.'])

    def test_signup_with_expired_google_token(self):
        """ test if a user can signup with correct google token """

        response = self.test_client.post(
            "/api/social/auth/google/", data=json.dumps(
                self.user_with_expired_google_token), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['auth_token'], [
            'The token is either invalid or expired. Please login again.'])

    def test_signup_with_expired_facebook_token(self):
        """ test if a user can signup with correct google token """

        response = self.test_client.post(
            "/api/social/auth/facebook/", data=json.dumps(
                self.user_with_expired_facebook_token), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['auth_token'], [
            'The token is either invalid or expired. Please login again.'])

    def test_signup_with_valid_google_token(self):
        """ test if a user can signup with correct google token """

        response = self.test_client.post(
            "/api/social/auth/google/", data=json.dumps(
                self.google_debug_token), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('auth_token', response.json())

        # user already exists
        response = self.test_client.post(
            "/api/social/auth/google/", data=json.dumps(
                self.google_debug_token), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('auth_token', response.json())

    def test_signup_with_valid_facebook_token(self):
        """ test if a user can signup with correct fb token """

        response = self.test_client.post(
            "/api/social/auth/facebook/", data=json.dumps(
                self.facebook_debug_token), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())
        self.assertIn('auth_token', response.json())

