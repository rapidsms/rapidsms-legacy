import rapidsms
import re
from apps.reporters.models import Reporter, Location
from models import *
from apps.i18n.utils import get_translation as _
from apps.i18n.utils import get_language
from strings import strings

class App (rapidsms.app.App):
    def start (self):
        """Configure your app in the start phase."""
        # we have to register our functions with the tree app
        tree_app = self.router.get_app("tree")
        tree_app.register_custom_transition("validate_pin", validate_pin)
        self.pending_pins = { }
        
    def parse (self, message):
        """Parse and annotate messages in the parse phase."""
        pass

    def handle (self, message):
        # there are three things this app deals with primarily:
        # registration, pin setup, and testing
        
        # but we'll also use it to circumvent some logic in the tree
        # app with a few custom codes.
        if message.text.lower() == "iavi uganda" or message.text.lower() == "iavi kenya":
            # if they are allowed to participate, return false so 
            # that the message propagates to the tree app.  If they
            # aren't this will come back as handled and the tree app
            # will never see it.  
            # ASSUMES ORDERING OF APPS AND THAT THIS IS BEFORE TREE
            return not self._allowed_to_participate(message)
        
        # we'll be using the language in all our responses so
        # keep it handy
        language = get_language(message.persistant_connection)
        
        # check pin conditions and process if they match
        if message.reporter and message.reporter.pk in self.pending_pins:
            return self._process_pin(message)
            
        # registration block
        # first make sure the string starts and ends with the *# - #* combination
        match = re.match(r"^\*\#(.*?)\#\*$", message.text)
        if match:
            self.info("Message matches! %s", message)
            body_groups = match.groups()[0].split("#")
            if len(body_groups) == 3:
                # assume this is the registration format
                # this is the (extremely ugly) format of registration
                # *#<Country/Language Group>#<Site Number>#<Last 4 Digits of Participant ID>#*
                
                language, site, id = body_groups
                # validate the format of the id, existence of location
                if not re.match(r"^\d{4}$", id):
                    message.respond("Error %s.  Id must be 4 numeric digits.  You sent %s" % (id, id))
                    return True
                try:
                    location = Location.objects.get(code=site)
                except Location.DoesNotExist:
                    message.respond("Error %s.  Unknown location %s" % (id, site))
                    return True
                # TODO: validate the language
                
                # create the reporter object for this person 
                # TODO: what if the id already exists?  currently blows up
                reporter = IaviReporter(alias=id, language=language, location=location)
                reporter.save()
                
                # also attach the reporter to the connection 
                message.persistant_connection.reporter=reporter
                message.persistant_connection.save()
                
                # TODO: also do some tree stuff
                # TODO: initiate pin sequence
                
                # send the response confirmation
                message.respond("Confirm %s Registration is Complete" % id)
                
                # also send the PIN request and add this user to the 
                # pending pins
                self.pending_pins[reporter.pk] = None
                message.respond(_(strings["pin_request"], language))
            elif len(body_groups)== 4:
                # assume this is the testing format
                # this is the (extremely ugly) format of testing
                # *#8377#<Country/Language Group>#<Site Number>#<Last 4 Digits of Participant ID>#*
                # TODO: implement testing
                
                code, language, site, id = body_groups
                message.respond("Sorry, we haven't made the testing feature yet!")
                return True
        else:
            self.info("Message doesn't match. %s", message)
            # this is okay.  one of the other apps may yet pick it up
            
    
    def cleanup (self, message):
        """Perform any clean up after all handlers have run in the
           cleanup phase."""
        pass

    def outgoing (self, message):
        """Handle outgoing message notifications."""
        pass

    def stop (self):
        """Perform global app cleanup when the application is stopped."""
        pass
    
    def _allowed_to_participate(self, message):
        if message.reporter:
            iavi_reporter = IaviReporter.objects.get(pk=message.reporter.pk)
            if iavi_reporter.pin:
                return True
            else:
                message.respond(_(strings["rejection_no_pin"], get_language(message.persistant_connection)))
        else:
            message.respond(_(strings["rejection_unknown_user"], get_language(message.persistant_connection)))
        return False
            
    def _process_pin(self, message):
        language = get_language(message.persistant_connection)
        incoming_pin = message.text.strip()
        if self.pending_pins[message.reporter.pk]:
            # this means it has already been set once 
            # check if they are equal and if so save
            pending_pin = self.pending_pins.pop(message.reporter.pk)
            if incoming_pin == pending_pin:
                # success!
                reporter = IaviReporter.objects.get(pk=message.reporter.pk)
                reporter.pin = pending_pin
                reporter.save()
                message.respond(_(strings["pin_set"], language))
            else:
                # oops they didn't match.  send a failure string
                message.respond(_(strings["pin_mismatch"], language) % {"alias": message.reporter.alias})
        else:
            # this is their first try.  make sure 
            # it's 4 numeric digits and if so ask for confirmation
            if re.match(r"^(\d{4})$", incoming_pin):
                self.pending_pins[message.reporter.pk] = incoming_pin
                message.respond(_(strings["pin_request_again"], language))
            else:
                # bad format.  send a failure string and prompt again
                message.respond(_(strings["bad_pin_format"], language) % {"alias": message.reporter.alias})
        return True
    

def validate_pin(msg):
    rep = IaviReporter.objects.get(pk=msg.reporter.pk)
    return msg.text == rep.pin
    
