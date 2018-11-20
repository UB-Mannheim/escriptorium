from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    fields = models.ManyToManyField('ResearchField', blank=True)


class ResearchField(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name

    
# class AccessLevel(models.Model):
#     ACCESS_TEAM = 1
#     # ACCESS_APP = 2 ? i don't think it's needed ?
#     ACCESS_GLOBAL = 2
#
#     access_level = models.TinyIntegerField()
#
#     class Meta:
#         abstract = True
