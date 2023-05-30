from functools import reduce as _reduce

def search_maxsatisfying(predicate, *, initial=0):
	"""Return the largest integer *n* for which predicate(n) succeeds

	predicate must have a nowhere-positive derivative.
	initial value must satisfy predicate."""
	lower_bound = initial
	upper_bound = lower_bound + 1
	if not predicate(lower_bound):
		raise ValueError(f"initial does not satisfy predicate")
	# 1. Exponential approach to establish upper-bound
	while predicate(upper_bound):
		upper_bound = upper_bound*2
	guess = lower_bound = (upper_bound - 1) and (upper_bound // 2)
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


def last_qualified(predicate, iterable, /, *, return_if_exhausted=True):
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
		raise ValueError("iterable exhausted with all items qualified")


DEC6 = bytes(range(32, 96)).decode('ascii')  # http://rabbit.eng.miami.edu/info/decchars.html


def crunch(s: str) -> int:
	"""Binary-pack a string into a single integer as DEC SIXBIT"""
	return _bitpack(bytes(DEC6.index(c) for c in s), n=6)


def uncrunch(i: int) -> str:
	"""Unpack an integer as a DEC SIXBIT binary-packed string; inverse of `crunch`"""
	return str().join(DEC6[j] for j in _bitunpack(i, n=6))


def _bitpack(l, n=8):
	return _reduce((lambda acc, cur: (acc << n | cur)), l, 0)


def _bitunpack(i, n=8):
	l = []
	mask = (1 << n) - 1
	while i:
		l.append(i & mask)
		i >>= n
	l.reverse()
	return l
