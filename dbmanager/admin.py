from django.contrib import admin
from .models import *

# Register your models here.
for model in (AccessToken, ClassDatabase, DatabaseImport, DatabaseProxyUser, DatabaseSnapshot, StudentDatabase, StudentDatabaseAccess):
    admin.site.register(model)

