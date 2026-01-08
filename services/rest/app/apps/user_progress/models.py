from django.db import models

from apps.accounts.models import User


class UserResource(models.Model):
    class Meta:
        managed = False
        db_table = "user_resources"
        verbose_name = "Ресурсы пользователя"
        verbose_name_plural = "Ресурсы пользователей"

    id = models.ForeignKey(User, primary_key=True, on_delete=models.PROTECT)
    scraps = models.IntegerField(default=1000, blank=False, null=False)
    wood = models.IntegerField(default=1000, blank=False, null=False)
    kegs = models.IntegerField(default=3, blank=False, null=False)
    big_kegs = models.IntegerField(default=1, blank=False, null=False)
    chests = models.IntegerField(default=0, blank=False, null=False)
    keys = models.IntegerField(default=3, blank=False, null=False)
