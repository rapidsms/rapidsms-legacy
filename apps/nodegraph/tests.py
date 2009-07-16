from rapidsms.tests.scripted import TestScript
from app import App
import apps.nodegraph.app as nodegraph_app
from apps.nodegraph.models import Node, NodeSet

# helpers
def _user(name, *grps):
    u=Node(debug_id=name)
    u.save()
    for grp in grps:
        u.add_to_parent(grp)

    return u

def _group(name, *children):
    g=NodeSet(debug_id=name)
    g.save()
    g.add_children(*children)
    return g

class Person(Node):
    @property
    def who_am_i(self):
        return 'Person'

class Parent(Person):
    @property
    def who_am_i(self):
        return 'Parent'

class Family(NodeSet):
    @property
    def who_am_i(self):
        return 'Family'


class TestApp (TestScript):
    apps = (App, nodegraph_app.App)

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
        self.m_nodes = [_user(n) for n in self.m_names]
        self.w_nodes = [_user(n) for n in self.w_names]
        self.girl_nodes = [_user(n) for n in self.girl_names]
        self.boy_nodes = [_user(n) for n in self.boy_names]
        self.m_group = _group('men',*self.m_nodes)
        self.w_group = _group('women',*self.w_nodes)
        self.g_group = _group('girls',*self.girl_nodes)
        self.g_group.add_to_parent(self.w_group)
        self.b_group = _group('boys',*self.boy_nodes)
        self.b_group.add_to_parent(self.m_group)

        self.people_group = _group('people', self.m_group, self.w_group)

        # set up Cyclic(A(B(*A,woman),man))
        self.cyc_a=_group('a',self.m_nodes[0])
        self.cyc_b=_group('b',self.cyc_a,self.w_nodes[0])
        self.cyc_a.add_children(self.cyc_b)
        self.cyclic_group=_group('cyclic',self.cyc_a)
               
        # simple tree 
        self.leaf1=_user('leaf1')
        self.leaf2=_user('leaf2')
        self.simple_tree=_group('tree', _group('L1',_group('L2',self.leaf1, _group('L3',self.leaf2))))
        
        self.all_groups = [
                        self.simple_tree,
                        self.cyclic_group,
                        self.cyc_a,
                        self.cyc_b,
                        self.people_group,
                        self.b_group,
                        self.g_group,
                        self.m_group,
                        self.w_group
                        ]
        
    def tearDown(self):
        all_nodes=set()
        for g in self.all_groups:
            all_nodes.update(g.flatten())
        for n in all_nodes:
            n.delete()
            
        for g in self.all_groups:
            g.delete()
        
    def test01BasicNodeAndNodeSet(self):
        print
        print "BASIC NODE and SET TESTS"
        print 'Create Node'
        n1 = _user('Node01')
        print 'Create NodeSet'
        ns1 = _group('NodeSet1')
        print 'Add Node to NodeSet w/add_to_parent'
        n1.add_to_parent(ns1)
        self.assertTrue(len(ns1.children)==1 and ns1.children[0]==n1)
        self.assertTrue(len(n1.parents)==1 and n1.parents[0]==ns1)
        print 'Remove from parent'
        n1.remove_from_parent(ns1)
        self.assertTrue(len(ns1.children)==0)
        self.assertTrue(len(n1.parents)==0)
        print 'Create second NodeSet and add via add_to_parents'
        ns2 = _group('NodeSet2')
        n1.add_to_parents(ns2,ns1)
        self.assertTrue(set(n1.parents)==set([ns1,ns2]))
        self.assertTrue(set(ns2.children)==set([n1]) and
                        set(ns1.children)==set([n1]))
        print 'Remove from parents'
        n1.remove_from_parents(ns1,ns2)
        self.assertTrue(len(n1.parents)==0)
        self.assertTrue(len(ns1.children)==0 and len(ns2.children)==0)
        print 'Create NodeSet3 and add NodeSets to eachother'
        ns3 = _group('NodeSet3')
        ns1.add_to_parent(ns2)
        self.assertTrue(set(ns2.get_children(klass=NodeSet))==\
                            set([ns1]))
        self.assertTrue(set(ns1.get_parents(klass=NodeSet))==\
                            set([ns2]))
        print 'Remove ns1 from ns2 with remove_from_parent'
        ns1.remove_from_parent(ns2)
        self.assertTrue(len(ns2.children)==0)
        self.assertTrue(len(ns1.parents)==0)
        print 'Add ns1 to ns2 and ns3 with add_to_parents'
        ns1.add_to_parents(ns2,ns3)
        self.assertTrue(set(ns2.get_children(klass=NodeSet))==\
                            set([ns1]))
        self.assertTrue(set(ns3.get_children(klass=NodeSet))==\
                            set([ns1]))
        self.assertTrue(set(ns1.get_parents(klass=NodeSet))==\
                            set([ns3,ns2]))
        print 'Remove ns1 with remove from parents'
        ns1.remove_from_parents(ns2,ns3)
        self.assertTrue(len(ns2.children)==0)
        self.assertTrue(len(ns3.children)==0)
        self.assertTrue(len(ns1.parents)==0)
        print 'Create additional Node, n2'
        n2 = _user('Node2')
        print 'Add n1, n2, ns1 to ns2 with add_children'
        ns2.add_children(n1,n2,ns1)
        self.assertTrue(set(ns2.get_children(klass=NodeSet))==\
                            set([n1,n2,ns1]))
        print 'Remove n2, ns1 with "remove_children"'
        ns2.remove_children(n2,ns1)
        self.assertTrue(set(ns2.children)==set([n1]))
        
        print 'Delete all nodes'
        for n in [ns1,ns2,ns3,n1,n2]:
            n.delete()

    def test02FlattenTests(self):
        print
        print "FLATTEN TESTS"
        print 'Simple 1-level flatten'
        self.assertTrue(set(self.b_group.flatten())==set(self.boy_nodes))
        print 'Two level flatten'
        self.assertTrue(set(self.m_group.flatten())==
                        (set(self.m_nodes)|set(self.boy_nodes)))

        print 'Flatten w/max_depth'
        self.assertTrue(set(self.m_group.flatten(max_depth=1))==
                        set(self.m_nodes))

    def test03Ancestors(self):
        print
        print "ANCESTOR TESTS"
        print 'Test of 1-level high ancestor chain'
        self.assertTrue(
            set(self.boy_nodes[0].get_ancestors(max_alt=1,klass=NodeSet))==
            set([self.b_group])
            )

        print 'Test of 2-level high ancestor chain'
        self.assertTrue(
            set(self.boy_nodes[0].get_ancestors(max_alt=2,klass=NodeSet))==
            set([self.b_group, self.m_group])
            )

        print 'Test full ancestors'
        self.assertTrue(
            set(self.boy_nodes[0].get_ancestors(klass=NodeSet))==
            set([self.b_group, self.m_group, self.people_group])
            )
                            
    def test04Downcast(self):
        print
        print "DOWNCAST TESTS"
        prnt = Parent(debug_id='Parent1')
        prnt.save()
        prsn = Person(debug_id='Person1')
        prsn.save()
        fmly = Family(debug_id='Family1')
        fmly.save()

        fmly.add_children(prnt, prsn)

        self.assertTrue(type(fmly.children[0]==Node))
        self.assertTrue(type(fmly.children[1]._downcast(Person))==
                        Person)
        self.assertTrue(fmly.children[1]._downcast(Person).who_am_i=='Person')
        self.assertTrue(type(prsn.get_parents(klass=Family)[0])==
                        Family)
        self.assertTrue(prsn.get_parents(klass=Family)[0].who_am_i=='Family')
        for p in fmly.flatten(klass=Person):
            self.assertTrue(type(p)==Person and
                            p.who_am_i=='Person')
        
    def test05Cyclic(self):
        print
        print "CYCLIC TESTS"
        self.assertTrue(set(self.cyclic_group.flatten())==
                        set([self.m_nodes[0],self.w_nodes[0]]))
        self.assertTrue(set(self.cyc_a.get_ancestors(klass=NodeSet))==
                        set([self.cyc_b,self.cyclic_group]))
