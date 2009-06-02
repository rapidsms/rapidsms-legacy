from rapidsms.webui.utils import render_to_response
from models import *
from forms import IaviReporterForm
from datetime import datetime, timedelta
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings

def index(req):
    template_name="iavi/index.html"
    return render_to_response(req, template_name, {})

@login_required
def compliance(req):
    template_name="iavi/compliance.html"
    
    user = req.user
    try:
        profile = user.get_profile()
        locations = profile.locations.all()
    except IaviProfile.DoesNotExist:
        # if they don't have a profile they aren't associated with
        # any locations and therefore can't view anything.  Only
        # exceptions are the superusers
        if user.is_superuser:
            locations = Location.objects.all()
        else:
            return render_to_response(req, "iavi/no_profile.html", {"user": user})
    
    reporters = IaviReporter.objects.filter(location__in=locations)
    seven_days = timedelta(days=7)
    thirty_days = timedelta(days=30)
    tomorrow = datetime.today() + timedelta(days=1)
    for reporter in reporters:
        
        all_reports = Report.objects.filter(reporter=reporter)
        last_7 = all_reports.filter(started__gte=tomorrow-seven_days)
        last_30 = all_reports.filter(started__gte=tomorrow-thirty_days)
        
        reporter.all_reports = len(all_reports)
        reporter.all_compliant = len(all_reports.filter(status="F"))
        
        reporter.past_7_reports = len(last_7)
        reporter.past_7_compliant = len(last_7.filter(status="F"))
        
        reporter.past_30_reports = len(last_30)
        reporter.past_30_compliant = len(last_30.filter(status="F"))
        
    return render_to_response(req, template_name, {"reporters":reporters })

@login_required
@permission_required("iavi.can_see_data")
def data(req):
    template_name="iavi/data.html"
    user = req.user
    try:
        profile = user.get_profile()
        locations = profile.locations.all()
    except IaviProfile.DoesNotExist:
        # if they don't have a profile they aren't associated with
        # any locations and therefore can't view anything.  Only
        # exceptions are the superusers
        if user.is_superuser:
            # todo: allow access to everything
            locations = Location.objects.all()
        else:
            return render_to_response(req, "iavi/no_profile.html", {"user": user})
    
    seven_days = timedelta(days=7)
    #thirty_days = timedelta(days=30)
    tomorrow = datetime.today() + timedelta(days=1)
    
    kenya_reports = KenyaReport.objects.filter(started__gte=tomorrow-seven_days).filter(reporter__location__in=locations).order_by("-started")
    uganda_reports = UgandaReport.objects.filter(started__gte=tomorrow-seven_days).filter(reporter__location__in=locations).order_by("-started")
    return render_to_response(req, template_name, {"kenya_reports":kenya_reports, "uganda_reports":uganda_reports})


@login_required
@permission_required("iavi.can_read_users")
def participants(req):
    template_name="iavi/participants.html"
    user = req.user
    try:
        profile = user.get_profile()
        locations = profile.locations.all()
    except IaviProfile.DoesNotExist:
        # if they don't have a profile they aren't associated with
        # any locations and therefore can't view anything.  Only
        # exceptions are the superusers
        if user.is_superuser:
            locations = Location.objects.all()
        else:
            return render_to_response(req, "iavi/no_profile.html", {"user": user})
    
    reporters = IaviReporter.objects.filter(location__in=locations)
    return render_to_response(req, template_name, {"reporters" : reporters })


@login_required
def participant_summary(req, id):
    template_name="iavi/participant_summary.html"
    try:
        reporter = IaviReporter.objects.get(pk=id)
    except IaviReporter.NotFound:
        reporter = None 
    # todo - see if we wnat to put these back in
    kenya_reports = KenyaReport.objects.filter(reporter=reporter).order_by("-started")
    uganda_reports = UgandaReport.objects.filter(reporter=reporter).order_by("-started")
    return render_to_response(req, template_name, {"reporter" : reporter,"kenya_reports":kenya_reports, "uganda_reports":uganda_reports})

@login_required
@permission_required("iavi.can_write_users")
def participant_edit(req, id):
    reporter = None
    if req.method == 'POST': 
        form = IaviReporterForm(req.POST) 
        if form.is_valid():
            # Process the data in form.cleaned_data
            id = req.POST["reporter_id"]
            if not id: 
                # should puke.  should also not be possible through the UI
                raise Exception("Reporter ID not set in form.  How did you get here?")
            reporter = IaviReporter.objects.get(id=id)
            reporter.pin = form.cleaned_data["pin"]
            reporter.location = form.cleaned_data["location"]
            reporter.alias = IaviReporter.get_alias(reporter.location.code, form.cleaned_data["participant_id"])
            reporter.save()
            conn = reporter.connection() 
            conn.identity = form.cleaned_data["phone"]
            conn.save()
            return HttpResponseRedirect('/iavi/participants/%s/' % id) 
    else:
        try:
            reporter = IaviReporter.objects.get(pk=id)
            if reporter.location:
                form = IaviReporterForm(initial={"participant_id" :reporter.study_id, "location" : reporter.location.pk,
                                                 "pin" : reporter.pin, "phone" : reporter.connection().identity } )
            else: 
                form = IaviReporterForm({"participant_id" :reporter.study_id, 
                                         "pin" : reporter.pin, "phone" : reporter.connection().identity } )
        except IaviReporter.NotFound:
            form = IaviReporterForm()

    template_name="iavi/participant_edit.html"
    return render_to_response(req, template_name, {"form" : form, "reporter" : reporter})
