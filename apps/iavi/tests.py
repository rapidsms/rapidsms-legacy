from rapidsms.tests.scripted import TestScript
from app import App
from models import *
import apps.reporters.app as reporters_app
import apps.tree.app as tree_app
#import apps.i18n.app as i18n_app
from apps.reporters.models import Reporter

class TestApp (TestScript):
    apps = (reporters_app.App, App, tree_app.App )
    fixtures = ["iavi_locations", "uganda_tree", 'test_backend']
    
    
    
    def testRegistration(self):
        reg_script = """
            # base case
            reg_1 > *#En#22#0001#*
            reg_1 < Confirm 0001 Registration is Complete
            reg_1 < Please Enter Your PIN Code
            # we'll deal with pins later
            # bad location id
            reg_2 > *#En##0002#*
            reg_2 < Error 0002.  Unknown location
            reg_2 > *#En#34#0002#*
            reg_2 < Error 0002.  Unknown location 34
            # bad participant ids
            reg_3 > *#En#22##*
            reg_3 < Error .  Id must be 4 numeric digits.  You sent 
            reg_3 > *#En#22#003#*
            reg_3 < Error 003.  Id must be 4 numeric digits.  You sent 003 
            reg_3 > *#En#22#00003#*
            reg_3 < Error 00003.  Id must be 4 numeric digits.  You sent 00003 
            reg_3 > *#En#22#o003#*
            reg_3 < Error o003.  Id must be 4 numeric digits.  You sent o003 
        """
        self.runScript(reg_script)
        
        # this reporter should have been created
        rep1 = IaviReporter.objects.get(alias="0001")
        
        # these ones should not have
        dict = {"alias":"0002"}
        self.assertRaises(IaviReporter.DoesNotExist, IaviReporter.objects.get, **dict)     
        dict = {"alias":"0003"}
        self.assertRaises(IaviReporter.DoesNotExist, IaviReporter.objects.get, **dict)     
        dict = {"alias":"003"}
        self.assertRaises(IaviReporter.DoesNotExist, IaviReporter.objects.get, **dict)     
        
    def testPinEntry(self):
        # this does a base registration/pin combo with everyhing correct
        self._register("pin_1", "0001", "4567")
        
        # get him back and make sure he's got the right pin
        rep = IaviReporter.objects.get(alias="0001")
        self.assertEqual("4567", rep.pin)
        
        pin_script = """
            pin_2 > *#En#22#0002#*
            pin_2 < Confirm 0002 Registration is Complete
            pin_2 < Please Enter Your PIN Code
            # test some poor formats
            pin_2 > 
            pin_2 < Error 0002. Poorly formatted PIN, must be 4 numbers. Please try again.
            pin_2 > 123
            pin_2 < Error 0002. Poorly formatted PIN, must be 4 numbers. Please try again.
            pin_2 > 12345
            pin_2 < Error 0002. Poorly formatted PIN, must be 4 numbers. Please try again.
            pin_2 > 123 4
            pin_2 < Error 0002. Poorly formatted PIN, must be 4 numbers. Please try again.
            pin_2 > 123a
            pin_2 < Error 0002. Poorly formatted PIN, must be 4 numbers. Please try again.
            pin_2 > I don't understand
            pin_2 < Error 0002. Poorly formatted PIN, must be 4 numbers. Please try again.
        """
        self.runScript(pin_script)
        
        # get him back and make sure he doesn't have a pin yet
        rep = IaviReporter.objects.get(alias="0002")
        self.assertEqual(None, rep.pin)
        
        pin_script = """
            pin_3 > *#En#22#0003#*
            pin_3 < Confirm 0003 Registration is Complete
            pin_3 < Please Enter Your PIN Code
            pin_3 > 1234
            # test mismatch
            pin_3 < Please Enter Your PIN Code Again
            pin_3 > 1235
            pin_3 < Error 0003. PINs did not match.
            # todo - implement and test that bit of functionality
            # pin_3 < Error 0003. PINs did not match.  Respond with "iavi set pin" to try again.

        """
        self.runScript(pin_script)
        
        rep = IaviReporter.objects.get(alias="0003")
        self.assertEqual(None, rep.pin)
        
        
    def testAllowEntry(self):
        # tests who is allowed to enter a survey.  for this application
        # only registered users with correctly set PINs are allowed to 
        # participate.  others will be rejected.  
        script = """
            # base case
            rejected_guy > iavi uganda
            rejected_guy < Sorry, only known respondants are allowed to participate in the survey. Please register before submitting.
            # register but don't set a PIN
            rejected_guy > *#En#22#0001#*
            rejected_guy < Confirm 0001 Registration is Complete
            rejected_guy < Please Enter Your PIN Code
            rejected_guy > iavi uganda
            rejected_guy < You must set a PIN before participating in the survey. Respond "iavi set pin" (without quotes) to do this now.
        """
        self.runScript(script)
        
        # register someone with a pin, and make sure only 
        # the PIN works
        self._register("accepted_guy", "0002", "1234")
        script = """
            accepted_guy > iavi uganda
            accepted_guy < Hello, Please Reply With Your PIN
            accepted_guy > 1235
            # I would prefer this response was improved
            accepted_guy < "1235" is not a valid answer. You must enter your 4-digit PIN
            
        """
        self.runScript(script)
    
    def testUgandaBasic(self):
        self._register("ugb_1")
        script = """
            # base case
            ugb_1 > iavi uganda
            ugb_1 < Hello, Please Reply With Your PIN
            ugb_1 > 1234
            ugb_1 < Did you have sex with your main partner in the last 24 hours?
            ugb_1 > yes
            ugb_1 < Did you use a condom?
            ugb_1 > yes
            ugb_1 < Did you have vaginal sex with any other partner in the last 24 hours?
            ugb_1 > no
            ugb_1 < Questionnaire is complete. Thank you.
        """
        self.runScript(script)
        # and again in another language
        self._register(**{"phone":"ugb_2", "id": "0002", "language":"ug"})
        script = """
            # base case
            ugb_2 > iavi uganda
            ugb_2 < Ssebo/Nnyabo Yingiza ennamba yo eye'kyaama mu ssimu yo. Era ennamba eyo giwereze ku kompyuta yaffe.
            ugb_2 > 1234
            ugb_2 < Wetabyeeko mu kikolwa eky'omukwano n'omwagalwawo gw'olinaye mukunoonyereza kuno mu lunaku lumu oluyise?
            ugb_2 > yes
            ugb_2 < Mwakozesezza kondomu?
            ugb_2 > yes
            ugb_2 < Wetabyeeko mu kikolwa ky'omukwano n'omwagalwawo omulala yenna mu lunaku lumu oluyise?
            ugb_2 > no
            ugb_2 < Ebibuuzo bino bikomemye wano. Webale nnyo kuwaayo budde bwo.
        """
        self.runScript(script)
        
    def _register(self, phone="55555", id="0001", pin="1234", location= "22", language="En"):
        script = """
            # base case - everything's all good
            %(phone)s > *#%(language)s#%(location)s#%(id)s#*
            %(phone)s < Confirm %(id)s Registration is Complete
            %(phone)s < Please Enter Your PIN Code
            %(phone)s > %(pin)s
            %(phone)s < Please Enter Your PIN Code Again
            %(phone)s > %(pin)s
            %(phone)s < Thank You. Your PIN Has Been Set
        """ % ({"phone": phone, "id": id, "pin": pin, "language":language, "location": location } )
        self.runScript(script)
        