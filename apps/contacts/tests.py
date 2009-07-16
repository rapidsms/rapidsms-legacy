from rapidsms.tests.scripted import TestScript
from rapidsms.tests.harness import MockRouter, MockBackend
from rapidsms.connection import Connection
from rapidsms.message import Message
from app import App
import apps.contacts.app as contacts_app
from apps.contacts.models import *
from apps.nodegraph.models import NodeSet
from time import sleep

# helpers
def _contact(name, *grps):
    u=Contact(debug_id=name)
    u.save()
    for grp in grps:
        u.add_to_parent(grp)

    return u

def _group(name, *children):
    g=NodeSet(debug_id=name)
    g.save()
    g.add_children(*children)
    return g

class Worker(Contact):
    pass

class StealWorker(Worker):
    pass

class TestApp (TestScript):
    apps = (App, contacts_app.App)
 
    # some globals for all tests
    m_nodes=None
    w_nodes=None
    m_group=None
    w_group=None
    people_group=None
    
    m_names = ['matt','larry','jim','joe','mohammed']
    w_names = ['jen','julie','mary','fatou','sue']
    girl_names = ['jennie','susie']
    boy_names = ['johnny', 'jimmie']

    def setUp(self):
        TestScript.setUp(self)
            
        # make some nodes and graphs
        # imagine this is users and groups for clarity
        self.m_nodes = [_contact(n) for n in self.m_names]
        self.w_nodes = [_contact(n) for n in self.w_names]
        self.girl_nodes = [_contact(n) for n in self.girl_names]
        self.boy_nodes = [_contact(n) for n in self.boy_names]
        self.m_group = _group('men',*self.m_nodes)
        self.w_group = _group('women',*self.w_nodes)
        self.g_group = _group('girls',*self.girl_nodes)
        self.g_group.add_to_parent(self.w_group)
        self.b_group = _group('boys',*self.boy_nodes)
        self.b_group.add_to_parent(self.m_group)

        self.people_group = _group('people', self.m_group, self.w_group)

        self.all_groups = [
                        self.people_group,
                        self.b_group,
                        self.g_group,
                        self.m_group,
                        self.w_group
                        ]
        
        self.router=MockRouter()
        self.backend=MockBackend(self.router)
        self.uid0='4156661212'
        self.uid1='6175551212'
        self.uid2='6195551212'
        
    def tearDown(self):
        all_nodes=set()
        for g in self.all_groups:
            all_nodes.update(g.flatten())
        for n in all_nodes:
            n.delete()
            
        for g in self.all_groups:
            g.delete()
    
    def testLocales(self):
        print "\n\nLocale Test..."
        # TODO: Make these all asserts
        en='en_US'
        fr='fr_CA@euro'
        wo='wo_SN'
        es='es_AR'

        p1=self.m_nodes[0]
        p2=self.w_nodes[1]

        p1.locale=fr
        p1.save()
        self.assertTrue(p1.locale==fr)
        p1.locale=en
        self.assertTrue(p1.locale==en)
        p2.locale=wo
        p2.save()
        self.assertTrue(p1.locale==en and p2.locale==wo)

    def testDowncast(self):
        sw=StealWorker(debug_id='bob builder')
        sw.save()
        workers=NodeSet(debug_id='workers')
        workers.save()
        sw.add_to_parent(workers)

        for o in workers.flatten(klass=Worker):
            self.assertTrue(o.__class__==Worker)
            
        for o in workers.flatten(klass=StealWorker):
            self.assertTrue(o.__class__==StealWorker)

    def testChannelConnectionFromMessage(self):
        print
        print "\nPrint Channel Connection Test:"

        con1=Connection(self.backend,self.uid0)
        msg=Message(con1, 'test message')
        channel_con0=channel_connection_from_message(msg)

        "assert that the ChannelConnection's contact has the correct ID"
        self.assertTrue(channel_con0.contact.debug_id==self.uid0)

        # create a _different_ message on the same connection
        msg = Message(con1, 'Another Message')
        channel_con1=channel_connection_from_message(msg)

        # assert channel_connections are the SAME
        self.assertTrue(channel_con0==channel_con1)
        
        # create a new channel connection for other contact
        con2=Connection(self.backend,self.uid1)
        msg2=Message(con2, 'test message 2')
        channel_con2=channel_connection_from_message(msg2)
        
        self.assertTrue(channel_con2 != channel_con1)
        
    def testContactFromMsg(self):
        print
        print "Test contact_from_message"
        msg1 = Message(Connection(self.backend,self.uid1))
        cnt1 = contact_from_message(msg1)
        self.assertTrue(
                        cnt1.created_from_channel_connection.user_identifier==
                            self.uid1)
        
        msg2 = Message(Connection(self.backend,self.uid1))
        cnt2 = contact_from_message(msg2)
        self.assertTrue(cnt2 == cnt1)
        
        msg3 = Message(Connection(self.backend,self.uid2))
        cnt3 = contact_from_message(msg3)
        self.assertTrue(cnt3 != cnt1)
        
    def testCommunicationChannelFromMsg(self):
        print
        print "Test communication_channel_from_message"
        msg1 = Message(Connection(self.backend,self.uid1))
        comm1=communication_channel_from_message(msg1)
        comm2=communication_channel_from_message(msg1)
        self.assertTrue(comm1 == comm2)
        
        msg2 = Message(Connection(self.backend,self.uid2))
        comm3 = communication_channel_from_message(msg2)
        self.assertTrue(comm3 == comm1)
        
    def testPerms(self):
        def printPerms(c):
            print "S: %s, R: %s, I: %s, A: %s" % \
                (c.perm_send, c.perm_receive, c.perm_ignore, c.perm_admin)
            
        print "Permission Test"
        c0=_contact('default')
        printPerms(c0)
        self.assertTrue(c0.perm_send and 
                        c0.perm_receive and 
                        not c0.perm_ignore and
                        not c0.perm_admin)
        c0.perm_ignore=True
        printPerms(c0)
        c0.save()
        self.assertTrue(c0.perm_send and c0.perm_receive and c0.perm_ignore)
        c0.perm_send=False
        self.assertFalse(c0.perm_send)
        c0.perm_receive=False
        self.assertFalse(c0.perm_receive)
        c0.perm_send=True
        self.assertTrue(c0.perm_send)
        c0.perm_receive=True
        self.assertTrue(c0.perm_receive)
        c0.perm_ignore=False
        self.assertFalse(c0.perm_ignore)
        c0.perm_ignore=True
        self.assertTrue(c0.perm_ignore)
        c0.perm_admin=False
        self.assertFalse(c0.perm_admin)
        c0.perm_admin=True
        self.assertTrue(c0.perm_admin)
        c0.perm_send=False
        c0.perm_receive=False
        c0.perm_ignore=True
        c0.perm_admin=True
        c0.save()
        c1=Contact.objects.get(pk=c0.id)
        self.assertTrue(not c1.perm_send and 
                        not c1.perm_receive and 
                        c1.perm_ignore and
                        c1.perm_admin)
        
    def testPermissionRestrictions(self):
        print
        print 'Test permission restrictions'
        user = self.m_nodes[0]
        
        user.perm_receive=False
        self.assertFalse(user.can_receive)
        try:
            user.send_to('Not allowed')
        except PermissionException, ex:
            self.assertTrue(ex.receive==False)
            print ex
        else:
            # should raise an exception
            self.assertTrue(False)
            
        user.perm_receive=True
        self.assertTrue(user.can_receive)
        user.send_to('Allowed')
        
        user.perm_send=False
        self.assertFalse(user.can_send)
        msg = Message(Connection(self.backend,self.uid2))
        try:
            user.sent_message_accepted(msg)
        except PermissionException, ex:
            self.assertTrue(ex.send==False)
            print ex
        else:
            # should raise exception
            self.assertTrue(False)
            
        user.perm_send = True
        self.assertTrue(user.can_send)
        # should not raise exception
        user.sent_message_accepted(msg)
        
        user.perm_ignore = True
        self.assertFalse(user.can_send)
        self.assertFalse(user.can_receive)
        try:
            user.send_to('Not Allowed')
        except PermissionException, ex:
            self.assertTrue(ex.ignore==True)
            print ex
        else:
            # should have thrown an exception
            self.assertTrue(False)

        try:
            user.sent_message_accepted(msg)
        except PermissionException, ex:
            self.assertTrue(ex.ignore==True)
            print ex
        else:
            # should raise exception
            self.assertTrue(False)
            
        user.perm_ignore=False
        self.assertTrue(user.can_send)
        self.assertTrue(user.can_receive)
    
    def testUniqueID(self):
        print 
        print 'Unique ID tests'
        user1 = self.m_nodes[0]
        user1.unique_id = 'Fred01'
        user1.save()
        
        user2 = self.m_nodes[1]
        user2.unique_id = 'Fred01'
        try:
            user2.save()
        except Exception, ex:
            print ex
        else:
            # should have thown
            self.assertTrue(False)
            
        user2.unique_id = 'Fred02'
        user2.save()   
    
    def testAge(self):
        print 
        print 'Age tests'
        user = self.w_nodes[0]
        user.age_months = 10*12
        user.save()
        self.assertTrue(user.age_months==10*12)
        self.assertTrue(user.age_years==10)
        user.age_years = 5
        user.save()
        self.assertTrue(user.age_months==5*12)
        user.age_years=1.5
        self.assertTrue(user.age_months==int(1.5*12))
        user.age_years=1.2
        # months is always a rounded down int
        self.assertTrue(user.age_months==int(math.floor(1.2*12)))
        user.age_months=17
        self.assertTrue(user.age_years==17/12.0)
        
    def testSignature(self):
        print 
        print 'Signature tests'
        user = self.w_nodes[1]
        user.common_name='Mary'
        print user.signature
        self.assertTrue(user.signature=='Mary: %s' % user.id)
        user.common_name=None
        user.given_name='Mary'
        print user.signature
        self.assertTrue(user.signature=='Mary: %s' % user.id)
        user.family_name='Worth'
        print user.signature
        self.assertTrue(user.signature=='Mary Worth: %s' % user.id)
        user.given_name=None
        print user.signature
        self.assertTrue(user.signature=='Worth: %s' % user.id)
        user.family_name=None
        self.assertTrue(user.signature=='%s' % user.id)
        user.common_name='01234567890'
        self.assertTrue(user.signature=='%s: %s' % \
                        (user.common_name, user.id))
        
        self.assertTrue(user.get_signature(max_len=100)==
                            '%s: %s' % \
                        (user.common_name, user.id))
        
        
        self.assertTrue(user.get_signature(max_len=8)==
                            '%s' % user.id)
    
    def testQuotas(self):
        print 
        print 'Quota tests'
        
        user = self.w_nodes[1]
        
        # default is quotas are off
        self.assertTrue(user.quota_send==(0,0))
        self.assertTrue(user.quota_receive==(0,0))
        self.assertFalse(user.has_quota_send)
        self.assertFalse(user.has_quota_receive)
        self.assertTrue(user.under_quota_send)
        self.assertTrue(user.under_quota_receive)
        self.assertTrue(user.period_remain_quota_send is None)
        self.assertTrue(user.period_remain_quota_receive is None)
        
        # set a quota and verify values
        user.quota_send=(10, 15)
        user.save()
        user = Contact.objects.get(pk=user.id)
        self.assertTrue(user.quota_send==(10,15))
        self.assertTrue(user.has_quota_send)
        self.assertTrue(user.under_quota_send)
        self.assertFalse(user.has_quota_receive)
        self.assertTrue(user.under_quota_send)
        self.assertTrue(user.under_quota_receive)
        sleep(2) # give a little time to count down
        self.assertTrue(user.period_remain_quota_send == 14) 
        self.assertTrue(user.period_remain_quota_receive is None)
        user.quota_send=None
        user.save()
        self.assertFalse(user.has_quota_send)
        
        # do it again for receive
        user.quota_receive=(10, 15)
        user.save()
        user = Contact.objects.get(pk=user.id)
        self.assertTrue(user.quota_receive==(10,15))
        self.assertTrue(user.has_quota_receive)
        self.assertTrue(user.under_quota_receive)
        self.assertFalse(user.has_quota_send)
        self.assertTrue(user.under_quota_receive)
        self.assertTrue(user.under_quota_send)
        sleep(2) # give a little time to count down
        self.assertTrue(user.period_remain_quota_receive == 14) 
        self.assertTrue(user.period_remain_quota_send is None)
        user.quota_receive=None
        user.save()
        self.assertFalse(user.has_quota_receive)
        
        # Now test decrement
        msg1 = Message(Connection(self.backend,self.uid1))
        user = contact_from_message(msg1)
        user.quota_receive=(10,15)
        for i in range(1,11):
            self.assertTrue(user.under_quota_receive)
            user.send_to('Hello')
            self.assertTrue(user._get_quota_headroom(type=quota_type.RECEIVE)==10-i)
        
        # this one should blow!
        try:
            user.send_to('Hello')
        except QuotaException, ex:
            print ex
        else:
            # should have blown
            self.assertTrue(False)
        
        # reset the quota and send again
        user.quota_receive=(1,15)
        user.send_to('Hello')
        user.quota_receive=None
        
        # now try the send quota
        user.quota_send=(10,15)
        for i in range(1,11):
            self.assertTrue(user.under_quota_send)
            user.sent_message_accepted(Message(connection='foo'))
            self.assertTrue(user._get_quota_headroom(type=quota_type.SEND)==10-i)
        
        # this one should blow!
        try:
            user.sent_message_accepted(Message(connection='foo'))
        except QuotaException, ex:
            print ex
        else:
            # should have blown
            self.assertTrue(False)
        
        # reset the quota and send again
        user.quota_send=(1,15)
        user.sent_message_accepted(Message(connection='foo'))
        user.quota_send=None   
        
        # now test timeperiods, takes a while 'cause minimum period is 1 min
        user.quota_receive=(1,1)
        user.send_to('hello')
        try:
            user.send_to('hello')
        except QuotaException, ex:
            # good!
            print ex
        else:
            self.assertTrue(False)
        # now wait 1 min
        print 'Waiting 1 minute for quota time out'
        sleep(60)
        self.assertTrue(user.under_quota_receive)
        user.send_to('hello')
        user.receive_quota=None
         
        # try it for send quota
        user.quota_send=(1,1)
        user.sent_message_accepted(Message(connection='foo'))
        try:
            user.sent_message_accepted(Message(connection='foo'))
        except QuotaException, ex:
            # good!
            print ex
        else:
            self.assertTrue(False)
        # now wait 1 min
        print 'Waiting 1 minute for quota time out'
        sleep(60)
        self.assertTrue(user.under_quota_send)
        user.sent_message_accepted(Message(connection='foo'))
        user.send_quota=None