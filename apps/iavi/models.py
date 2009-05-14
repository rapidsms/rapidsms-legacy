from django.db import models
from apps.reporters.models import Reporter, PersistantConnection 
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
    
    def __unicode__(self):
        return self.connection().identity
        
class StudyParticipant(models.Model):
    """ This represents a participant in the IAVI study. """
    reporter = models.ForeignKey(IaviReporter)
    start_date = models.DateField()
    # if the end_date is blank the study will go indefinitely
    end_date = models.DateField(null=True, blank=True)
    notification_time = models.TimeField()
    
    def __unicode__(self):
        return "%s: %s - %s" % (self.reporter, self.start_date, self.end_date)
    

class TestSession(models.Model):
    TEST_STATUS_TYPES = (
                         ("A", "Active"),
                         ("P", "Passed"),
                         ("F", "Failed")
                         )
    
    date = models.DateTimeField(auto_now_add=True)
    initiator = models.ForeignKey(PersistantConnection)
    tester = models.ForeignKey(IaviReporter)
    tree_session = models.ForeignKey(Session, null=True, blank=True)
    status = models.CharField(max_length=1, choices=TEST_STATUS_TYPES)
    
    def __unicode__(self):
        return "%s --> %s" % (self.initiator, self.status)
    
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
    
    def __unicode__(self):
        return "%s: %s (%s)" % (self.reporter, self.started, self.get_status_display())
    
    
class KenyaReport(Report):
    sex_past_day = models.PositiveIntegerField(null=True, blank=True)
    condoms_past_day = models.PositiveIntegerField(null=True, blank=True)
    
    

class UgandaReport(Report):
    sex_with_partner = models.BooleanField(null=True, blank=True)
    condom_with_partner = models.BooleanField(null=True, blank=True)
    sex_with_other = models.BooleanField(null=True, blank=True)
    condom_with_other = models.BooleanField(null=True, blank=True)
    