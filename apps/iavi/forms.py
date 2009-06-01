#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django import forms
from models import *
from apps.reporters.models import Location, Reporter

class IaviReporterForm(forms.Form):

    participant_id = forms.CharField(min_length=3, max_length=3, required=True)
    location = forms.ModelChoiceField(Location.objects.all(), required=True)
    phone = forms.CharField(max_length=15, required=True)
    pin = forms.CharField(min_length=4, max_length=4, required=True)
        
    def clean_pin(self):
        if not self.cleaned_data["pin"].isdigit():
            raise forms.ValidationError("PIN number must be 4 numeric digits.")
        return self.cleaned_data["pin"]

    def clean_participant_id(self):
        if not self.cleaned_data["participant_id"].isdigit():
            raise forms.ValidationError("Participant ID must be 3 numeric digits.")
        return self.cleaned_data["participant_id"]
    
