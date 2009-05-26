#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


from django.db import connection

from django import template
register = template.Library()


class QueryLogVarsNode(template.Node):
    def render(self, context):
        context["queries"] = connection.queries
        return "<!-- loaded query log vars -->"


@register.tag
def query_log_vars(parser, token):
    args = token.split_contents()
    tag_name = args.pop(0)
    
    return QueryLogVarsNode(*args)
