from django.db import models



# Create your models here.

class Status(models.Model):
    curr_iteration = models.IntegerField()
    curr_route_number = models.IntegerField()
  
    