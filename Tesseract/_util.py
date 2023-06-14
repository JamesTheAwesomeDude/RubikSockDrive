from functools import reduce as _reduce, wraps as _wraps
from itertools import repeat as _repeat, starmap as _starmap, chain as _chain, count as _count
from collections.abc import Callable as _Callable, Mapping as _Mapping, Collection as _Collection, Iterable as _Iterable, Set as _Set, MutableSet as _MutableSet, ItemsView as _ItemsView, Sequence as _Sequence
from collections import defaultdict as _defaultdict
from math import isqrt as _isqrt, prod as _prod
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
	for prompt, send in ez_generator_interface(g):
		send(input(f"{prompt}\n> "))


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

