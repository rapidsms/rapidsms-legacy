from django.db import models
from apps.reporters.models import Reporter

class IaviReporter(Reporter):
    """This model represents a reporter in IAVI.  They are an extension of
       the basic reporters, but also have PIN numbers"""  
    pin = models.CharField(max_length=4, null=True, blank=True)
    
    @property
    def study_id(self):
        # use some implicit knowledge about how we're storing the
        # aliases to get these.
        if "-" in self.alias:
            return self.alias.split('-')[1]
        return None
        
    @classmethod
    def get_alias(klass, location, study_id):
        return location + "-" + study_id