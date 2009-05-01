from django.db import models

# Create your Django models here, if you need them.
class Pattern(models.Model):
    name = models.CharField(max_length=160)
    regex = models.CharField(max_length=160)

    def __unicode__(self):
        return "%s %s" % (self.name, self.regex)

