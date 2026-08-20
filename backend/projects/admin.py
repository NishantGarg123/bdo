from django.contrib import admin
from .models import Project, ProjectIssue, ProjectFAQ

admin.site.register(Project)
admin.site.register(ProjectIssue)
admin.site.register(ProjectFAQ)
