#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8


from django.db import models
from datetime import datetime

# 
# A data model for simple interconnected graphs of nodes.
#
# There are two types of nodes: Sets and Nodes.
#
# The only distinction is:
# - Sets may contain other nodes (both Sets and Nodes)
# - Leaves may _not_ contain other nodes (they terminate the graph)
#
# Speaking concretely, A graph of Nodes can represent GROUPS of USERS where:
# - Groups are Sets and can contain other Groups and Users
#
# Data integrity policies/enforcement:
# - When requests a list of members for a Set, the model will break cycles.
#   So if you have Set A with itself as the only member (A<A--A contains A) asking for the
#   members of 'A' will not create an endless loop, and will return an empty list
#
#   In the case of A<B<A (A contains B contains A) A.members() returns B only
#
# ALL OTHER RULES MUST BE ENFORCED BY THE USER OF THE MODEL. 
# For example, there is no restriction on Leaves appearing in multiple Sets
# 
#

class Node(models.Model):
    """
    Represents a Node in a cyclic graph. Superclass to NodeSet

    """

    """
    For testing only. If you want a real name, id, or any other data,
    make Node and NodeSet subclasses

    """
    debug_id = models.CharField(max_length=16,blank=True,null=True)
    
    def __unicode__(self):
        return u'%s' % self.debug_id

    @property
    def as_set(self):
        """Helper to tell if a Node is in fact a NodeSet"""
        if hasattr(self,'children'):
            return self

        ns = self._downcast(klass=NodeSet)
        if isinstance(ns, NodeSet):
            return ns
        return None
    
    def get_ancestors(self,max_alt=None,klass=None):
        """
        max_alt=None means no limit
        
        if 'klass' is a Class, downcast results

        """
        seen=set()

        if max_alt is not None:
            max_alt=int(max_alt)
            if max_alt<1:
                return
            
        def _recurse(node,alt):
            if (max_alt is not None and alt>max_alt) or \
                    node in seen:
                return
            else:
                seen.add(node)
                
            for a in node.get_parents():
                _recurse(a,alt+1)

        _recurse(self,0)
        seen.remove(self)
        ret=None
        if klass is not None:
            ret = [r._downcast(klass) for r in seen]
        else:
            ret = list(seen) # make a list so indexable, but order not guaranteed
        return ret

    def get_parents(self,klass=None):
        """
        The parent NodeSets this node is a member of.

        Equivalent to 'get_ancestors(max_alt=1)'

        Downcasted to 'klass' if provided (see downcast() for more info)

        """
        rents=self._parents.all()
        if klass is not None:
            return [r._downcast(klass) for r in rents]
        else:
            return rents

    @property
    def parents(self):
        return self.get_parents()
        
    def add_to_parent(self,rent):
        rent.add_children(self)

    def add_to_parents(self,*rents):
        for rent in rents:
            self.add_to_parent(rent)

    def remove_from_parent(self,rent):
        rent.remove_children(self)

    def remove_from_parents(self,*rents):
        for rent in rents:
            self.remove_from_parent(rent)
            
    def _downcast(self, klass):
        """
        Multiple-inherited models are weird.
        If you access a subclass from a superclass manager, you
        get an object of superclass type.

        E.g. You do aNone=Node.objects.all()[0], you will get Node classes
        even if the actual object is a subclass like a Contact.

        The 'contact' object will be availble as aNode.contact

        This method, given a target Class, will return the properly typed
        subclass.

        Usage example: aWorker=aNode.downcast(Worker)

        NOTE: If the object is not fully downcastable, it
        casts as far as possible, so return values may be of
        differing types.
        
        Take this obj map where '<' means inherits from:
        d<c<b<a
        
        If you have a set of objects (d,c,b,a), all know as 'a' type, and
        you downcast to 'd', the resulting list will be typed (d,c,b,a)
        
        NOTE2: PROBABLY WONT WORK WITH MULTIPLE INHERITENCE!! SO
        DON'T USE IT, IT'S DUMB ANYWAY. YOU _REALLY_ WANT duck-typing OR
        delegation OR component model instead.
        
        """
        # what class do I think I am?
        # e.g. 'Node'
        self_cname=self.__class__.__name__
        
        # what are all the target-class's superclasses?
        # e.g. Man<Person<Node<AbstractNode<object
        cast_cnames=[c.__name__ for c in klass.__mro__]

        # truncate list to only classes between target class and what
        # I think I am.
        # e.g. Man<Person
        cast_cnames=[cn.lower() for cn in cast_cnames[:cast_cnames.index(self_cname)]]

        # swap order for the walk
        # e.g. Person>Man
        cast_cnames.reverse()
        casted=self
        for cn in cast_cnames:
            # See if I have the Django inherited model attrib
            # and remeber that pointer
            # # self.person
            if hasattr(casted,cn):
                casted=getattr(casted,cn)
            else:
                break
        return casted

class NodeSet(Node):
    _children = models.ManyToManyField(Node,related_name='_parents')

    def __unicode__(self):
        """
        Prints the graph starting at this instance.

        Format is NodeSetName(subnode_set(*), subnode+)

        If nodes appear more than once in traversal, additional references are
        shown as *NodeSetName--e.g. pointer-to-NodeSetName.

        Given A->b,c,D->A, where CAPS are NodeSet and _lowers_ are Nodes, results are:

        A(D(*A),b,c)
        
        """

        buf=list()
        seen=set()
        def _recurse(node, index):            
            if index>0:
                buf.append(u',')

            ns = node.as_set
            if ns is not None:
                # it's a nodeset
                if ns in seen:
                    buf.append(u'*%s' % ns.debug_id)
                    return
                else:
                    seen.add(ns)
                    buf.append(u'%s(' % ns.debug_id)
                    i=0
                    for sub in ns.children:
                        _recurse(sub,i)
                        i+=1
                    buf.append(u')')
            else:
                # it's a node
                buf.append(u'%s' % node.debug_id)

        _recurse(self,0)

        return u''.join(buf)

    def add_children(self,*sub_nodes):
        """
        Add the passed nodes to this instance as 'subnodes'
        
        Can be NodeSets or Nodes
        
        """
        for n in sub_nodes:
            self._children.add(n)

    def remove_children(self, *subnodes):
        for n in subnodes:
            self._children.remove(n)
        
    def get_children(self, klass=None):
        childs = self._children.all()
        if klass is not None:
            return [c._downcast(klass) for c in childs]
        else:
            return childs

    # and some shortcut properties
    def __get_children(self):
        """All the direct sub-NodeSets"""
        return self.get_children()
    children=property(__get_children)

    # full graph access methods
    def flatten(self, max_depth=None,klass=None):
        """
        Flattens the graph from the given node to max_depth returning
        a set of all leaves.

        Breaks cycles.

        """
        # hold unique set of NodeSets we've visited to break cycles
        seen=set()
        leaves=set()

        if max_depth is not None:
            max_depth=int(max_depth)
            if max_depth<1:
                return leaves # empty set

        # recursive function to do the flattening
        def _recurse(node, depth):
            # check terminating cases
            # - node is None (shouldn't happen but why not be safe?)                        
            # - reached max_depth
            # - seen this guy before (which breaks any cycles)
            ns = node.as_set
            if (max_depth is not None and depth>max_depth) or \
                    ns in seen: 
                return
            
            if ns is not None:
                seen.add(ns)
                # recurse to its childsets
                for n in ns.children:
                    _recurse(n, depth+1)
            else:
                # add it to leaves
                leaves.add(node)
                
        # Now call recurse
        _recurse(self, 0)
        
        # downcast if requested and make sure returns are
        # indexable lists
        if klass is not None:
            return [l._downcast(klass) for l in leaves]
        else:
            return list(leaves)

