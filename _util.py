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
