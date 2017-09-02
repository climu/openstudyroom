from django.contrib import admin
from .models import Community
# Register your models here.
mymodels = [Community]

admin.site.register(mymodels)
