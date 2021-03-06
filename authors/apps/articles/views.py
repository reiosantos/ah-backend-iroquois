"""
Views for articles
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from authors.apps.articles.exceptions import (
    NotFoundException, InvalidQueryParameterException)
from authors.apps.articles.models import Article, Tag, ArticleReport
from authors.apps.articles.renderer import ArticleJSONRenderer, TagJSONRenderer
from authors.apps.articles.serializers import (RatingSerializer, ArticleReportSerializer,
                                               ArticleSerializer, PaginatedArticleSerializer, TagSerializer)
from authors.apps.articles.permissions import IsSuperuser

from .preference_utils import call_preference_helpers

from .views_extra import *


# noinspection PyUnusedLocal,PyMethodMayBeStatic


class ArticleViewSet(ViewSet):
    """
    Article ViewSet
    Handles all request methods
    Post, Get, Put, Delete
    """
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ArticleJSONRenderer,)
    serializer_class = ArticleSerializer
    lookup_field = "slug"

    def list(self, request):
        """
        returns a list of all articles
        :param request:
        :return:
        """
        limit = request.query_params.get("limit", 20)
        offset = request.query_params.get("offset", 0)

        def to_int(val):
            """
            convert param to positive integer
            :param val:
            :return:
            """
            return int(val) if int(val) > 0 else -int(val)

        try:
            limit = to_int(limit)
            offset = to_int(offset)
        except ValueError:
            raise InvalidQueryParameterException()

        queryset = Article.objects.search(request.query_params)

        if queryset.count() > 0:
            queryset = queryset[offset:]

        data = self.serializer_class(queryset, many=True, context={
                                     'request': request}).data

        pager_class = PaginatedArticleSerializer()
        pager_class.page_size = limit

        return Response(pager_class.get_paginated_response(pager_class.paginate_queryset(data, request)))

    def retrieve(self, request, slug=None):
        """
        returns a specific article based on primary key
        :param slug:
        :param request:
        :return:
        """
        queryset = Article.objects.all()
        article = get_object_or_404(queryset, slug=slug)
        serializer = self.serializer_class(
            article, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        """
        creates an article
        :param request:
        :return:
        """
        article = request.data.get("article", {})
        article.update({"author": request.user.pk})
        serializer = self.serializer_class(
            data=article, context={'request': request})
        serializer.tags = article.get("tags", [])
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, slug=None):
        """
        update a specific article
        :param request:
        :param slug:
        :return:
        """
        article_update = request.data.get("article", {})

        article, article_update = self.serializer_class.validate_for_update(
            article_update, request.user, slug)

        serializer = self.serializer_class(
            data=article_update, context={'request': request})
        serializer.instance = article
        serializer.tags = article_update.get("tags", [])
        serializer.is_valid(raise_exception=True)

        serializer.update(article, serializer.validated_data)

        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    def destroy(self, request, slug=None):
        """
        delete an article
        :param request:
        :param slug:
        :return:
        """

        try:
            article = Article.objects.filter(
                slug__exact=slug, author__exact=request.user)
            if article.count() > 0:
                article = article[0]
            else:
                raise Article.DoesNotExist

            article.delete()
        except Article.DoesNotExist:
            raise NotFoundException("Article is not found for update.")
        return Response({"detail": "Article has been deleted."}, status=status.HTTP_204_NO_CONTENT)


class RatingsView(APIView):
    """
    implements methods to handle ratings requests
    """
    serializer_class = RatingSerializer
    permission_classes = (IsAuthenticated,)
    renderer_classes = (ArticleJSONRenderer,)

    def post(self, request, slug=None):
        """
        :param slug:
        :param request:
        """
        data = self.serializer_class.update_request_data(
            request.data.get("article", {}), slug, request.user)

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class FavoriteArticlesAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ArticleSerializer

    def post(self, request, article_slug=None):
        profile = self.request.user.userprofile
        serializer_context = {'request': request}

        try:
            article = Article.objects.get(slug=article_slug)
            if article.author == request.user:
                return Response({'error': 'You cannot favorite your own article'}, status=status.HTTP_400_BAD_REQUEST)
        except Article.DoesNotExist:
            raise NotFound('An article with this slug was not found.')

        if profile.has_favorited(article):
            return Response({'message': 'You have already favorited this article'}, status=status.HTTP_400_BAD_REQUEST)

        profile.favorite(article)
        article.favorites_count += 1
        article.save()

        serializer = self.serializer_class(article, context=serializer_context)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, article_slug=None):
        profile = self.request.user.userprofile
        serializer_context = {'request': request}

        try:
            article = Article.objects.get(slug=article_slug)
        except Article.DoesNotExist:
            raise NotFound('An article with this slug was not found.')

        if not profile.has_favorited(article):
            return Response({'message': 'This article is not in your favorites list'},
                            status=status.HTTP_400_BAD_REQUEST)

        profile.unfavorite(article)
        article.favorites_count = article.favorites_count - 1 if article.favorites_count > 0 else 0
        article.save()

        serializer = self.serializer_class(article, context=serializer_context)

        return Response(serializer.data, status=status.HTTP_200_OK)


class TagViewSet(viewsets.ModelViewSet):
    """Handles creating, reading, updating and deleting tags"""
    queryset = Tag.objects.all()
    permission_classes = (IsSuperuser, IsAuthenticated)
    serializer_class = TagSerializer
    renderer_classes = (TagJSONRenderer, )

    @staticmethod
    def make_snake_style(request_data):
        snake_style = request_data.data.get(
            "tag_name").replace(" ", "_").lower()
        request_data.data.update({"tag_name": snake_style})
        return request_data

    def create(self, request, *args, **kwargs):
        self.make_snake_style(request)

        return super().create(request)

    def update(self, request, *args, **kwargs):
        self.make_snake_style(request)
        return super().update(request)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "tag deleted successfuly"}, status=status.HTTP_204_NO_CONTENT)


class ArticleReportView(APIView):
    """
    Handles creating, reading, updating and deleting reports
    made on an article
    """
    permission_classes = (IsAuthenticated, )
    serializer_class = ArticleReportSerializer

    def post(self, request, slug):
        """This method handles post requests when reporting an article."""
        message = None
        if "report_message" in request.data and request.data["report_message"].strip():
            article = ArticleSerializer.get_article_object(slug)
            user = request.user.id
            message = request.data["report_message"]
            data = {"user": user, "article": article.id,
                    "report_message": message}
            serializer = self.serializer_class(data=data)

            serializer.is_valid()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response({"detail": "A report message is required"},
                        status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, slug=None):
        """This method returns reports made on an article."""
        article_reports = None
        serializer = None
        if request.user.is_superuser:
            if slug:

                article = ArticleSerializer.get_article_object(slug)
                article_reports = ArticleReport.objects.filter(
                    article=article.id)
                serializer = self.serializer_class(article_reports, many=True)
                return Response({"reports": serializer.data}, status=status.HTTP_200_OK)

            article_reports = ArticleReport.objects.all()
            serializer = self.serializer_class(article_reports, many=True)
            return Response({"reports": serializer.data}, status=status.HTTP_200_OK)
        return Response({"detail": "permission denied, you do not have access rights."},
                        status=status.HTTP_403_FORBIDDEN)


class LikeOrUnlikeAPIView(APIView):
    """ Implement liking an article """

    permission_classes = (IsAuthenticated,)

    def post(self, request, slug):
        return call_preference_helpers("like", slug, request.user)


class DislikeOrUndislikeAPIView(LikeOrUnlikeAPIView):
    """ Implement disliking an article """

    def post(self, request, slug):
        return call_preference_helpers("dislike", slug, request.user)


