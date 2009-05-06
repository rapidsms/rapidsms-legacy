#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.contrib import admin
from apps.patterns.models import *

class PatternAdmin(admin.ModelAdmin):
    list_display = ['name', 'regex']

admin.site.register(Pattern, PatternAdmin)
