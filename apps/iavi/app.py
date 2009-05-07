import rapidsms
import re
from rapidsms.connection import Connection 
from rapidsms.message import Message
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
        tree_app.register_custom_transition("validate_pin", self.validate_pin)
        tree_app.register_custom_transition("validate_1_to_19", self.validate_1_to_19)
        tree_app.register_custom_transition("validate_num_times_condoms_used", self.validate_num_times_condoms_used)
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
                # *#<Country/Language Group>#<Site Number>#<Last 3 Digits of Participant ID>#*
                
                language, site, id = body_groups
                # validate the format of the id, existence of location
                if not re.match(r"^\d{3}$", id):
                    message.respond("Error %s. Id must be 3 numeric digits. You sent %s" % (id, id))
                    return True
                try:
                    location = Location.objects.get(code=site)
                except Location.DoesNotExist:
                    message.respond("Error %s. Unknown location %s" % (id, site))
                    return True
                
                # TODO: validate the language?
                
                # user ids are unique per-location so use location-id
                # as the alias
                alias = IaviReporter.get_alias(location.code, id)
                
                # make sure this isn't a duplicate alias
                if len(IaviReporter.objects.filter(alias=alias)) > 0:
                    message.respond(_(strings["already_registered"], language) % {"alias": id, "location":location.code})
                    return True
                
                # create the reporter object for this person 
                reporter = IaviReporter(alias=alias, language=language, location=location)
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
                
            elif len(body_groups)== 4 and body_groups[0] == "8377":
                # this is the testing format
                # this is the (extremely ugly) format of testing
                # *#8377#<Country/Language Group>#<Site Number>#<Last 4 Digits of Participant ID>#*
                # TODO: implement testing
                
                code, language, site, id = body_groups
                alias = IaviReporter.get_alias(site, id)
                try: 
                    user = IaviReporter.objects.get(alias=alias)
                    user_conn = user.connection()
                    if user_conn:
                        db_backend = user_conn.backend
                        # we need to get the real backend from the router 
                        # to properly send it 
                        real_backend = self.router.get_backend(db_backend.slug)
                        if real_backend:
                            connection = Connection(real_backend, user_conn.identity)
                            text = self._get_tree_sequence(language)
                            if not text:
                                message.respond(_(strings["unknown_language"],language) % {"language":language, "alias":id})
                            else:
                                start_msg = Message(connection, text)
                                self.router.incoming(start_msg)
                        else:
                            self.error("Can't find backend %s.  Messages will not be sent", connection.backend.slug)
                    else:
                        self.error("Can't find connection %s.  Messages will not be sent", connection)
                except IaviReporter.DoesNotExist:
                    message.respond(_(strings["unknown_user"], language) % {"alias":id})
                return True
            else:
                message.respond(_(strings["unknown_format"], get_language(message.persistant_connection)))
                
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
        reporter = IaviReporter.objects.get(pk=message.reporter.pk)
        if self.pending_pins[reporter.pk]:
            # this means it has already been set once 
            # check if they are equal and if so save
            pending_pin = self.pending_pins.pop(reporter.pk)
            if incoming_pin == pending_pin:
                # success!
                reporter.pin = pending_pin
                reporter.save()
                message.respond(_(strings["pin_set"], language))
            else:
                # oops they didn't match.  send a failure string
                message.respond(_(strings["pin_mismatch"], language) % {"alias": reporter.study_id})
        else:
            # this is their first try.  make sure 
            # it's 4 numeric digits and if so ask for confirmation
            if re.match(r"^(\d{4})$", incoming_pin):
                self.pending_pins[reporter.pk] = incoming_pin
                message.respond(_(strings["pin_request_again"], language))
            else:
                # bad format.  send a failure string and prompt again
                message.respond(_(strings["bad_pin_format"], language) % {"alias": reporter.study_id})
        return True
    
    def _get_tree_sequence(self, language):
        if re.match(r"^(ug[a-z]*)$", language, re.IGNORECASE):
            return "iavi uganda"
        elif re.match(r"^(ke[a-z]*|sw[a-z]*)$", language, re.IGNORECASE):
            return "iavi kenya"
        else:
            return None
    
    # this region is for the validation logic
    
    def validate_pin(self, msg):
        rep = IaviReporter.objects.get(pk=msg.reporter.pk)
        return msg.text == rep.pin
    
    # we need to save these in order to validate the other
    sex_answers = {}
    
    def validate_1_to_19(self, msg):
        value = msg.text.strip()
        if value.isdigit():
            if 0 < int(value) < 20:
                self.sex_answers[msg.reporter.pk] = int(value)
                return True
        return False
    
    def validate_num_times_condoms_used(self, msg):
        value = msg.text.strip()
        if value.isdigit():
            old_value = self.sex_answers.get(msg.reporter.pk)
            if not old_value:
                # this should never happen unless we were
                # interrupted between questions. we could
                # look this up in the DB but for now we'll
                # be dumb.  
                # TODO: do this for real from the DB
                old_value = 20
            if 0 <= int(value) <= old_value:
                self.sex_answers.pop(msg.reporter.pk)
                return True
        return False
        
