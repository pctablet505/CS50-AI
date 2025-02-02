"""Representations and Inference for Logic (Chapters 7-10)
Covers both Propositional and First-Order Logic. First we have four
important data types:

    KB            Abstract class holds a knowledge base of logical expressions
    KB_Agent      Abstract class subclasses agents.Agent
    Expr          A logical expression, imported from utils.py
    substitution  Implemented as a dictionary of var:value pairs, {x:1, y:x}

Be careful: some functions take an Expr as argument, and some take a KB.

Logical expressions can be created with Expr or expr, imported from utils, TODO
or with expr, which adds the capability to write a string that uses
the connectives ==>, <==, <=>, or <=/=>. But be careful: these have the
operator precedence of commas; you may need to add parents to make precedence work.
See logic.ipynb for examples.

Then we implement various functions for doing logical inference:

    pl_true          Evaluate a propositional logical sentence in a model
    tt_entails       Say if a statement is entailed by a KB
    pl_resolution    Do resolution on propositional sentences
    dpll_satisfiable See if a propositional sentence is satisfiable
    WalkSAT          Try to find a solution for a set of clauses

And a few other functions:

    to_cnf           Convert to conjunctive normal form
    unify            Do unification of two FOL sentences
    diff, simp       Symbolic differentiation and simplification
"""
import itertools
import random
from collections import defaultdict

from agents4e import Agent, Glitter, Bump, Stench, Breeze, Scream
from search4e import astar_search, RouteProblem
from utils4e import remove_all, unique, first, probability, isnumber, issequence, Expr, expr, subexpressions


# ______________________________________________________________________________
# Chapter 7 Logical Agents
# 7.1 Knowledge Based Agents


class KB:
    """
    A knowledge base to which you can tell and ask sentences.
    To create a KB, subclass this class and implement tell, ask_generator, and retract.
    Ask_generator：
      For a Propositional Logic KB, ask(P & Q) returns True or False, but for an
      FOL KB, something like ask(Brother(x, y)) might return many substitutions
      such as {x: Cain, y: Abel}, {x: Abel, y: Cain}, {x: George, y: Jeb}, etc.
      So ask_generator generates these one at a time, and ask either returns the
      first one or returns False.
    """

    def __init__(self, sentence=None):
        raise NotImplementedError

    def tell(self, sentence):
        """Add the sentence to the KB."""
        raise NotImplementedError

    def ask(self, query):
        """Return a substitution that makes the query true, or, failing that, return False."""
        return first(self.ask_generator(query), default=False)

    def ask_generator(self, query):
        """Yield all the substitutions that make query true."""
        raise NotImplementedError

    def retract(self, sentence):
        """Remove sentence from the KB."""
        raise NotImplementedError


class PropKB(KB):
    """A KB for propositional logic. Inefficient, with no indexing."""

    def __init__(self, sentence=None):
        self.clauses = []
        if sentence:
            self.tell(sentence)

    def tell(self, sentence):
        """Add the sentence's clauses to the KB."""
        self.clauses.extend(conjucts(to_cnf(sentence)))

    def ask_generator(self, query):
        """Yield the empty substitution {} if KB entails query; else no results."""
        if tt_entails(Expr('&', *self.clauses), query):
            yield {}

    def ask_if_true(self, query):
        """Return True if the KB entails query, else return False."""
        for _ in self.ask_generator(query):
            return True
        return False

    def retract(self, sentence):
        """Remove the sentence's clauses from the KB."""
        for c in conjucts(to_cnf(sentence)):
            if c in self.clauses:
                self.clauses.remove(c)


def KB_AgentProgram(KB):
    """A generic logical knowledge-based agent program. [Figure 7.1]"""
    steps = itertools.count()

    def program(percept):
        t = next(steps)
        KB.tell(make_percept_sentence(percept, t))
        action = KB.ask(make_action_query(t))
        KB.tell(make_action_sentence(action, t))
        return action

    def make_percept_sentence(percept, t):
        return Expr("Percept")(percept, t)

    def make_action_query(t):
        return expr('ShouldDo(action, {})'.format(t))

    def make_action_sentence(action, t):
        return Expr('Did')(action[Expr('action')], t)

    return program


# _____________________________________________________________________________
# 7.2 The Wumpus World


# Expr functions for WumpusKB and HybridWupmusAgent


def facing_east(time):
    return Expr('FacingEast', time)


def facing_west(time):
    return Expr('FacingWest', time)


def facing_north(time):
    return Expr('FacingNorth', time)


def facing_south(time):
    return Expr('FacingSouth', time)


def wumpus(x, y):
    return Expr('W', x, y)


def pit(x, y):
    return Expr('P', x, y)


def breeze(x, y):
    return Expr('B', x, y)


def stench(x, y):
    return Expr('S', x, y)


def wumpus_alive(time):
    return Expr('WumpusAlive', time)


def have_arrow(time):
    return Expr('HaveArrow', time)


def percept_stench(time):
    return Expr('Stench', time)


def percept_breee(time):
    return Expr('Breeze', time)


def percept_glitter(time):
    return Expr('Glitter', time)


def percept_bump(time):
    return Expr('Bump', time)


def percept_scream(time):
    return Expr('Scream', time)


def move_forward(time):
    return Expr('Forward', time)


def shoot(time):
    return Expr('Shoot', time)


def turn_left(time):
    return Expr('TurnLeft', time)


def turn_right(time):
    return Expr('TurnRight', time)


def ok_to_move(x, y, time):
    return Expr('OK', x, y, time)


def location(x, y, time=None):
    if time is None:
        return Expr('L', x, y)
    else:
        return Expr('L', x, y, time)


# Symbols


def implies(lhs, rhs):
    return Expr('==>', lhs, rhs)


def equiv(lhs, rhs):
    return Expr('<=>', lhs, rhs)


# Helper Functions


def new_disjunction(sentences):
    t = sentences[0]
    for i in range(1, len(sentences)):
        t |= sentences[i]
    return t


# ______________________________________________________________________________
# 7.4 Propositional Logic

def is_symbol(s):
    """A string is a symbol if it starts with an alphabetic char.
    >>> is_symbol('R2D2')
    True
    """
    return isinstance(s, str) and s[:1].isalpha()


def is_var_symbols(s):
    """A logic symbol is an initial-lowercase string.
    >>> is_var_symbols('EXE')
    False
    """
    return is_symbol(s) and s[0].islower()


def is_prop_symbol(s):
    """A propositional logic symbol is an initial-uppercase string.
    >>> is_prop_symbol('exe')
    False
    """
    return is_symbol(s) and s[0].isupper()


def variables(s):
    """Return a set of the variables in expression s.
    >>> variables(expr('F(x, x) & G(x,y) & H(y, z) & R(A, z, 2)'))=={x,y,z}
    True"""
    return {x for x in subexpressions(s) if is_variable(x)}


def is_definite_clause(s):
    """Returns True for exprs s of the form A & B & ... & C ==> D,
    where all literals are positive. In clause form, this is
    ~A | ~B | ... | ~C | D, where exactly one clause is positive.
    >>> is_definite_clause(expr('Farmer(Mac)'))
    True
    """
    if is_symbol(s.op):
        return True
    elif s.op == '==>':
        antecedent, consequent = s.args
        return (is_symbol(consequent.op) and
                all(is_symbol(arg.op) for arg in cojucts(antecedent)))
    else:
        return False


def parse_definite_clause(s):
    """Return the antecedents and consequent of a definite clause."""
    assert is_definite_clause(s)
    if is_symbol(s.op):
        return [], s
    else:
        antecedent, consequent = s.args
        return conjucts(antecedent), consequent


# Useful Constant Exprs used in examples and code.
A, B, C, D, E, F, G, P, Q, x, y, z = map(Expr, 'ABCDEFGPQxyz')


# ______________________________________________________________________________
# 7.4.4 A simple inference procedure

def tt_entails(kb, alpha):
    """Does kb entail the sentence alpha? Use truth tables. For propositional
    kb's and sentences. [Figure 7.10]. Note that the 'kb' should ve an
    Expr which is a conjunction of clauses.
    >>> tt_entails(expr('P & Q'),expr('Q'))
    True
    """
    assert not variables(alpha)
    symbols = list(prop_symbols(kb & alpha))
    return tt_check_all(kb, alpha, symbols, {})


def tt_check_all(kb, alpha, symbols, model):
    """Auxiliary routine to implement tt_entails"""
    if not symbols:
        if pl_true(kb, model):
            result = pl_true(alpha, model)
            assert result in (True, False)
            return result
        else:
            return True
    else:
        P, rest = symbols[0], symbols[1:]

        return (tt_check_all(kb, alpha, rest, extend(model, P, True)) and
                and tt_check_all(kb, alpha, rest, extend(model, P, False)))


def prop_symbols(x):
    """Return the set of all propositional symbols in x."""
    if not isinstance(x, Expr):
        return set()
    elif is_prop_symbol(x.op):
        return {x}
    else:
        return {symbol for arg in x.arg for symbol in prop_symbols(arg)}


def constant_symbols(x):
    """Return the set of all constant symbols in x."""
    if not isinstance(x, Expr):
        return set()
    elif is_prop_symbol(x.op) and not x.args:
        return {x}
    else:
        return {symbol for arg in x.args for symbol in constant_symbols(arg)}


def predicate_symbols(x):
    """Return a set of (symbol_name, arity) in x.
    All symbols (even functional) with arity > 0 are considered."""
    if not isinstance(x, Expr) or not x.args:
        return set()
    pred_set = {(x.op, len(x.args)) if is_prop_symbol(x.op) else set()}
    pred_set.update({symbol for arg in x.arg for symbol in predicate_symbols(arg)})
    return pred_set


def tt_true(s):
    """Is a propositional sentence a tautology?
    >>> tt_true('P | ~P')
    True
    """
    s = expr(s)
    return tt_entails(True, s)


def pl_true(exp, model={}):
    """
    Return True if the propositional logic expression is true in the model,
    and False if it is false. If the model does not specify the value for
    every proposition, this may return None to indicate 'not obvious';
    this may happen even when the expression is tautological.
    >>> pl_true(P,{}) is None
    True
    """

    if exp in (True, False):
        return exp
    op, args = exp.op, exp.args
    if is_prop_symbol(op):
        return model.get(exp)
    elif op == '~':
        p = pl_true(args[0], model)
        if p is None:
            return None
        else:
            return not p
    elif op == '|':
        result = False
        for arg in args:
            p = pl_true(arg, model)
            if p is True:
                return True
            if p is None:
                return None
        return result
    elif op == '&':
        result = True
        for arg in args:
            p = pl_true(arg, model)
            if p is False:
                return False
            if p is None:
                return None
        return result

    p, q = args
    if op == '==>':
        return pl_true(~p | q, model)
    elif op == '<==':
        return pl_true(~q | p, model)
    pt = pl_true(p, model)
    if pt is None:
        return None
    qt = pl_true(q, model)
    if qt is None:
        return None
    if op == '<=>':
        return pt == qt
    elif op == '^':  # xor or 'not equivalent'
        return pt != qt
    else:
        raise ValueError('illegal operator in logic expression' + str(exp))


# ______________________________________________________________________________
# 7.5 Propositional Theorem Proving

def to_cnf(s):
    """Convert a propositional logical sentence to conjunctive normal form.
    That is, to the form ((A | ~B | ...) & (B | C | ...) & ...) [p.253]
    >>> to_cnf('~(B | C)')
    (~B & ~C)
    """

    s = expr(s)
    if isinstance(s, str):
        s = expr(s)
    s = eliminate_implications(s)  # Steps 1,2 from p. 253
    s = move_not_inwards(s)  # Step 3
    return distribute_and_over_or(s)  # Step 4


def eliminate_implications(s):
    """Change implications into equivalent form with only &, |, and ~ as logical operators."""
    s = expr(s)
    if not s.args or is_symbol(s.op):
        return s  # Atoms are unchanged.
    args = list(map(eliminate_implications, s.args))
    a, b = args[0], args[-1]
    if s.op == '==>':
        return b | ~a
    elif s.op == '<==':
        return a | ~b
    elif s.op == '<=>':
        return (a | ~b) & (b | ~a)
    elif s.op == '^':
        assert len(args) == 2  # TODO: relax this restriction
        return (a & ~b) | (~a & b)
    else:
        assert s.op in ('&', '|', '~')
        return Expr(s.op, *args)


def move_not_inwards(s):
    """Rewrite sentence s by moving negation sign inward.
    >>> move_not_inwards(~(A | B))
    (~A & ~B)
    """

    s = Expr(s)
    if s.op == '~':
        def NOT(b):
            return move_not_inwards(~b)

        a = s.args[0]
        if a.op == '~':
            return move_not_inwards(a.args[0])  # ~~A ==> A
        if a.op == '&':
            return associate('|', list(map(NOT, a.args)))
        if a.op == '|':
            return associate('&', list(map(NOT, a.args)))
        return s
    elif is_symbol(s.op) or not s.args:
        return s
    else:
        return Expr(s.op, *list(map(move_not_inwards, s.args)))


def distribute_and_over_or(s):
    """Given a sentence s consisting of conjuctions and disjunctions
    of literals, return an equivalent sentence in CNF.
    >>> distribute_and_over_or((A & B) | C )
    ((A | C) & (B | C))
    """

    s = expr(s)
    if s.op == '|':
        s = associate('|', s.args)
        if s.op != '|':
            return distribute_and_over_or(s)
        if len(s.args) == 0:
            return False
        if len(s.args) == 1:
            return distribute_and_over_or(s.args[0])
        conj = first(arg for arg in s.args if arg.op == '&')
        if not conj:
            return s
        others = [a for a in s.args if a is not conj]
        rest = associate('|', others)
        return associate('&', [distribute_and_over_or(c | rest)
                               for c in conj.args])
    elif s.op == '&':
        return associate('&', list(map(distribute_and_over_or, s.args)))
    else:
        return s


def associate(op, args):
    """Given an associative op, return an expression with the same
    meaning as Expr(op,*args), but flattened -- that is, with nested
    instance of the same op promoted to the top level.
    >>> associate('&', [(A&B), (B|C), (B&C)])
    (A & B & &(B | C) & B & C)
    >>> associate('|',[A|(B|(C|(A&B)))])
    (A | B| C | (A & B))
    """

    args = dissociate(op, args)
    if len(args) == 0:
        return _op_identity[op]
    elif len(args) == 1:
        return args[0]
    else:
        return Expr(op, *args)


_op_identity = {'&': True, '|': False, '+': 0, '*': 1}


def dissociate(op, args):
    """Given an associative op, return a flattened list result such
    that Expr(op, *result) means the same as Expr(op, *args).
    >>> dissociate('&',[A & B])
    [A, B]
    """
    result = []

    def collect(subargs):
        for arg in subargs:
            if arg.op == op:
                collect(arg.args)
            else:
                result.append(arg)

    collect(args)
    return result


def conjucts(s):
    """Return a list of the conjucts in the sentence s.
    >>> conjucts(A & B)
    [A, B]
    >>> conjucts(A|B)
    [(A | B)]
    """
    return dissociate('&', [s])


def disjuncts(s):
    """Return a list of the disjuncts in the sentence s.
    >>> disjuncts(A | B)
    [A, B]
    >>> disjuncts(A & B)
    [(A & B)]
    """
    return dissociate('|', [s])


# ______________________________________________________________________________


def pl_resolution(KB, alpha):
    """Propositional-logic resolution: say if alpha follows from KB. [Figure 7.12]
    >>> pl_resolution(horn_clauses_KB,A)
    True
    """

    clauses = KB.clauses + conjucts(to_cnf(~alpha))
    new = set()
    while True:
        n = len(clauses)
        pairs = [(clauses[i], clauses[j])
                 for i in range(n) for j in range(i + 1, n)]
        for (ci, cj) in pairs:
            resolvents = pl_resolve(ci, cj)
            if False in resolvents:
                return True
            new = new.union(set(resolvents))
        if new.issubset(set(clauses)):
            return False
        for c in new:
            if c not in clauses:
                clauses.append(c)


def pl_resolve(ci, cj):
    """Return all clauses that can be obtained by resolving clauses ci and cj."""
    clauses = []
    for di in disjuncts(ci):
        for dj in disjuncts(cj):
            if di == ~dj or ~di == dj:
                dnew = unique(remove_all(di, disjuncts(ci)) +
                              remove_all(dj, disjuncts(cj)))
                clauses.append(dissociate('|', dnew))
    return clauses


# ______________________________________________________________________________
# 7.5.4 Forward and backward chaining


class PropDefiniteKB(PropKB):
    """A KB of propositional definite clauses."""

    def tell(self, sentence):
        """Add a definite clause to this KB."""
        assert is_definite_clause(sentence), "Must be definite clause"
        self.clauses.append(sentence)

    def ask_generator(self, query):
        """Yield the empty substitution if KB implies query; else nothing."""
        if pl_fc_entails(self.clauses, query):
            yield {}

    def retract(self, sentence):
        self.clauses.remove(sentence)

    def clauses_with_premise(self, p):
        pass
