"""Multiset implementation.

"""

__all__ = ["Multiset"]


from sortedcontainers import SortedList  # https://pypi.org/project/sortedcontainers/

from collections import Counter, deque
from collections.abc import Mapping, Sequence, Set, MutableSet, Collection
from functools import reduce
from itertools import chain, groupby, repeat, starmap
from math import isqrt
from numbers import Real


class Multiset(MutableSet):
	"""Multiset is a mutable multiset.

	Multiset values must be hashable. The hash of values
	must not change while they are stored in the Multiset.

	Mutable set methods:

	* :func:`Multiet.__contains__`
	* :func:`Multiset.__iter__`
	* :func:`Multiset.__len__`
	* :func:`Multiset.add`
	* :func:`Multiset.discard`

	Methods for removing values:

	* :func:`Multiset.clear`
	* :func:`Multiset.pop`
	* :func:`Multiset.remove`

	Set-operation methods:

	* :func:`Multiset.difference`
	* :func:`Multiset.difference_update`
	* :func:`Multiset.intersection`
	* :func:`Multiset.intersection_update`
	* :func:`Multiset.symmetric_difference`
	* :func:`Multiset.symmetric_difference_update`
	* :func:`Multiset.union`
	* :func:`Multiset.update`

	Methods for miscellany:

	* :func:`Multiset.copy`
	* :func:`Multiset.count`
	* :func:`Multiset.extend`
	* :func:`Multiset.__repr__`

	Multiset comparisons use subset and superset relations. Two multisets
	are equal if and only if every element of each multiset has at least as
	great multiplicity in the other (each is a subset of the other). A multiset
	is less than another multiset if and only if the first multiset is a proper
	subset of the second multiset (is a subset, but is not equal). A multiset is
	greater than another multiset if and only if the first multiset is a
	proper superset of the second multiset (is a superset, but is not equal).
	"""
	__slots__ = ['__sortedlist']

	def __init__(self, iterable=None):
		"""Initialize multiset instance.

		Optional `iterable` argument provides an initial iterable of values to
		initialize the multiset.
		"""
		self.__sortedlist = SortedList(key=hashable_universal_key)
		if iterable is not None:
			self.extend(iterable)


	def __repr__(self):
		if isqrt(len(self)) > len(self._asset()):
			# Alternate compact representation for sets with EXCESSIVE duplication
			# (when the set's cardinality is greater than the SQUARE of its support's)
			return f"{self.__class__.__name__}.from_counter({self._asdict()!r})"
		return f"{self.__class__.__name__}({self._aslist()!r})"


	# Public Misc. methods

	@classmethod
	def from_counter(cls, counter):
		"""Convert a collections.Counter into a Multiset

		"""
		return cls.from_multiplicities(counter.items())


	@classmethod
	def from_multiplicities(cls, items):
		"""Convert an iterable of (element, multiplicity) tuples into a Multiset

		"""
		it = chain.from_iterable(starmap(repeat, items))
		return cls(it)


	def __iter__(self):
		return self.__sortedlist.__iter__()


	# Public Set-like Methods

	def __len__(self):
		# TOTAL number of elements, including repeats.
		# i.e., len(list(x)) == len(Multiset(x))
		# if you want the number of UNIQUE elements, see len(ms._asset()).
		return len(self.__sortedlist)


	def __bool__(self):
		# bool-cast works as expected for a a collection
		# if the set is empty, it's falsy; if the set has any element in it, it's truthy
		return bool(self.__sortedlist)


	def __contains__(self, elem):
		# "in" operator works as expected for a set
		if isinstance(elem, MutableSet):
			elem = frozenset(elem)
		return (elem in self.__sortedlist)


	def isdisjoint(self, other):
		"Return `True` if the set has no elements in common with *other*. Sets are disjoint if and only if their intersection is the empty set."
		other = Multiset._maybe_cast_collection(other)

		return not any(self.__intersection_items(other, delta=False))


	def issubset(self, other):
		"""Test whether every element in the set is at least as multiplicitous in *other*.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Inclusion"""
		other = Multiset._maybe_cast_collection(other)

		return not any(self.__intersection_items(other, delta=True))


	def issuperset(self, other):
		"""Test whether every element in *other* is at least as multiplicitous in the set.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Inclusion"""
		other = Multiset._maybe_cast_collection(other)

		return not any(self.__union_items(other, delta=True))


	def union(self, *others):
		"""Return a new set with element multiplicity unioned from the set and all others.

		NOTE that Multiset("aab").union("b") == Multiset("aab")
		https://en.wikipedia.org/wiki/Multiset#:~:text=Union

		If you want Multiset("aab").some_operation("b") == Multiset("aabb"),
		use operator.add(), or Multiset.extend() if mutating."""
		others = map(Multiset._maybe_cast_collection, others)

		return Multiset.from_multiplicities(self.__union_items(*others, delta=False))


	def intersection(self, *others):
		"""Return a new set with element multiplicities common to the set and all others.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Intersection"""
		others = map(Multiset._maybe_cast_collection, others)

		return Multiset.from_multiplicities(self.__intersection_items(*others, delta=False))


	def difference(self, *others):
		"""Return a new set with element multiplicities in the set that exceed the sum of the others.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Difference"""
		others = map(Multiset._maybe_cast_collection, others)

		return Multiset.from_multiplicities(self.__difference_items(*others, delta=False))


	def symmetric_difference(self, other):
		"""Return a new set with element multiplicities only of which one set exceeds another.

		Similar to `Multiset.difference_update`
		except that abs(m1 - m2) is used instead of max(0, m1 - m2)"""
		other = Multiset._maybe_cast_collection(other)

		return Multiset.from_multiplicities(self.__symmetric_difference_items(other, delta=False))


	def copy(self):
		"Return a shallow copy of the set."
		return Multiset(self)


	def update(self, *others):
		"""Update the set with element multiplicity unioned from the set and all others.

		NOTE that Multiset("aab").update("bc") results in Multiset("aabc")
		https://en.wikipedia.org/wiki/Multiset#:~:text=Union

		If you want Multiset("aab").some_operation("bc") resulting in Multiset("aabbc"),
		use operator.iadd or Multiset.extend()."""
		others = map(Multiset._maybe_cast_collection, others)
		deltas = list(self.__union_items(*others, delta=True))
		map_immed_noretval(self.__add_quantity, deltas, splat=True)


	def intersection_update(self, *others):
		"""Update the set, keeping only element multiplicities at least found in it and all others.

		https://en.wikipedia.org/wiki/Multiset#:~:text=Intersection"""
		others = map(Multiset._maybe_cast_collection, others)
		deltas = list(self.__intersection_items(*others, delta=True))
		map_immed_noretval(self.__remove_quantity, deltas, splat=True)


	def difference_update(self, *others):
		"https://en.wikipedia.org/wiki/Multiset#:~:text=Difference"
		others = map(Multiset._maybe_cast_collection, others)
		deltas = list(self.__difference_items(*others, delta=True))
		map_immed_noretval(self.__remove_quantity, deltas, splat=True)


	def symmetric_difference_update(self, other):
		"""Update the set, keeping only element multiplicities of which one set exceeds another.

		Similar to `Multiset.difference_update`
		except that abs(m1 - m2) is used instead of max(m1 - m2, 0)"""
		other = Multiset._maybe_cast_collection(other)
		deltas = list(self.__symmetric_difference_items(other, delta=True))
		map_immed_noretval(self.__include_quantity, deltas, splat=True)


	def add(self, elem):
		"Add single element *elem* to the set."
		self.extend([elem])


	def remove(self, elem):
		"Remove single element *elem* from the set. Raises `KeyError` if *elem* is not present in the set."
		self.__remove_quantity(elem, 1)


	def discard(self, elem):
		"Completely remove element *elem* from the set if it is present."
		if isinstance(elem, MutableSet):
			elem = frozenset(elem)
		while elem in self:
			self.__sortedlist.discard(elem)


	def pop(self):
		"Remove and return an arbitrary element from the set. Raises `KeyError` if the set is empty."
		if not self:
			raise KeyError('pop from an empty Multiset')
		return self.__sortedlist.pop(0)


	def clear(self):
		"Remove all elements from the set."
		self.__sortedlist.clear()


	# Public "bonus" methods, beyond the `set` interface

	def count(self, elem):
		# like list.count()
		return self.__sortedlist.count(elem)


	def extend(self, iterable):
		# operator.iadd
		# like list.extend(); NOT like set.update()
		self.__sortedlist.update(iterable)


	def __str__(self):
		# simplified representation if cast to string
		return str(self._aslist())


	# Internal Methods

	@classmethod
	def _maybe_cast_collection(cls, obj):
		if not isinstance(obj, cls):
			if isinstance(obj, Collection):
				return cls(obj)
			else:
				raise TypeError(type(obj))
		return obj


	def __add_quantity(self, elem, count):
		self.extend(repeat(elem, count))


	def __remove_quantity(self, elem, count):
		map_immed_noretval(self.__sortedlist.remove, repeat(elem, count), splat=True)


	def __include_quantity(self, elem, count):
		if count < 0:
			self.__remove_quantity(elem, -count)
		else:
			self.__add_quantity(elem, count)


	def __union_items(self, *others, delta):
		it = joint_group_count(self, *others)
		if not delta:
			return ((elem, max(counts)) for elem, counts in it if max(counts) > 0)
		return ((elem, max(counts) - counts[0]) for elem, counts in it if max(counts) > counts[0])


	def __intersection_items(self, *others, delta):
		it = joint_group_count(self, *others)
		if not delta:
			return ((elem, min(counts)) for elem, counts in it if min(counts) > 0)
		return ((elem, counts[0] - min(counts)) for elem, counts in it if min(counts) < counts[0])


	def __difference_items(self, *others, delta):
		it = joint_group_count(self, *others)
		if not delta:
			return ((elem, reduce(soft_diff, counts)) for elem, counts in it if reduce(soft_diff, counts) > 0)
		return ((elem, counts[0] - reduce(soft_diff, counts)) for elem, counts in it if reduce(soft_diff, counts) < counts[0])


	def __symmetric_difference_items(self, other, *, delta):
		it = joint_group_count(self, other)
		if not delta:
			return ((elem, symm_diff(self_count, other_count)) for elem, (self_count, other_count) in it if self_count != other_count)
		return ((elem, symm_diff(self_count, other_count) - counts[0]) for elem, (self_count, other_count) in it if other_count > 0)


	def _aslist(self):
		return list(self.__sortedlist)


	def _asdict(self):
		return {elem: count for elem, count in self.__difference_items(delta=False)}


	def _asset(self):
		# quasi-abstract method; may be optimized in deduplicating implementations.
		return set(self)


	# Operator Methods

	def __eq__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return not any(self.__symmetric_difference_items(other, delta=False))


	def __le__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self.issubset(other)


	def __lt__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self <= other and self != other


	def __ge__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self.issuperset(other)


	def __gt__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self >= other and self != other


	def __add__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		result = self.copy()
		result.extend(other)
		return result


	def __iadd__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		self.extend(other)
		return self


	def __or__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self.union(other)


	def __ior__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		self.update(other)
		return self


	def __and__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self.intersection(other)


	def __iand__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		self.intersection_update(other)
		return self


	def __sub__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self.difference(other)


	def __isub__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		self.difference_update(other)
		return self


	def __xor__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		return self.symmetric_difference(other)


	def __ixor__(self, other):
		if not isinstance(other, Multiset):
			if not isinstance(other, (Set, list)):
				return NotImplemented
			other = Multiset(other)
		self.symmetric_difference_update(other)
		return self


def exhaust_iterable(it):
	deque(it, 0)


def map_immed_noretval(f, it, splat=False):
	exhaust_iterable((starmap if splat else map)(f, it))


def soft_diff(a, b):
	return max(0, a - b)


def symm_diff(a, b):
	return abs(a - b)


def joint_groupby(*iterables, key=None, ordered=True):
	"""Like itertools.groupby, but to work through collections of iterables simultaneously.
	If the value type (or the return type of key) is not comparable, you MUST pass ordered=False.

	Example: [(x, tuple(sum(1 for _ in group) for group in groups)) for x, groups in joint_groupby(...)]"""
	if key is None:
		key = lambda x: x
	iterables = [iter(it) for it in iterables]
	stop = object()
	buffer = [next(it, stop) for it in iterables]

	if ordered:
		def _choice(vals, key=lambda val: (0, val) if val is not stop else (1, )):
			return min(vals, default=stop, key=key)
	else:
		def _choice(vals):
			return next(iter(vals), stop)

	def _grouper(i, tgtkey):
		if buffer[i] is stop:
			return
		it = iterables[i]
		while buffer[i] is not stop and key(buffer[i]) == tgtkey:
			yield buffer[i]
			buffer[i] = next(it, stop)

	# 1. Acquire current group
	# (If multiple iterables yield, choose the LEAST as keyed by the user)
	while (tgtval := _choice(buffer)) is not stop:
		tgtkey = key(tgtval)

		# 2. Yield grouper bundle
		groupers = tuple(_grouper(i, tgtkey) for i in range(len(iterables)))
		yield (tgtval, groupers)

		# 3. Before next iteration, advance/flush groupers
		map_immed_noretval(exhaust_iterable, groupers)


def joint_group_count(*iterables, **k):
	for x, groups in joint_groupby(*iterables, **k):
		yield x, tuple(sum(1 for _ in group) for group in groups)


def total_group_count(*iterables, **k):
	for x, groups in joint_groupby(*iterables, **k):
		yield x, tuple(sum(1 for group in groups for _ in group))


def hashable_universal_key(obj):
	if isinstance(obj, Real):
		# Numbers are first, sorted numerically
		return (0, obj)
	elif isinstance(obj, tuple):
		# Immutable sequences are second, sorted lexographically, by this same definition
		return (1, tuple(map(hashable_universal_key, obj)))
	else:
		# Non-numeric non-sequence immutables are third, arbitrarily
		return (2, hash(obj))


def universal_key(obj):
	if isinstance(obj, Real):
		return (0, obj)
	elif isinstance(obj, tuple):
		return (1, tuple(map(universal_key, obj)))
	else:
		try:
			return (2, hash(obj))
		except TypeError:
			return (-1, id(obj))
