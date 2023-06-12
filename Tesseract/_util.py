from functools import reduce as _reduce, wraps as _wraps
from itertools import repeat as _repeat, starmap as _starmap, chain as _chain, count as _count
from collections.abc import Callable as _Callable, Mapping as _Mapping, Collection as _Collection, Iterable as _Iterable, Set as _Set, MutableSet as _MutableSet, ItemsView as _ItemsView, Sequence as _Sequence
from collections import defaultdict as _defaultdict
from math import isqrt as _isqrt
from operator import add as _add, sub as _sub
from sys import maxsize as _sys_maxsize
import logging as _logging


# assorted utilities

def fit_to_epoch(i, epochs):
	epoch_offset = 0
	if isinstance(epochs, _Callable):
		epochs = map(epochs, _count())
	for epoch_index, current_epoch_offset in enumerate(epochs):
		if (i - epoch_offset) > current_epoch_offset:
			epoch_offset += current_epoch_offset
			continue
		break
	else:
		raise ValueError("exhausted epochs without fitting i")
	return epoch_index, epoch_offset


def ez_generator_interface(g):
	"""Handy wrapper for generator-driven program flows.

	Example usage:

	def g(questions=[("What's 3 + 3?", 6), ("What's 9 + 10?", 19)]):
		"Example generator function that yields queries expecting a reply"
		for question, correct_answer in questions:
			answer = yield question  # <- KEY LINE
			if int(answer) != correct_answer:
				raise ValueError("STUPID")

	for query, send in _ez_generator_interface(g()):
		prompt = '{}\\n> '.format(query)
		response = input(prompt)
		send(response)
	"""
	x = None; del x  # if -god forbid- there's a logic error in this code, an undefined variable error is appropriate
	awaiting_input = False
	stop_exc = None
	def send(value):
		nonlocal x, awaiting_input, stop_exc
		if not awaiting_input:
			raise TypeError("attempt to send() more than once in a loop")
		awaiting_input = False
		try:
			x = g.send(value)
		except StopIteration as e:
			stop_exc = e
	try:
		x = next(g)
	except StopIteration as e:
		# handle empty generator
		return e.value
	awaiting_input = True
	yield x, send
	while stop_exc is None:
		if awaiting_input:
			raise TypeError("attempt to advance generator without send()")
		awaiting_input = True
		yield x, send
	return stop_exc.value


def generator_dialogue(g, *, input=input):
	for prompt, send in g:
		send(input(prompt))


def search_maxsatisfying(predicate, *, initial=0, _increasefunc=lambda n, base=_sys_maxsize+1: n*base):
	"""Return the largest integer *n* for which predicate(n) succeeds

	predicate must have a nowhere-positive derivative.
	initial value must satisfy predicate."""
	if initial < 0:
		offset = -initial
		return _search_maxsatisfying(lambda guess: predicate(guess - offset), initial=0, _increasefunc=_increasefunc) - offset
	lower_bound = initial
	upper_bound = lower_bound + 1
	if not predicate(lower_bound):
		raise ValueError("initial guess does not satisfy predicate")

	# 1. Exponential approach to establish upper-bound
	while predicate(upper_bound):
		lower_bound, upper_bound = upper_bound, _increasefunc(upper_bound)
	guess = lower_bound

	# 2. Binary search
	while (upper_bound - lower_bound) > 1:
		guess = lower_bound + (upper_bound - lower_bound) // 2
		if not predicate(guess):
			upper_bound = guess
			guess = lower_bound
		else:
			lower_bound = guess

	assert predicate(guess) and not predicate(guess+1)
	return guess


def last_qualified(predicate, iterable, /, return_if_exhausted=True):
	"""
	Consumes iterable or sequence `iterable` until finding an item
	not satisfying `predicate`, or until exhausted, then returns the last item
	which satisfied `predicate`.

	Raises ValueError if `iterable` is empty.

	Raises ValueError if the first item from `iterable` does not satisfy `predicate`.

	If `return_if_exhausted=False` is passed, raises ValueError when `iterable` is
	non-empty and exhausts with all items satisfying `predicate`.
	"""
	iterator = iter(iterable)
	try:
		cur = next(iterator)
	except StopIteration:
		raise ValueError("empty iterable") from None
	if not predicate(cur):
		raise ValueError("iterable begun with a non-qualified item")
	prev = cur
	for cur in iterator:
		if not predicate(cur):
			return prev
		prev = cur
	else:
		if return_if_exhausted:
			return cur
		else:
			raise ValueError("iterable exhausted with all items qualified")


# Multiset class

def _op_symmdiff(a, b):
	return abs(a - b)

def _op_softsub(a, b):
	return max(0, a - b)

def _op_replace(a, b):
	return b

class Multiset:
	__slots__ = ('__ddict', )
	def __init__(self, collection_or_mapping=None):
		self.__ddict = _defaultdict(int)
		if collection_or_mapping is not None:
			self.__include(collection_or_mapping, op=_add)

	# Public Misc. methods
	def __iter__(self):
		# guaranteed: Multiset(list(Multiset(x))) == Multiset(x)
		yield from _chain.from_iterable(_starmap(_repeat, self._multiplicity_items))
	def count(self, elem):
		# like list.count() but O(1)
		return self.__getcount(elem)
	def extend(self, other):
		# like list.extend()
		self.__include(other, op=_add)
	def __repr__(self):
		if _isqrt(len(self)) > len(self._support):
			# Alternate compact representation for sets with EXCESSIVE duplication
			# (when the set's cardinality is greater than the SQUARE of its support's)
			return f"{self.__class__.__name__}({self._asdict()!r})"
		return f"{self.__class__.__name__}({self._aslist()!r})"
	def __str__(self):
		# simplified representation if cast to string
		return str(self._aslist())

	# Public Set-like Methods
	def __len__(self):
		# TOTAL number of elements, including repeats.
		# i.e., len(list(x)) == len(Multiset(x))
		# if you want the number of UNIQUE elements, see len(ms._elements).
		return sum(self._multiplicities)
	def __bool__(self):
		# bool-cast works as expected for a a collection
		return any(self._multiplicities)
	def __contains__(self, elem):
		# "in" operator works as expected for a collection
		if isinstance(elem, _MutableSet):
			elem = frozenset(elem)
		return self.count(elem) > 0
	def isdisjoint(self, other):
		"Return `True` if the set has no elements in common with *other*. Sets are disjoint if and only if their intersection is the empty set."
		if not isinstance(other, Multiset):
			if isinstance(other, (_Collection)):
				other = Multiset(other)
			else:
				raise TypeError(type(other))
		return not self._get_common_support(other)
	def issubset(self, other, *, proper=False):
		"""Test whether every element in the set is at least as multiplicitous in *other*.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Inclusion"""
		if not isinstance(other, Multiset):
			if isinstance(other, (_Collection)):
				other = Multiset(other)
			else:
				raise TypeError(type(other))
		return all(self.count(elem) <= other.count(elem) for elem in self._support) and ((not proper) or (self != other))
	def issuperset(self, other, *, proper=False):
		"""Test whether every element in *other* is at least as multiplicitous in the set.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Inclusion"""
		if not isinstance(other, Multiset):
			if isinstance(other, (_Collection)):
				other = Multiset(other)
			else:
				raise TypeError(type(other))
		return all(self.count(elem) >= other.count(elem) for elem in other._support) and ((not proper) or (self != other))
	def union(self, *others):
		"""Return a new set with element multiplicity unioned from the set and all others.

		NOTE that Multiset("aab").union("b") == Multiset("aab")
		https://en.wikipedia.org/wiki/Multiset#:~:text=Union

		If you want Multiset("aab").some_operation("b") == Multiset("aabb"),
		use operator.add(), or Multiset.extend() if mutating."""
		result = self.copy()
		result.update(*others)
		return result
	def intersection(self, *others):
		"""Return a new set with element multiplicities common to the set and all others.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Intersection"""
		result = self.copy()
		result.intersection_update(*others)
		return result
	def difference(self, *others):
		"""Return a new set with element multiplicities in the set that exceed the sum of the others.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Difference"""
		result = self.copy()
		result.difference_update(*others)
		return result
	def symmetric_difference(self, other):
		"""Return a new set with element multiplicities only of which one set exceeds another.

		Similar to https://en.wikipedia.org/wiki/Multiset#:~:text=Difference
		except that abs(m1 - m2) is used instead of max(m1 - m2, 0)"""
		result = self.copy()
		result.symmetric_difference_update(other)
		return result
	def copy(self):
		"Return a shallow copy of the set."
		return Multiset(self)
	def update(self, *others):
		"""Update the set with element multiplicity unioned from the set and all others.

		NOTE that Multiset("aab").update("bc") results in Multiset("aabc")
		https://en.wikipedia.org/wiki/Multiset#:~:text=Union

		If you want Multiset("aab").some_operation("bc") resulting in Multiset("aabbc"),
		use operator.iadd or Multiset.extend()."""
		for other in others:
			self.__include(other)
	def intersection_update(self, *others):
		"""Update the set, keeping only element multiplicities at least found in it and all others.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Intersection"""
		for other in others:
			self.__revise(other.count, op=min)
	def difference_update(self, *others):
		"https://en.wikipedia.org/wiki/Multiset#:~:text=Difference"
		for other in others:
			self.__include(other, op=_op_softsub)
	def symmetric_difference_update(self, *others):
		"""Update the set, keeping only element multiplicities of which one set exceeds another.

		Similar to https://en.wikipedia.org/wiki/Multiset#:~:text=Difference
		except that abs(m1 - m2) is used instead of max(m1 - m2, 0)"""
		for other in others:
			self.__include(other, op=_op_symmdiff)
	def add(self, elem):
		"Add single element *elem* to the set."
		self.__addcount(elem, 1)
	def remove(self, elem):
		"Remove single element *elem* from the set. Raises `KeyError` if *elem* is not present in the set."
		if isinstance(elem, _MutableSet):
			elem = frozenset(elem)
		try:
			self__addcount(elem, -1)
		except ValueError:
			raise KeyError(elem) from None
	def discard(self, elem):
		"Completely remove element *elem* from the set if it is present."
		if isinstance(elem, _MutableSet):
			elem = frozenset(elem)
		self.__setcount(elem, 0)
	def pop(self):
		"Remove and return an arbitrary element from the set. Raises `KeyError` if the set is empty."
		try:
			elem = next(iter(self._support))
			self.remove(elem)
			return elem
		except StopIteration:
			raise KeyError('pop from an empty Multiset') from None
	def clear(self):
		"Remove all elements from the set."
		self.__revise(lambda _: 0, op=_op_replace)

	# Internal Methods
	def __include(self, obj, *, op=max):
		for elem, multiplicity in Multiset.__to_multiplicity_items(obj):
			self.__addcount(elem, multiplicity, op=op)
	def __revise(self, func, *, op):
		for elem in list(self._support):
			self.__addcount(elem, func(elem), op=op)
	def __getcount(self, elem):
		return self.__ddict[elem]
	def __setcount(self, elem, count):
		if count > 0:
			self.__ddict[elem] = int(count)
		elif count == 0:
			del self.__ddict[elem]
		else:
			raise ValueError({elem: count})
	def __addcount(self, elem, count, *, op=_add):
		newcount = op(self.__getcount(elem), count)
		self.__setcount(elem, newcount)
	@property
	def _support(self):
		return self.__ddict.keys()
	def _get_joint_support(self, other):
		return self._support | other._support
	def _get_common_support(self, other):
		return self._support ^ other._support
	@property
	def _multiplicities(self):
		return self.__ddict.values()
	@property
	def _multiplicity_items(self):
		return self.__ddict.items()
	@staticmethod
	def __to_multiplicity_items(obj):
		if isinstance(obj, _Mapping):
			# e.g. collections.Counter
			return obj.items()
		elif isinstance(obj, _ItemsView):
			# e.g. collections.Counter.items()
			return obj
		elif isinstance(obj, Multiset):
			# ...
			return obj._multiplicity_items
		else:
			# e.g. set, list, frozenset, tuple
			assert isinstance(obj, _Collection)
			return zip(obj, _repeat(1))

	# Efficient type-recast methods
	def _aslist(self, sortkey=lambda x: (id(type(x)), x)):
		"list, of all elements, sorted iff possible."
		try:
			return sorted(self, key=sortkey)
		except (TypeError, AttributeError):
			return list(self)
	def _asdict(self):
		"Mapping from all present elements to their counts"
		return dict(self._multiplicity_items)
	def _asset(self):
		"unique elements"
		return set(self._support)

	# Operator Methods
	def __eq__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self._multiplicity_items == other._multiplicity_items
	def __le__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self.issubset(other)
	def __lt__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self <= other and self != other
	def __ge__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self.issuperset(other)
	def __gt__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self >= other and self != other
	def __add__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		result = self.copy()
		result.extend(other)
		return result
	def __iadd__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		self.extend(other)
		return self
	def __or__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self.union(other)
	def __ior__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		self.update(other)
		return self
	def __and__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self.intersection(other)
	def __iand__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		self.intersection_update(other)
		return self
	def __sub__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self.difference(other)
	def __isub__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		self.difference_update(other)
		return self
	def __xor__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		return self.symmetric_difference(other)
	def __ixor__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, _Set):
				other = Multiset(other)
			else:
				return NotImplemented
		self.symmetric_difference_update(other)
		return self


# Bijection between integers and strings

def string_rank(s, k, ord=ord):
	"Given string *s* from underlying alphabet of size *k*, return a unique integer representative."
	i = 0
	offset = 0
	for j, c in enumerate(map(ord, (s))):
		assert 0 <= c < k
		i = i*k + c
		offset += k**j
	return i + offset

def _str_ish(chr=chr):
	return lambda it: str().join(map(chr, it))

def string_unrank(i, k, t=_str_ish()):
	"Given unique integer representative *i* of a string from underlying alphabet of size *k*, return that string."
	length, offset = fit_to_epoch(i, lambda l: k**l)
	i -= offset
	l = []
	for j in range(length):
		i, c = divmod(i, k)
		l.append(c)
	assert i == 0
	l.reverse()
	return t(l)


# Loose variant of https://en.wikipedia.org/wiki/DEC_RADIX_50

A50 = ' 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ\u001F\u0017\u001B'

def rank50(s):
	s = s.upper()
	s = s.replace('\t', '\u001F')
	s = s.replace('\n', '\u0017')
	s = s.replace('\\', '\u001B')
	return string_rank(s.upper(), len(A50), A50.index)

def unrank50(i):
	s = string_unrank(i, len(A50), _str_ish(chr=A50.__getitem__))
	return s

def rank_octetstring(s):
	return string_rank(s, 2**8, ord=int)

def unrank_octetstring(i):
	return string_unrank(i, 2**8, t=bytes)


# class to model mixed-radix integers

class MixedBase:
	def __init__(self, base, repeat=False):
		if not isinstance(base, _Sequence):
			if isinstance(base, _Collection):
				_logging.warning(f"attempt to create MixedBase out of non-ordered {base!r}")
			else:
				_logging.warning(f"attempt to create MixedBase out of potentially non-finite {base!r}")
		if repeat:
			raise NotImplementedError("non-finite base")
		self.base = tuple(base)
	def __repr__(self):
		return f'{self.__class__.__name__}({list(self.base)!r})'
	@property
	def order(self):
		return _prod(self.base)
	@property
	def max(self):
		return self.order - 1
	def to_int(self, value):
		i = 0
		for b, digit in zip(reversed(self.base), value, strict=True):
			if not 0 <= digit < b:
				raise ValueError("digit out of range")
			i = i * b + digit
		return i
	def __int__(self):
		return self.to_int()
	def from_int(self, i):
		value = ...
		for b in self.base:
			i, digit = divmod(i, b)
			value.append(digit)
		if i:
			raise ValueError("integer out of range")
		value.reverse()
		return tuple(value)

