#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import rapidsms
from apps.contacts.models import contact_from_message

#
# NEARLY a pure data-model 'project'
# 
# App class makes sure inbound messages have a Contact
# See models.py for meat.
#

class App(rapidsms.app.App):
    def parse(self, msg):
        msg.sender = contact_from_message(msg,self.router)
        txt = 'Added Contact to msg: %r,%s with connections: %s'
        self.info(txt, 
                  msg.sender, msg.sender.locale,
                  ', '.join([repr(c) for c \
                            in msg.sender.channel_connections.all()]))
