from django.db import models

# Create your Django models here, if you need them.
class Pattern(models.Model):
    name = models.CharField(max_length=160)
    regex = models.CharField(max_length=160)

    @staticmethod
    def join(patterns):
        '''Joins a set of passed in patterns, assumed to be the result of a 
           ManyToMany field foreign key from some other object'''
        # fix any patterns we just or-ed together so they are the kind of or we want
        # e.g., (\w+)|(\d+) => (\w+|\d+)
        # TODO figure out how to handle non-captured matches
        # e.g., (?:\w+)|(\d+) => (?:\w+)|(\d+) and then zip up tokens correctly
        regex = '|'.join(patterns.values_list('regex', flat=True))
        return regex.replace(')|(', '|')


    def __unicode__(self):
        return "%s %s" % (self.name, self.regex)

