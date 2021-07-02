from django.contrib import admin
from .models import *

# Register your models here.
for model in (StudentDatabase, StudentDatabaseAccess):
    admin.site.register(model)

