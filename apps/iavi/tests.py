from rapidsms.tests.scripted import TestScript
from app import App
import apps.reporters.app as reporters_app

class TestApp (TestScript):
    apps = (App, reporters_app.App)
    fixtures = ["iavi_locations"]
    
    # define your test scripts here.
    # e.g.:
    #
    # testRegister = """
    #   8005551212 > register as someuser
    #   8005551212 < Registered new user 'someuser' for 8005551212!
    #   8005551212 > tell anotheruser what's up??
    #   8005550000 < someuser said "what's up??"
    # """
    #
    # You can also do normal unittest.TestCase methods:
    #
    # def testMyModel (self):
    #   self.assertEquals(...)
    
    
    testRegistration = """
        # base case
        reg_1 > *#En#22#0001#*
        reg_1 < Confirm 0001 Registration is Complete
        # bad location id
        reg_2 > *#En#34#0002#*
        reg_2 < Error 0002.  Unknown location 34
        # bad participant ids
        
    
    """