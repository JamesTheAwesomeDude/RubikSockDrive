
from . import Multiset
from .macaulay import integer_to_varmultiset, varmultiset_to_integer
from ._util import (
	rank50 as _rank50, unrank50 as _unrank50,
	rank_octetstring as _rank_octetstring, unrank_octetstring as _unrank_octetstring,
	MixedBase as _MixedBase,
	generator_dialogue as _generator_dialogue)

from rubik.solve import Solver as _pglass_Solver

from math import prod as _prod
from itertools import count as _count
import re
import logging


__all__ = ["data2bag", "bag2data", "data2bag_wizard", "bag2data_wizard", "Cube", "RUBIKS_BASE"]


_N = 43252003274489856000


def data2bag(data):
	if isinstance(data, str):
		logging.warning("AUTO-CASTING STR TO RADIX-50 (30%-50% MORE STORAGE FOR VERY SIMPLE MESSAGES). OUTPUT WILL NEED TO BE DECODED WITH unrank50().")
		logging.warning("IF YOU MEANT TO USE UTF-8 OR SOMETHING, ENCODE IT FIRST INSTEAD OF PASSING str INTO data2bag().")
		data = _rank50(data)
	elif isinstance(data, bytes):
		data = _rank_octetstring(data)
	elif hasattr(data, 'encode'):
		data = _rank_octetstring(data.encode())
	representatives = integer_to_varmultiset(data, n=RUBIKS_BASE.order)
	return Multiset(map(Cube._from_int, representatives))


def data2bag_wizard(data):
	scrambles = data2bag(data)
	k = len(scrambles)
	for i, scramble in enumerate(scrambles):
		solve = TODO_SOLVE(scramble)
		scramble_instructions = -solve  # this depends on the Solution interface providing .__neg__()
		yield f"Scramble Cube \x23{i+1}/{k}:\n{scramble_instructions}\nPress Enter once the cube has been solved."  # str NOT repr since this is end-user-facing
	scramble_check = Multiset()
	for i, scramble in enumerate(scrambles):
		cube = yield from _cube_input_wizard("Cube \x23{i+1}/{k}", input=input)
		scramble_check.append(cube)
	if scramble_check != scrambles:
		raise RuntimeError(f"verification failed: {scramble_check!r} != {scrambles!r}")


def bag2data(bag, *, is_a50=False):
	i = varmultiset_to_integer(bag, n=RUBIKS_BASE.order)
	if is_dec6:
		data = _unrank50(i)
	else:
		data = _unrank_octetstring(i)
	return data


def _cube_input_wizard(name="the cube"):
	input_edges = []
	for fcolor1, fcolor2 in map(Cube._COLORS.__getitem__, Cube._CANON_SOLVED_STATE[0]):
		ecolor1 = yield f"What color is the sticker on the edge piece ADJACENT TO the {fcolor1} center face of {name}, in the direction of the {fcolor2} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)\n> "
		ecolor2 = yield f"What color is the sticker on the edge piece ADJACENT TO the {fcolor2} center face of {name}, in the direction of the {fcolor1} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)\n> "
		input_edges.append(tuple(map(Cube._COLORS.index, [ecolor1, ecolor2])))

	input_corners = []
	for fcolor1, fcolor2, fcolor3 in map(Cube._COLORS.__getitem__, Cube._CANON_SOLVED_STATE[1]):
		ccolor1 = yield f"Regarding the corner which is BETWEEN the {fcolor1}, {fcolor2}, and {fcolor3} center faces of {name}: What color is the sticker which is CLOSEST TO the {fcolor1} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)\n> "
		ccolor2 = yield f"Regarding the corner which is BETWEEN the {fcolor1}, {fcolor2}, and {fcolor3} center faces of {name}: What color is the sticker which is CLOSEST TO the {fcolor2} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)\n> "
		ccolor3 = yield f"Regarding the corner which is BETWEEN the {fcolor1}, {fcolor2}, and {fcolor3} center faces of {name}: What color is the sticker which is CLOSEST TO the {fcolor3} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)\n> "
		input_corners.append(tuple(map(Cube._COLORS.index, [ccolor1, ccolor2, ccolor3])))

	return Cube((input_edges, input_corners, Cube._CANON_SOLVED_STATE[2]))


def bag2data_wizard(*, input=input):
	is_a50 = {'': False, '50': True}[input('Were you expecting a RADIX-50 TEXT message?\nIf so, type "50" (without the quotes) and press Enter. If not, just press Enter.\n> ')]
	k = int(input("How many cubes do you have?\n> "))
	bag = []
	for i in range(k):
		input_cube = (yield from _cube_input_wizard(name=f"Cube \x23{i+1}"))
		bag.append(cube2i(input_cube))
	return bag2data(bag, is_a50=is_a50)


class Cube:
	"""Mutable class representing a Rubik's Cube.

	May represent "illegal" states.
	"""
	__slots__ = ('_edges', '_corners', '_centers')
	_EDGES = ('UL', 'UF', 'UR', 'UB', 'BL', 'FL', 'FR', 'BR', 'DL', 'DF', 'DR', 'DB')
	_CORNERS = ('UBL', 'UFL', 'UFR', 'UBR', 'DBL', 'DFL', 'DFR', 'DBR')
	_CENTERS = ('U', 'L', 'F', 'R', 'B', 'D')  # These are official face abbreviations
	_COLORS = ('w', 'g', 'r', 'b', 'o', 'y')
	_CANON_SOLVED_STATE = (
		((0, 1), (0, 2), (0, 3), (0, 4), (1, 4), (1, 2), (3, 2), (3, 4), (1, 5), (2, 5), (3, 5), (4, 5)),
		((0, 1, 4), (0, 2, 1), (0, 3, 2), (0, 4, 3), (5, 4, 1), (5, 1, 2), (5, 2, 3), (5, 3, 4)),
		((0,), (1,), (2,), (3,), (4,), (5,)))

	def __repr__(self):
		return f'{self.__class__.__name__}.fromsolverstring({self.solverstring!r})'

	def __str__(self):
		return self.solverstring

	@classmethod
	def fromsolverstring(cls, solverstring):
		return cls(cls.solverstring2cubies(solverstring))

	def copy(self):
		return self.__class__(self.state)

	@property
	def state(self):
		"Immutable representative of the current state (STABLE INTERFACE)"
		return tuple(tuple(tuple(cubie) for cubie in subset) for subset in self.cubies)

	@state.setter
	def state(self, state):
		self.cubies = state  # forward to cubies setter

	@property
	def cubies(self):
		# NOTE that this returns mutable accessors valid though the object's lifetime.
		# For example, this will mutate myCube:
		# c = myCube.cubies; c[1][0].twist(-1)
		# use Cube.state if you want a simple (and immutable!) representative.
		return self._edges, self._corners, self._centers

	@cubies.setter
	def cubies(self, cubies):
		edges, corners, centers = cubies
		if not (len(edges) == 12 and len(corners) == 8 and len(centers) == 6):
			raise ValueError("bad cubies")
		self._edges[:], self._corners[:], self._centers[:] = map(_EdgeCubie, edges), map(_CornerCubie, corners), map(_CenterCubie, centers)

	@property
	def solverstring(self):
		return self.cubies2solverstring(self.cubies)

	@solverstring.setter
	def _set_solverstring(self, solverstring):
		self.cubies = self.solverstring2cubies(solverstring)

	@property
	def is_legal(self):
		return all(value == 0 for value in self.orbit)

	@property
	def is_conceivable(self):
		# Weaker version of is_legal
		# Doesn't require pulling the *core* apart, at least
		return all(value == 0 for value in self.orbit[-2:])

	@property
	def orbit(self):
		"That which is changed by, and only by, illegal moves."
		# 1. Swap parity -- EZ, just sort the edges + sort the corners and see how long it took
		# 2. Flip parity -- for each edge piece, check if it can be rehomed without rotating the red or orange faces
		# 3. Corner twist parity -- pretend white and yellow are the same color, then simply calculate it
		# 4. Center chirality -- IGNORING/TODO
		# 5. Core-torsion -- IGNORING/TODO
		return self._swap_parity,\
		  self._edgeflip_parity,\
		  self._cornertwist_parity,\
		  self._centerchirality,\
		  self._centertwist_parity

	@property
	def _swap_parity(self):
		if self.state[2] != self._CANON_SOLVED_STATE[2]:
			raise NotImplementedError("TODO check to make sure this function works right in nonstandard orientations")

		working_model = self.copy()  # a property accessor musn't mutate the instance, for the love of god
		edges, corners, _ = working_model.cubies  # mutable accessors

		swaps = 0
		# TODO don't sort like a MORON lol

		for i, (current_edge, expect_stickers) in enumerate(zip(edges, map(frozenset, self._CANON_SOLVED_STATE[0]))):
			i_found, edge_found = next((i, edge) for i, edge in enumerate(edges) if edge.stickers == expect_stickers)
			if i != i_found:
				current_edge.swap(edge_found)
				swaps += 1

		for i, (current_corner, expect_stickers) in enumerate(zip(corners, map(frozenset, self._CANON_SOLVED_STATE[1]))):
			i_found, corner_found = next((i, corner) for i, corner in enumerate(corners) if corner.stickers == expect_stickers)
			if i != i_found:
				current_corner.swap(corner_found)
				swaps += 1

		return swaps % 2

	@property
	def _edgeflip_parity(self):

		flips = 0

		for i, edge in enumerate(edges):
			stickers_ordered = tuple(edge)
			if (0 in stickers_ordered):
				# White
				flips += stickers_ordered.index(0)
				continue
			if (5 in stickers_ordered):
				# Yellow
				flips += stickers_ordered.index(5)
				continue
			if (1 in stickers_ordered):
				# Green
				flips += stickers_ordered.index(1) ^ (i in [4, 5, 6, 7])
				continue
			if (3 in stickers_ordered):
				# Blue
				flips += stickers_ordered.index(3) ^ (i in [4, 5, 6, 7])
				continue
			raise ValueError(f"edge {edge} at index {i}")

		return flips % 2

	@property
	def _cornertwist_parity(self):
		twists = 0
		for corner in self.state[1]:
			for sticker in corner:
				if 0 in corner:
					twists += corner.index(0)
					continue
				if 5 in corner:
					twists += corner.index(5)
					continue
				raise ValueError("CORNER HAS NEITHER WHITE NOR YELLOW STICKERS, WTF")
		return twists % 3

	@property
	def _centerchirality(self):
		_, _, centers = self.cubies
		if self.state[2] == self._CANON_SOLVED_STATE[2]:
			return 0
		raise NotImplementedError("cube must be white-up, red-forward, and conceivable")  # TODO

	@property
	def _centertwist_parity(self):
		_, _, centers = self.cubies
		if self.state[2] == self._CANON_SOLVED_STATE[2]:
			return 0
		raise NotImplementedError("cube must be white-up, red-forward, and conceivable")  # TODO

	@classmethod
	def cubies2solverstring(cls, cubies):
		edges, corners, centers = cubies
		palette = cls._COLORS
		# https://www.google.com/search?q=cs+graduate+meme&tbm=isch
		return ''.join(
			(palette[cubies[i][j][k]])
			for i, j, k in [
				(1, 0, 0), (0, 3, 0), (1, 3, 0),
				(0, 0, 0), (2, 0, 0), (0, 2, 0),
				(1, 1, 0), (0, 1, 0), (1, 2, 0),

				(1, 0, 1), (0, 0, 1), (1, 1, 2),  (1, 1, 1), (0, 1, 1), (1, 2, 2),  (1, 2, 1), (0, 2, 1), (1, 3, 2),  (1, 3, 1), (0, 3, 1), (1, 0, 2),
				(0, 4, 0), (2, 1, 0), (0, 5, 0),  (0, 5, 1), (2, 2, 0), (0, 6, 1),  (0, 6, 0), (2, 3, 0), (0, 7, 0),  (0, 7, 1), (2, 4, 0), (0, 4, 1),
				(1, 4, 2), (0, 8, 1), (1, 5, 1),  (1, 5, 2), (0, 9, 1), (1, 6, 1),  (1, 6, 2), (0,10, 1), (1, 7, 1),  (1, 7, 2), (0,11, 1), (1, 4, 1),

				( 1,  5,  0), ( 0,  9,  0), ( 1,  6,  0),
				( 0,  8,  0), ( 2,  5,  0), ( 0, 10,  0),
				( 1,  4,  0), ( 0, 11,  0), ( 1,  7,  0)]
		)

	@classmethod
	def solverstring2cubies(cls, s):
		palette = cls._COLORS
		assert len(s) == 54
		edges = tuple(
			_EdgeCubie([palette.index(s[i]), palette.index(s[j])])
			for i, j in [
				( 3, 10), ( 7, 13), ( 5, 16), ( 1, 19),
				(21, 32), (23, 24), (27, 26), (29, 30),
				(48, 34), (46, 37), (50, 40), (50, 42)]
		)
		corners = tuple(
			_CornerCubie([palette.index(s[i]), palette.index(s[j]), palette.index(s[k])])
			for i, j, k in [
				( 0,  9, 20), ( 6, 12, 11), ( 8, 15, 14), ( 2, 18, 17),
				(51, 44, 33), (45, 35, 36), (47, 38, 39), (53, 41, 42)
			]
		)
		centers = tuple(
			_CenterCubie([palette.index(s[i])])
			for i, in [
				( 4,),
				(22,), (25,), (28,), (31,),
				(49,)
			]
		)
		return edges, corners, centers

	def do_move(self, move):
		logging.debug("Applying move")
		logging.debug(self)
		edges, corners, centers = self.cubies
		match move:
			case 'U':
				edges[0].swap(edges[3], edges[2], edges[1])
				corners[0].swap(corners[3], corners[2], corners[1])
			case 'U2':
				edges[0].swap(edges[2])
				edges[1].swap(edges[3])
				corners[0].swap(corners[2])
				corners[1].swap(corners[3])
			case 'Ui':
				edges[0].swap(edges[1], edges[2], edges[3])
				corners[0].swap(corners[1], corners[2], corners[3])
			case 'L':
				edges[4].swap(edges[0], edges[5], edges[8], flip=True)
				corners[0].swap(corners[1], corners[5], corners[4])
			case 'L2':
				edges[0].swap(edges[8])
				edges[4].swap(edges[5])
				corners[0].swap(corners[5])
				corners[1].swap(corners[4])
			case 'Li':
				edges[4].swap(edges[8], edges[5], edges[0], flip=True)
				corners[0].swap(corners[4], corners[5], corners[1])
			case 'F':
				edges[5].swap(edges[1], edges[6], edges[9])
				corners[1].swap(corners[2], corners[6], corners[5])
			case 'F2':
				edges[1].swap(edges[9])
				edges[6].swap(edges[5])
				corners[1].swap(corners[6])
				corners[2].swap(corners[5])
			case 'Fi':
				edges[5].swap(edges[9], edges[6], edges[1])
				corners[1].swap(corners[5], corners[6], corners[2])
			case 'R':
				edges[6].swap(edges[2], edges[7], edges[10], flip=True)
				corners[2].swap(corners[3], corners[7], corners[6])
			case 'R2':
				edges[6].swap(edges[7])
				edges[2].swap(edges[10])
				corners[2].swap(corners[7])
				corners[3].swap(corners[6])
			case 'Ri':
				edges[6].swap(edges[10], edges[7], edges[2], flip=True)
				corners[2].swap(corners[6], corners[7], corners[3])
			case 'B':
				edges[7].swap(edges[3], edges[4], edges[11])
				corners[3].swap(corners[0], corners[4], corners[7])
			case 'B2':
				edges[7].swap(edges[4])
				edges[3].swap(edges[11])
				corners[3].swap(corners[4])
				corners[0].swap(corners[7])
			case 'Bi':
				edges[7].swap(edges[11], edges[4], edges[3])
				corners[3].swap(corners[7], corners[4], corners[0])
			case 'D':
				edges[8].swap(edges[9], edges[10], edges[11])
				corners[5].swap(corners[6], corners[7], corners[4])
			case 'D2':
				edges[8].swap(edges[10])
				edges[9].swap(edges[11])
				corners[5].swap(corners[7])
				corners[6].swap(corners[4])
			case 'Di':
				edges[6].swap(edges[2], edges[7], edges[10])
				corners[2].swap(corners[3], corners[7], corners[6])

			# nonstandard "moves" that change the orbit
			case _ if (m := re.fullmatch(r'([UDBF][BFLR])^([UDBF][BFLR])', move)):
				# swap two edges, e.g. 'UL^UR' would swap the top-left and top-right edges
				target1 = edges[self._EDGES.index(m.group(1))]
				target2 = edges[self._EDGES.index(m.group(2))]
				target1.swap(target2)
			case _ if (m := re.fullmatch(r'!([UDBF][BFLR])', move)):
				# flip a single edge, e.g. '!UL' would flip the top-left edge
				target = edges[self._EDGES.index(m.group(1))]
				target.flip()
			case _ if (m := re.fullmatch(r'+([UD][BF][LR])(i)?', move)):
				# twist a corner
				target = corners[self._CORNERS.index(m.group(1))]
				distance = 1 if m.group(2) is not None else -1
				target.twist(distance)
			case _ if (m := re.fullmatch(r'([UD][BF][LR])^([UD][BF][LR])', move)):
				# swap two corners, e.g. 'UFL^UFR' would swap the top near left and top near right corners
				target1 = corners[self._CORNERS.index(m.group(1))]
				target2 = corners[self._CORNERS.index(m.group(2))]
				target1.swap(target2)
			case _ if (m := re.fullmatch(r'([UDBFLR])^([UDBFLR])', move)):
				# swap two centers, e.g. 'L^R' would swap the left and right centers
				target1 = centers[self._CENTERS.index(m.group(1))]
				target2 = centers[self._CENTERS.index(m.group(2))]
				target1.swap(target2)

		logging.debug(self)

	def __init__(self, cubies):
		self._edges, self._corners, self._centers = [None]*12, [None]*8, [None]*6
		self.state = cubies


class _Cubie:
	__slots__ = ('_value')

	#abstractclassvariable
	_len = object()

	def __init__(self, value):
		if len(value) != self._len:
			raise ValueError(f"bad cubie {value} (expected length {self._len}, got length {len(value)})")
		self._value = list(value)

	def __repr__(self):
		return f'{self.__class__.__name__}({self._value!r})'

	def __iter__(self):
		return iter(self._value)

	def __len__(self):
		return len(self._value)

	def __getitem__(self, index):
		return self._value[index]

	@property
	def stickers(self):
		return frozenset(self._value)

	def swap(self, *others):
		for other in others:
			if not isinstance(other, self.__class__):
				raise TypeError(other.__class__)
		values = list(list(cubie) for cubie in [self, *others])
		for target, value in zip([*others, self], values):
			target._value[:] = value

	def __eq__(self, other):
		if not isinstance(other, _Cubie):
			return NotImplemented
		return self._value == other._value

	def __sub__(self, other):
		if not isinstance(other, _Cubie):
			return NotImplemented
		if set(self._value) != set(other._value):
			return NotImplemented
		raise NotImplementedError("TODO")


class _EdgeCubie(_Cubie):
	_len = 2

	def swap(self, *others, flip=False):
		super().swap(*others)
		if flip:
			for edge in [self, *others]:
				edge.flip()

	def flip(self):
		self._value[1], self._value[0] = self._value[0], self._value[1]


class _CornerCubie(_Cubie):
	_len = 3

	def twist(self, distance=1):
		d0 = _posmod(0 + distance, 3)
		d1 = _posmod(1 + distance, 3)
		d2 = _posmod(2 + distance, 3)
		self._value[d0], self._value[d1], self._value[d2] = self._value[0], self._value[1], self._value[2]


class _CenterCubie(_Cubie):
	_len = 1


class _SuperCenterCubie(_CenterCubie):
	__slots__ = ('_orientation')

	def __repr__(self):
		args = [*self._value, self._orientation]
		return f'{self.__class__.__name__}({args!r})'

	def __init__(self, value):
		super().__init__(value[:-1])
		self._orientation = value[-1]
		raise NotImplementedError()


def _posmod(x, m):
	x = x % m
	if x < 0:
		return x + m
	return x


RUBIKS_BASE = _MixedBase([
	# EDGE PIECES
	12, 2,
	11, 2,
	10, 2,
	9,  2,
	8,  2,
	7,  2,
	6,  2,
	5,  2,
	4,  2,
	3,  2,
	2,  2,
	# CORNER PIECES
	8, 3,
	7, 3,
	6, 3,
	5, 3,
	4, 3,
	3, 3,
	   3,
])
