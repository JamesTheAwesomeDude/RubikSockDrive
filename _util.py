from itertools import count as _count
from functools import reduce as _reduce
from itertools import repeat as _repeat, starmap as _starmap, chain as _chain
from collections.abc import Callable as _Callable, Mapping as _Mapping, Collection as _Collection
from collections import defaultdict as _defaultdict
from math import isqrt as _isqrt
from sys import maxsize as _sys_maxsize

_N = 43252003274489856000


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

class Multiset:
	__slots__ = ('__ddict', )
	# Public Methods
	def __init__(self, collection_or_mapping):
		self.__ddict = _defaultdict(int)
		if isinstance(collection_or_mapping, _Mapping):
			items = collection_or_mapping.items()
		else:
			items = zip(collection_or_mapping, _repeat(1))
		for elem, count in items:
			self.__addcount(elem, count)
	def __len__(self):
		return sum(self._quantities())
	def __contains__(self, elem):
		return self.count(elem) > 0
	def __iter__(self):
		yield from _chain.from_iterable(_starmap(_repeat, self._items()))
	def __repr__(self):
		if _isqrt(len(self)) > len(self._elements()):
			# Alternate representation for sets with EXCESSIVE duplication
			return f"{self.__class__.__name__}({self._asdict()!r})"
		return f"{self.__class__.__name__}({self._aslist()!r})"
	def __str__(self):
		return str(self._aslist())
	def count(self, elem):
		return self.__getcount(elem)
	def add(self, elem):
		self.__addcount(elem, 1)
	def remove(self, elem):
		try:
			self__subcount(elem, 1, permissive=False)
		except ValueError:
			raise KeyError(elem) from None
	def pop(self):
		try:
			elem = next(iter(self._elements()))
			self.remove(elem)
			return elem
		except StopIteration:
			raise KeyError('pop from an empty Multiset') from None

	# Internal Methods
	def __getcount(self, elem):
		return self.__ddict[elem]
	def __setcount(self, elem, count):
		if count > 0:
			self.__ddict[elem] = int(count)
		elif count == 0:
			del self.__ddict[elem]
		else:
			raise ValueError({elem: count})
	def __addcount(self, elem, count):
		newcount = self.__getcount(elem) + count
		if not count >= 0:
			raise ValueError({elem: count})
		self.__setcount(elem, newcount)
	def __subcount(self, elem, count, permissive=False):
		newcount = self.__getcount(elem) - count
		if not newcount >= 0:
			if permissive:
				newcount = 0
			else:
				raise ValueError({elem: oldcount - count})
		self.__setcount(elem, newcount)
	def _elements(self):
		"Unique elements"
		return self.__ddict.keys()
	def _quantities(self):
		"Components of len()"
		return self.__ddict.values()
	def _items(self):
		return self.__ddict.items()
	def _aslist(self):
		try:
			return sorted(self, key=lambda x: (id(type(x)), x))
		except (TypeError, AttributeError):
			return list(self)
	def _asdict(self):
		return dict(self.__ddict)

	# Operator Methods
	def __eq__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, (_Mapping, _Collection)):
				other = Multiset(other)
			else:
				return NotImplemented
		return self._asdict() == other._asdict()
	def __ge__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, (_Mapping, _Collection)):
				other = Multiset(other)
			else:
				return NotImplemented
		return all(self.count(elem) >= other.count(elem) for elem in set(self._elements()).union(other._elements()))
	def __gt__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, (_Mapping, _Collection)):
				other = Multiset(other)
			else:
				return NotImplemented
		return self >= other and self != other
	def __le__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, (_Mapping, _Collection)):
				other = Multiset(other)
			else:
				return NotImplemented
		return all(self.count(elem) <= other.count(elem) for elem in set(self._elements()).union(other._elements()))
	def __lt__(self, other):
		if not isinstance(other, Multiset):
			if isinstance(other, (_Mapping, _Collection)):
				other = Multiset(other)
			else:
				return NotImplemented
		return self <= other and self != other


# Bijection between integers and strings

def string_rank(s, k, ord=ord):
	i = 0
	offset = 0
	for j, c in enumerate(map(ord, (s))):
		assert 0 <= c < k
		i = i*k + c
		offset += k**j
	return i + offset

def _str_ish(chr):
	return lambda it: str().join(map(chr, it))

def string_unrank(i, k, t=_str_ish(chr=chr)):
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
	return string_rank(s.upper(), len(A50), A50.index)

def unrank50(i):
	s = string_unrank(i, len(A50), _str_ish(chr=A50.__getitem__))
	s = s.replace('\u0017', '\n')
	s = s.replace('\u001F', '\t')
	return s

def rank_octetstring(s):
	return string_rank(s, 2**8, ord=int)

def unrank_octetstring(i):
	return string_rank(s, 2**8, t=bytes)
