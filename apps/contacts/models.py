#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from datetime import datetime,timedelta

from django.db import models
from rapidsms.message import Message
from rapidsms.connection import Connection
from apps.nodegraph.models import Node
from apps.locations.models import Location
import math
from rapidsms import utils
import traceback

# 
# Definition of Contacts (people) and ChannelConnections (ways to contact 
# those people) that depends on nodegraph 
#

#
# Module Constants
#

class quota_type():
    SEND='send'
    RECEIVE='receive'

class permission_type():
    SEND='send'
    RECEIVE='receive'
    IGNORE='ignore'

CHOICE_VALUES={
    'male':'m',
    'female':'f'
}

GENDER_CHOICES=(
    (CHOICE_VALUES['male'], 'male'),
    (CHOICE_VALUES['female'],'female')
)


class QuotaException(Exception):
    """
    Exception for going over a send or receive quote

    """

    def __init__(self,message=None,type=quota_type.SEND,period_remain=None):
        self.type=type
        self.remain=period_remain
        self.ts=datetime.utcnow()
        
        if message is None:
            message = '%s(%s): %s at %s' % \
                (self.__class__.__name__,self.type,str(self.ts))
                
            if self.period_remain is not None:
                message+='. %d minutes in quota period' % \
                    (self.remain.days*86400 + self.remain.seconds)
        Exception.__init__(self,message)
        

class PermissionException(Exception):
    """
    Exception for going over a send or receive permissions

    """
    def __init__(self,message=None,send=False, receive=False, ignore=False):
        self.send=send
        self.receive=receive
        self.ignore=ignore
        
        if message is None:
            message = '%s: perms: Send (%s)  Receive (%s) Ignore (%s)' % \
                (self.__class__.__name__,self.send,self.receive,self.ignore)
        Exception.__init__(self,message)
    
#    
# reimplementing stuff from Reporters to work with Node classes. 
# basically this should be agreed on and moved to core
# TODO: harmonize with Reporters
#
class Contact(Node):
    """
    Represents a person or other contact that can send and recive
    messages to this system.

    Minimum requirement for utility is that one ChannelConnection
    (a way to reach this contact, e.g. a phone number and a modem
    backend) is created with this contact as a ForeignKey

    given_name -- May be multiple names in single string, e.g. "Jeffrey Louis"
    family_name -- May be multiple names in single string, e.g. "Wishnie Edwards"

    That is, it's up to the users of the system to define what goes in those fields.
    But in general *given_name* should identify individuals and *family_name*
    identifies families.

    national_id -- A uniqued field that can hold a unique id across all Contacts.
    It is not required but useful for storing things that a national id (e.g. SocSec number)

    """

    # permission masks
    __PERM_RECEIVE=0x01
    __PERM_SEND=0x02
    __PERM_ADMIN=0x04
    __PERM_IGNORE=0x08 # trumps the others


    #
    # Table columns
    #

    # when Contact was first created (not modifiable, Django sets this)
    first_seen = models.DateTimeField(auto_now_add=True)

    # First name, or names, e.g. 'Jeffrey Louis'
    given_name = models.CharField(max_length=255,blank=True)

    # Last name, or names, e.g. Wishnie Luk
    family_name = models.CharField(max_length=255,blank=True)

    # How the Contact wants to be addressed in the context
    # of sending and receiving messages, e.g. Jeff W.
    common_name = models.CharField(max_length=255,blank=True)

    # a unique (but nullable field) that can be used for any
    # gloabbly unique info for the Contact. E.g. a National ID
    # where availble, or a system username
    unique_id = models.CharField(max_length=255,unique=True,null=True,blank=True)

    # a nullable field to identify the actual geographic location of contacts
    # (for ease of use, those around a village may decide to join that village
    # even if they live somewhere else
    location = models.ForeignKey(Location, null=True, blank=True)

    # 'm' or 'f'
    gender = models.CharField(max_length=1,choices=GENDER_CHOICES,blank=True) 

    # store age in months in case you want to track people under 1yr old
    # or older people in more detail. The property 'age_years' lets
    # you retrieve and store this in years
    age_months = models.IntegerField(null=True,blank=True)

    # User's prefered locale, in v2 3-letter style (e.g. 'eng'=='en')
    _locale = models.CharField(max_length=10,null=True,blank=True)

    # channel_connections[] -- is available via ForeignKey in ChannelConnection
    
    # Permissions and  Quota
    # 
    # There are 3 permissions stored in a bit mask. Properties on the 
    # contact object give simple 'perm_XXX' access to setting and reading these.
    # you shouldn't have to muck with '_permissions' directly.
    #
    # The permissions are:
    # - 'CAN_RECEIVE' -- contact can receive messages sent by RapidSMS
    # - 'CAN_SEND' -- contact can send messages to RapidSMS (ok, we
    #                 can't really stop them from sending, but we _can_
    #                 reject them when received)
    # - 'IGNORE' -- Ignore should be interpreted by Apps as 'ignore this contact
    #               entirely'. E.g. if a Contact has IGNORE, just return False
    #               from 'App.handle' and do not respond.
    # -  'ADMIN' -- Not used for anything right now but could indicate an admin
    #               user who can do things others can't
    #
    # There are two quotas: Send and Receive, interpreted just like the 
    # permissions. They are expressed as '# messages/N-minutes (period)'
    # If 'period' is 0, it is interpreted as unlimited and '# messages is ignored'
    #
    # Permissions are global and can restrict access to RapidSMS beyond the 
    # quotas. E.g. a user with quota to receive messages but without the 'can send'
    # permission is not allowed to send messages to the system.
    #
    _permissions = models.PositiveSmallIntegerField(default=__PERM_RECEIVE | __PERM_SEND)

    # TODO --normalize into a quota sub-table with 'send' and 'receive' entries?
    # worth it if we come up with more quota types, but won't worry about for now
    _quota_send_max = models.PositiveSmallIntegerField(default=0)
    _quota_send_period = models.PositiveSmallIntegerField(default=0) # period in minutes
    _quota_send_period_begin = models.DateTimeField(null=True,blank=True)
    _quota_send_seen = models.PositiveSmallIntegerField(default=0) # num messages seen in current period
    _quota_receive_max = models.PositiveSmallIntegerField(default=0)
    _quota_receive_period = models.PositiveSmallIntegerField(default=0) # period in minutes
    _quota_receive_period_begin = models.DateTimeField(null=True,blank=True)
    _quota_receive_seen = models.PositiveSmallIntegerField(default=0) # num messages seen in current period

    def __unicode__(self):
        return unicode(self.signature)

    #
    # Use the following to make sure quotas are enforced!!
    #
    def send_response_to(self,text,in_reply_to=None):
        """
        Use to send a response to a received message.
        
        - in_reply_to -- the msg you are respoding to. This uses the
                 associated CommunicationChannel to know
                 how to send the reply. E.g. if the Contact
                 has CommConnections to multiple cell phone
                 companies or email acconts--that is they have
                 multiple phone numbers or email addresses--
                 this will make sure the response goes to the
                 number/address that the user used to send in 
                 the original message.

        """
        if in_reply_to is not None:
            cc = channel_connection_from_message(in_reply_to)
        else:
            cc = self.created_from_channel_connection

        self.send_to(text,cc)

    def send_to(self,text,channel_conn=None):
        """
        Send a message to the Contact.

        - com_channel -- if this is a specific communication_channel, 
        send on this channel only. Iif it is None, send on ALL channels. 
        If it is the token 'preferred', send on the preferred channel only
        
        NOTE: Preferred is not currently implemented!
        
        """
        if self.perm_ignore or not self.perm_receive:
            # read as 'Contact does not have right to receive messages'
            raise PermissionException(
                                        send=self.perm_send,
                                        receive=self.perm_receive,
                                        ignore=self.perm_ignore
                                      )
        
        if not self.under_quota_receive:
            # NOTE: to be strict we'd check this in the loop
            # but for efficiency we'll count all messages sent on all
            # channels as one message against the quota.
            #
            # When we need something more complicated than this,
            # quotas will need to move to CommunicationChannel so that
            # e.g. we can have 1 quota for SMS and another for Email
            raise QuotaException('User over Receive quota',quota_type.SEND)

        connections=[]
        if channel_conn is not None:
            connections.append(channel_conn)
        else:
            connections=self.channel_connections.all()

        # TODO: raise exception if no connections?
        try:
            for conn in connections:
                self._quota_receive_seen+=1
                try:
                    Message(conn.connection, text).send()
                except Exception:
                    # TODO: fix the finding a backend mess..
                    pass
        finally:
            self.save()

    def sent_message_accepted(self,msg):
        """
        Let the system know that RapidSMS accepted a message
        sent by the Contact, and increment their 'send' quota

        """
        
        if self.perm_ignore or not self.perm_send:
            # read as 'Contact does not have right to send messages'
            raise PermissionException(
                                        send=self.perm_send,
                                        receive=self.perm_receive,
                                        ignore=self.perm_ignore
                                      )
        
        if not self.under_quota_send:
            raise QuotaException('User over Send quota',quota_type.SEND)

        self._quota_send_seen+=1
        self.save()

    ##############
    # Properties #
    ##############
    def __get_locale(self):
        return self._locale

    def __set_locale(self,val):
        if val is None:
            raise("Locale can't be None!")
        self._locale=val
        self.save()
    locale=property(__get_locale,__set_locale)

    def __get_age_years(self):
        """
        Always a float to account for things 6 month old
        
        6 months = 0.5 age_years
        
        """
        if self.age_months is None:
            return None
        return self.age_months/12.0

    def __set_age_years(self,value):
        """
        You may pass a float, but is always
        stored as rounded-down integer months
        
        """
        self.age_months=int(math.floor(value*12))
    age_years=property(__get_age_years,__set_age_years)

    def __can_receive(self):
        """
        Returns a _SINGLE_ 'True/False' representing
        
        Both permissions and quota_type. 

        E.g. True if-and-only-if user has both send
        permission and quota_type.

        """
        return not self.perm_ignore and \
            self.perm_receive and \
            self.under_quota_receive
    can_receive=property(__can_receive)

    def __get_can_send(self):
        """
        Returns a _SINGLE_ 'True/False' representing
        
        Both permissions and quota_type. 

        E.g. True if-and-only-if user has both send
        permission and quota_type.

        """
        return not self.perm_ignore and \
            self.perm_send and \
            self.under_quota_send
    can_send=property(__get_can_send)

    def __get_perm_receive(self):
        return bool(self._permissions & self.__PERM_RECEIVE)

    def __set_perm_receive(self,val):
        if bool(val):
            self._permissions|=self.__PERM_RECEIVE
        else:
            self._permissions&=~self.__PERM_RECEIVE
    perm_receive=property(__get_perm_receive, __set_perm_receive)

    def __get_perm_send(self):
        """
        Returns state of 'send' permission, regardless
        of quota_type.

        """
        return bool(self._permissions & self.__PERM_SEND)

    def __set_perm_send(self,val):
        if bool(val):
            self._permissions|=self.__PERM_SEND
        else:
            self._permissions&=~self.__PERM_SEND
    perm_send=property(__get_perm_send,__set_perm_send)

    def __get_perm_admin(self):
        return bool(self._permissions & self.__PERM_ADMIN)

    def __set_perm_admin(self,val):
        if bool(val):
            self._permissions|=self.__PERM_ADMIN
        else:
            self._permissions&=~self.__PERM_ADMIN
    perm_admin=property(__get_perm_admin,__set_perm_admin)

    def __get_perm_ignore(self):
        return bool(self._permissions & self.__PERM_IGNORE)

    def __set_perm_ignore(self,val):
        if bool(val):
            self._permissions|=self.__PERM_IGNORE
        else:
            self._permissions&=~self.__PERM_IGNORE
    perm_ignore=property(__get_perm_ignore, __set_perm_ignore)        

    # quota manipulators
    def __check_quota_period(self, type=quota_type.SEND):
        """
        Checks to see if quota period has expired and resets
        quota levels if it has.

        returns: True if the quota period was reset and False otherwise
                 (including the case where there is no quota set)
        
        """
        remain=self.__get_quota_period_remain(type)
        
        if remain is not None and \
                abs(remain) != remain:
            # we have a quota, and are beyond time period, and should
            # reset the period
            setattr(self,'_quota_%s_period_begin' % type, datetime.utcnow())
            setattr(self, '_quota_%s_seen' % type, 0)
            self.save()
            return True
        else:
            return False

    def set_quota(self, type=quota_type.SEND, max=15, \
                      period=15):
        """
        Set's quota and resets current period and count.

        """
        
        setattr(self,'_quota_%s_max' % type,max)
        setattr(self,'_quota_%s_period' % type,period)
        setattr(self,'_quota_%s_period_begin' % type, datetime.utcnow())
        setattr(self,'_quota_%s_seen' % type, 0)

    def __get_quota_send(self):
        """
        returns a tuple of (max, period)

        """
        return (self._quota_send_max,self._quota_send_period)

    def __set_quota_send(self,val):
        """
        Takes a tupe (int: max, int: period minutes)
        or None to turn off quota
        
        """
        if val is None:
            self.set_quota(type=quota_type.SEND,period=0)
        else:
            self.set_quota(quota_type.SEND,val[0],val[1])
    quota_send=property(__get_quota_send,__set_quota_send)

    def __get_quota_receive(self):
        """
        returns a tuple of (max, period)

        """
        return (self._quota_receive_max,self._quota_receive_period)

    def __set_quota_receive(self,val):
        if val is None:
            self.set_quota(type=quota_type.RECEIVE,period=0)
        else:
            self.set_quota(quota_type.RECEIVE,val[0],val[1])
    quota_receive=property(__get_quota_receive,__set_quota_receive)


    def _get_has_quota(self,type=quota_type.SEND):
        period=getattr(self, '_quota_%s_period' % type)
        return period!=0

    def __get_has_quota_send(self):
        return self._get_has_quota(quota_type.SEND)
    has_quota_send=property(__get_has_quota_send)

    def __get_has_quota_receive(self):
        return self._get_has_quota(quota_type.RECEIVE)
    has_quota_receive=property(__get_has_quota_receive)

    def _get_quota_headroom(self,type=quota_type.SEND):
        """
        how many more messages can go under current quota
        OR None if infinite quota.

        """
        if not getattr(self,'has_quota_%s' % type):
            return None

        # check and reset time period if needed before doing anything
        self.__check_quota_period(type)

        seen=getattr(self,'_quota_%s_seen' % type)
        max=getattr(self,'_quota_%s_max' % type)
        room=max-seen
        if room>0:
            return room
        else:
            return 0

    def __get_quota_period_remain(self,type=quota_type.SEND):
        """
        PRIVATE VERSION needed to avoid recursion

        Returns remaining time in minutes (rounded down) 
        in current period or None if infinite (no quota)

        Private version is also called by __check_quota_period

        """
        if not getattr(self,'has_quota_%s' % type):
            return None
        
        period_begin=getattr(self,'_quota_%s_period_begin' % type)
        period=timedelta(minutes=\
                         getattr(self,'_quota_%s_period' % type))
        return utils.timedelta_as_minutes(period-(datetime.utcnow()-period_begin))
        
    def _get_quota_period_remain(self,type=quota_type.SEND):
        """
        Return a timedelta object of remaining time
        in current period or None if infinite (no quota)

        """
        # check and reset time period if needed before doing anything
        self.__check_quota_period(type)
        return self.__get_quota_period_remain(type)
        
    def __get_under_quota_send(self):
        """Return number of messages under quota or 0 if over"""
        under=self._get_quota_headroom(type=quota_type.SEND)
        if under is None:
            return True
        return bool(under)
    under_quota_send=property(__get_under_quota_send)

    def __get_under_quota_receive(self):
        """Return number of messages under quota or 0 if over"""
        under=self._get_quota_headroom(type=quota_type.RECEIVE)
        if under is None:
            return True
        return bool(under)
    under_quota_receive=property(__get_under_quota_receive)

    def __get_period_remain_quota_send(self):
        return self._get_quota_period_remain(type=quota_type.SEND)
    period_remain_quota_send=property(__get_period_remain_quota_send)

    def __get_period_remain_quota_receive(self):
        return self._get_quota_period_remain(type=quota_type.RECEIVE)
    period_remain_quota_receive=property(__get_period_remain_quota_receive)

    def get_signature(self, max_len=None,for_message=None):
        """
        Return a string suitable for signing an SMS.
        
        - max_len -- max length in characters. Watch out! It may be
                     '' (blank str) if max_len is too small to write
                     anything meaningful

        - for_message -- if the sig is used on a response to a message,
                     or for a new one, pass that message in and the 
                     sig will include the associated id--e.g. if you
                     received a message on a pygsm backend talking to Orange
                     and you pass that message, you get the user's Orange number
                     in the sig
                     
        """
        
        # First try to make a name portion in this order
        # of what values are set:
        #
        # 1. common_name
        # 2. given_name family_name
        #
        # Then see if name_part + user_identifier fit under 
        # max.
        #
        # If not, see if identifier alone fits under and
        # truncate name part.
        #
        # If identifier alone doesn't fit center ltruncate it
        # so +14155551212 => ...1212
        # If that doesn't fit, return ''

        
        name_part= (None if utils.empty_str(self.common_name)
                    else self.common_name.strip())
        
        if utils.empty_str(name_part):
            gn = (None if utils.empty_str(self.given_name) 
                  else self.given_name.strip())
            fn = (None if utils.empty_str(self.family_name) 
                  else self.family_name.strip())
            if gn is not None and fn is not None:
                name_part=u'%s %s' % (gn,fn)
            elif gn is not None:
                name_part=gn
            else:
                name_part=fn

        # default to DB id so you can at least look 'em up
        id_part=str(self.id) 
        # try to get phone number from a channel connection
        if for_message is not None:
            cc=channel_connection_from_message(for_message,False)
        else:
            # take first one
            ccs=self.channel_connections.all()
            if len(ccs)==0:
                # hmmm, user exists only in DB. Has
                # never contacted system...
                cc=None
            else:
                cc=ccs[0]
        if cc is not None:
            id_part=cc.user_identifier
        
        # make sig
        if not utils.empty_str(name_part):
            sig=': '.join([name_part, id_part])
        else:
            sig=id_part
        if max_len is not None:
            # adjust for max len
            if len(sig)>max_len:
                sig=id_part
            if len(sig)>max_len:
                sig='...%s' % id_part[-4:]
            if len(sig)>max_len:
                sig=''
        return sig


    def __get_signature(self):
        return self.get_signature()
    signature=property(__get_signature)
    
#basically a PersistentBackend
class CommunicationChannel(models.Model):
    """
    Info to identify backend instances.

    And example of multiple comm-channels would be
    channels to each of several Mobile carriers.

    E.g. a modem communicating with Zain and another to MTN

    """
    backend_slug = models.CharField(max_length=30,primary_key=True)
    title = models.CharField(max_length=255,blank=True)

    def __repr__(self):
        return 'CommunicationChannel(backend_slug=%s,title=%s' % \
            (self.backend_slug, self.title)
    
    def __unicode__(self):
        return unicode(self.backend_slug)
    
    class Meta:
        unique_together = ('backend_slug','title')
            

# basically persistent connection
class ChannelConnection(models.Model):
    """
    Maps phone# to communication channel

    """
    user_identifier = models.CharField(max_length=64)
    communication_channel = models.ForeignKey(CommunicationChannel)

    # always associated with a Contact, though contact
    # may be _blank_
    contact = models.ForeignKey(Contact,related_name='channel_connections') 

    def __unicode__(self):
        return u"UserID: %s, Contact DebugID: %s, Backend: %s" % \
            (self.user_identifier, self.contact.debug_id, self.communication_channel.backend_slug)

    def __repr__(self):
        return 'ChannelConnection(%s,%s)' % \
            (self.user_identifier, self.communication_channel.backend_slug)

    @property
    def connection(self):
        return Connection(self.communication_channel.backend_slug, \
                              self.user_identifier)

    class Meta:
        unique_together = ('user_identifier', 'communication_channel')

#
# Module level methods (more or less equiv to Java static methods)
# Read online that this is a cleaner way to do this than @classmethod
# or @staticmethod which can have weird calling behavior
#
def communication_channel_from_message(msg, save=True):
    """
    Create a ChannelConnection object from a Message.

    If 'save' is True, object is saved to DB before 
    returning.

    """

    slug = msg.connection.backend.slug

    rs=CommunicationChannel.objects.filter(backend_slug=slug)
    cc=None
    if len(rs)==0:
        cc=CommunicationChannel(backend_slug=slug)
        if save:
            cc.save()
    else:
        cc=rs[0]
        
    return cc


def contact_from_message(msg,save=True):
    return channel_connection_from_message(msg,save).contact

def channel_connection_from_message(msg,save=True):
    """
    Create, or retrieve, a ChannelConnection from
    a message.

    E.g. Phone# + Service Provider backend

    """
    # Get the comm channel
    comm_c=communication_channel_from_message(msg)
    u_id=msg.connection.identity

    # try to get an existing ChannelConnection
    chan_con=None
    rs=ChannelConnection.objects.filter(user_identifier__exact=u_id, \
                                            communication_channel__exact=comm_c)
    if len(rs)==0:
        # didn't find an existing connection, which means this specific
        # CommunicationChannel (e.g. service provider) and id (e.g. phone number)
        # combo aren't known, so we need a blank Contact for this combo.
        contact=Contact(debug_id=u_id[:16]) # debug id is only 16 char
        contact.save()
        chan_con=ChannelConnection(user_identifier=u_id,\
                                       communication_channel=comm_c,\
                                       contact=contact)
        if save:
            chan_con.save()
    else:
        chan_con=rs[0]
    
    # cache channel connection back ptr for easy responses,
    # just in runtime object, not in db
    chan_con.contact.created_from_channel_connection = chan_con
    return chan_con



