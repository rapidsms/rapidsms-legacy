from django.db import models
from apps.reporters.models import Reporter
from apps.tree.models import Session

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
    STATUS_TYPES = (
        ('C', 'Canceled'),
        ('A', 'Active'),
        ('F', 'Finished'),
    )

    reporter = models.ForeignKey(IaviReporter)
    session = models.ForeignKey(Session)
    started = models.DateTimeField()
    completed = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS_TYPES)
    
    @classmethod
    def pending_sessions(klass):
        return klass.objects.filter(completed=None)
    
    
class KenyaReport(Report):
    sex_past_day = models.PositiveIntegerField(null=True, blank=True)
    condoms_past_day = models.PositiveIntegerField(null=True, blank=True)
    

class UgandaReport(Report):
    sex_with_partner = models.BooleanField(null=True, blank=True)
    condom_with_partner = models.BooleanField(null=True, blank=True)
    sex_with_other = models.BooleanField(null=True, blank=True)
    condom_with_other = models.BooleanField(null=True, blank=True)
    