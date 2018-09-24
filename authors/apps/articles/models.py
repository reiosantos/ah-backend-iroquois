"""
class to declare an article
model. To be used for all articles
"""

from django.db import models
from django.db.models import Avg
from django.utils import timezone

from authors.apps.articles.filters import ArticleManager
from authors.apps.articles.utils import generate_slug
from authors.apps.authentication.models import User


class Tag(models.Model):
    """
    Tag for the article(s). Every tag has unique tag_name.
    """
    tag_name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.tag_name


class Article(models.Model):
    """
    A model for an article
    """
    objects = ArticleManager()

    slug = models.SlugField(max_length=100, unique=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles", null=True)

    title = models.CharField(max_length=255, null=False, blank=False,
                             error_messages={"required": "Write a short title for your article."})

    description = models.TextField(null=False, blank=False,
                                   error_messages={"required": "A description of your post is required."})

    body = models.TextField(null=False, blank=False,
                            error_messages={"required": "You cannot submit an article without body."})

    created_at = models.DateTimeField(auto_created=True, auto_now=False, default=timezone.now)

    updated_at = models.DateTimeField(auto_created=True, auto_now=False, default=timezone.now)

    favorites_count = models.IntegerField(default=0)

    photo_url = models.CharField(max_length=255, null=True)

    tags = models.ManyToManyField(Tag, related_name='article_tag')

    def __str__(self):
        """
        :return: string
        """
        return self.title

    def save(self, *args, **kwargs):
        """
        override default save() to generate slug
        :param args:
        :param kwargs:
        """
        self.slug = generate_slug(Article, self)

        super(Article, self).save(*args, **kwargs)

    @property
    def average_rating(self):
        """
        calculates the average rating of the article.
        :return:
        """
        ratings = self.scores.all().aggregate(score=Avg("score"))
        return float('%.2f' % (ratings["score"] if ratings['score'] else 0))

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['-created_at', 'author']


class Rating(models.Model):
    """
    Model for creating article ratings or votes
    """
    article = models.ForeignKey(Article, related_name="scores", on_delete=models.CASCADE)
    rated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scores", null=True)
    rated_at = models.DateTimeField(auto_created=True, default=timezone.now, auto_now=False)
    score = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        ordering = ('-score',)


class Comments(models.Model):

    article = models.ForeignKey(Article, related_name='comments', on_delete=models.CASCADE, blank=True, null=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE)

    body = models.TextField(null=False, blank=False, error_messages={"required": "You cannot submit without a comment."})

    created_at = models.DateTimeField(auto_created=True, auto_now=False, default=timezone.now)

    def __str__(self):
        """
        :return: string
        """
        return self.body

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['-created_at']


class Replies(models.Model):

    comment = models.ForeignKey(Comments, related_name='replies', on_delete=models.CASCADE, blank=True, null=True)

    author = models.ForeignKey(User, related_name='replies',  on_delete=models.CASCADE, blank=True , null=True)

    content = models.TextField(null=False, blank=False,
                            error_messages={"required": "You cannot submit without a reply."})

    created_at = models.DateTimeField(auto_created=True, auto_now=False, default=timezone.now)

    def __str__(self):
        """
        :return: string
        """
        return self.content

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['-created_at']

