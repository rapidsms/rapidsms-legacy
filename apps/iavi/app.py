import rapidsms
import re
from apps.reporters.models import Reporter, Location

class App (rapidsms.app.App):
    def start (self):
        """Configure your app in the start phase."""
        pass

    def parse (self, message):
        """Parse and annotate messages in the parse phase."""
        pass

    def handle (self, message):
        """Add your main application logic in the handle phase."""
        
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
                reporter = Reporter(alias=id, language=language, location=location)
                reporter.save()

                # also attach the reporter to the connection 
                message.persistant_connection.reporter=reporter
                message.persistant_connection.save()
                
                # TODO: also do some tree stuff
                # TODO: initiate pin sequence
                
                # send the response confirmation
                message.respond("Confirm %s Registration is Complete" % id)
                
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
