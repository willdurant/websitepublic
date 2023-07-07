from django.db import models
from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractUser
import requests
import pandas as pd
import polars as pl


class User(AbstractUser):
    pass


# Create your models here.
class Energy(models.Model):
    ENERGY_TYPE_CHOICES = [("GAS", "Gas"), ("ELEC", "Electricty")]
    date = models.DateField()
    energy_type = models.CharField(choices=ENERGY_TYPE_CHOICES, max_length=4)
    interval_start = models.TimeField()
    interval_end = models.TimeField()
    consumption = models.FloatField()
    cost = models.FloatField()
