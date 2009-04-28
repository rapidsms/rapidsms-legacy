from rapidsms.tests.scripted import TestScript
from app import App
import apps.reporters.app as reporters_app
import apps.tree.app as tree_app
from apps.reporters.models import Reporter

class TestApp (TestScript):
    apps = (reporters_app.App, tree_app.App, App )
    fixtures = ["iavi_locations", "uganda_tree", 'test_backend']
    
    
    
    def testRegistration(self):
        reg_script = """
            # base case
            reg_1 > *#En#22#0001#*
            reg_1 < Confirm 0001 Registration is Complete
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
        rep1 = Reporter.objects.get(alias="0001")
        
        # these ones should not have
        dict = {"alias":"0002"}
        self.assertRaises(Reporter.DoesNotExist, Reporter.objects.get, **dict)     
        dict = {"alias":"0003"}
        self.assertRaises(Reporter.DoesNotExist, Reporter.objects.get, **dict)     
        dict = {"alias":"003"}
        self.assertRaises(Reporter.DoesNotExist, Reporter.objects.get, **dict)     
        
    def testUgandaBasic(self):
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
        