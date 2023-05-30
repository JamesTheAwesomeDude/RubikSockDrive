from math import comb as _comb
from itertools import count as _count

from _util import search_maxsatisfying as _search_maxsatisfying


_Multiset = list  # monkey-patch this if it please you; only ensure that __sorted__(), __iter__(), and __init__(elements: abc.Collection) are implemented.


def integer_to_multiset(i, k=None, n=43252003274489856000):
	# TODO: fix redundancy
	# https://discord.com/channels/834837272234426438/866699434116775946/1112819325666070539?invite=WZvZMVsXXR&referer=https://some.3b1b.co/
	if k is None:
		assert (n > 1) or (i == 0)
		k = next(k for k in _count(1) if multicomb(n, k) > i)
	nPrime = n + k - 1
	return combination_to_multiset(integer_to_combination(i, k, nPrime))


def multiset_to_integer(ms, n):
	return combination_to_integer(multiset_to_combination(ms))


#####


def combination_to_multiset(s):
	return _Multiset(elem - offset for offset, elem in enumerate(sorted(s)))


def multiset_to_combination(ms):
	return set(elem + offset for offset, elem in enumerate(sorted(ms)))


def multicomb(n, k):
	"https://en.wikipedia.org/wiki/Multiset#Counting_multisets"
	return _comb(n + k - 1, k)


def integer_to_combination(i, k, n):
	"https://en.wikipedia.org/wiki/Combinatorial_number_system#Finding_the_k-combination_for_a_given_number"
	s = set()
	universe = range(n)
	if not 0 <= i < _comb(n, k):
		raise ValueError(f"not 0 <= {i} < comb({n}, {k})")
	for j in range(k, 0, -1):
		elem = _search_maxsatisfying(lambda n, r=j, N=i, comb=_comb: _comb(n, r) <= N)
		assert elem in universe
		assert elem not in s
		s.add(elem)
		i -= _comb(elem, j)
	assert i == 0
	return s


def combination_to_integer(s):
	"https://en.wikipedia.org/wiki/Combinatorial_number_system#Place_of_a_combination_in_the_ordering"
	return sum(_comb(elem, k+1) for k, elem in enumerate(sorted(s)))
