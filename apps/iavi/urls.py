#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import os
from django.conf.urls.defaults import *
import apps.iavi.views as views

urlpatterns = patterns('',
    url(r'^iavi/?$', views.index),
    url(r'^iavi/compliance/?$', views.compliance),
    url(r'^iavi/data/?$', views.data),
    url(r'^iavi/participants/?$', views.participants),
    url(r'^iavi/participants/(?P<id>\d*)/?$', views.participant_summary),
)
