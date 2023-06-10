from math import comb as _comb
from itertools import count as _count

from . import Multiset
from ._util import search_maxsatisfying as _search_maxsatisfying, fit_to_epoch as _fit_to_epoch


def multicomb(n, k):
	"https://en.wikipedia.org/wiki/Multiset#Counting_multisets"
	return _comb(n + k - 1, k)


# Set-Multiset bijection

def combination_to_multiset(s):
	return Multiset(elem - offset for offset, elem in enumerate(sorted(s)))

def multiset_to_combination(ms):
	return set(elem + offset for offset, elem in enumerate(sorted(ms)))


# Multiset-Integer bijections

def integer_to_varmultiset(i, n):
	k, offset = _fit_to_epoch(i, lambda k: multicomb(n, k))
	return integer_to_multiset(i - offset, k)

def varmultiset_to_integer(ms, n):
	k = len(ms)
	offset = sum(multicomb(n, k) for k in range(k))
	return multiset_to_integer(ms) + offset


def multiset_to_integer(ms):
	return combination_to_integer(multiset_to_combination(ms))

def integer_to_multiset(i, k):
	return combination_to_multiset(integer_to_combination(i, k))


# Integer-Combination bijection

def integer_to_varcombination(i, n):
	k, epoch_offset = _fit_to_epoch(i, lambda k: _comb(n, k))
	return integer_to_combination(i - epoch_offset, k)

def varcombination_to_integer(i, n):
	k = len(ms)
	epoch_offset = sum(_comb(n, k) for k in range(k))
	return combination_to_integer(ms) + epoch_offset


def integer_to_combination(i, k):
	"https://en.wikipedia.org/wiki/Combinatorial_number_system#Finding_the_k-combination_for_a_given_number"
	if i < 0:
		raise ValueError(f"can't represent {i} as a {k}-combination (i too small)")
	if k < 1 and i > 0:
		raise ValueError(f"can't represent {i} as a {k}-combination (k too small)")
	remainder = int(i)
	s = set()
	for j in range(k, 0, -1):  # [k, k-1, ..., 1]
		elem = _search_maxsatisfying(lambda n: not _comb(n, j) > remainder)
		assert elem not in s
		s.add(elem)
		remainder -= _comb(elem, j)
	assert remainder == 0, {'i': i, 'k': k}
	return s

def combination_to_integer(s):
	"https://en.wikipedia.org/wiki/Combinatorial_number_system#Place_of_a_combination_in_the_ordering"
	return sum(_comb(elem, j) for j, elem in enumerate(sorted(s), start=1))
