from rapidsms.webui.utils import render_to_response
from models import *
from datetime import datetime, timedelta

def index(req):
    template_name="iavi/index.html"
    return render_to_response(req, template_name, {})

def compliance(req):
    template_name="iavi/compliance.html"
    reporters = IaviReporter.objects.all()
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
        
    return render_to_response(req, template_name, {"reporters":reporters})

def data(req):
    template_name="iavi/data.html"
    
    seven_days = timedelta(days=7)
    thirty_days = timedelta(days=30)
    tomorrow = datetime.today() + timedelta(days=1)
    kenya_reports = KenyaReport.objects.filter(started__gte=tomorrow-seven_days).order_by("-started")
    uganda_reports = UgandaReport.objects.filter(started__gte=tomorrow-seven_days).order_by("-started")
    return render_to_response(req, template_name, {"kenya_reports":kenya_reports, "uganda_reports":uganda_reports})
    