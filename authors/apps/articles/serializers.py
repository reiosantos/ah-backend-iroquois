"""
Serializer classes for articles
"""
from rest_framework import serializers

from authors.apps.articles.exceptions import NotFoundException
from authors.apps.articles.models import Article
from authors.apps.articles.utils import get_date
from authors.apps.authentication.models import User
from authors.apps.authentication.serializers import UserSerializer


class ArticleSerializer(serializers.ModelSerializer):
    """
    Define action logic for an article
    """

    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    slug = serializers.CharField(read_only=True)

    def create(self, validated_data):
        """
        :param validated_data:
        :return:
        """
        return Article.objects.create(**validated_data)

    @staticmethod
    def validate_for_update(data: dict, user, slug):
        """
        :param data:
        :param user:
        :param slug:
        :return:
        """
        try:
            article = Article.objects.filter(slug__exact=slug, author__exact=user)
            if article.count() > 0:
                article = article[0]
            else:
                raise Article.DoesNotExist

        except Article.DoesNotExist:
            raise NotFoundException("Article is not found for update.")

        required = {"title", "description", "body"}
        keys = set(data.keys())

        missing = required.difference(keys)

        for val in missing:
            data.update({val: article.__getattribute__(val)})

        data.update({
            "author": user.pk,
            "updated_at": get_date()
        })
        return article, data

    def to_representation(self, instance):
        """
        formats serializer display response
        :param instance:
        :return:
        """
        response = super().to_representation(instance)
        response['author'] = UserSerializer(instance.author).data
        return response

    class Meta:
        """
        class behaviours
        """
        model = Article
        # noinspection SpellCheckingInspection
        fields = ('slug', 'title', 'description', 'body', 'created_at',
                  'updated_at', 'favorited', 'favorites_count', 'photo_url', 'author')
