from django.db import models
from apps.reporters.models import Reporter

class IaviReporter(Reporter):
    """This model represents a reporter in IAVI.  They are an extension of
       the basic reporters, but also have PIN numbers"""  
    pin = models.CharField(max_length=4, null=True, blank=True)
    registered = models.DateTimeField()
    
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
    

class Report(models.Model):
    reporter = models.ForeignKey(IaviReporter)
    started = models.DateTimeField()
    completed = models.DateTimeField(null=True, blank=True)
    
class KenyaReport(Report):
    sex_past_day = models.PositiveIntegerField(null=True, blank=True)
    condoms_past_day = models.PositiveIntegerField(null=True, blank=True)
    

class UgandaReport(Report):
    sex_with_partner = models.BooleanField(null=True, blank=True)
    condom_with_partner = models.BooleanField(null=True, blank=True)
    sex_with_other = models.BooleanField(null=True, blank=True)
    condom_with_other = models.BooleanField(null=True, blank=True)
    