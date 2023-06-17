
from . import Multiset, Cube
from .macaulay import integer_to_varmultiset, varmultiset_to_integer
from ._util import (
	rank50 as _rank50, unrank50 as _unrank50,
	rank_octetstring as _rank_octetstring, unrank_octetstring as _unrank_octetstring,
	MixedBase as _MixedBase,
	generator_dialogue as _generator_dialogue)

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
	for fcolorprompt1, fcolorprompt2 in map(lambda edge: map(Cube._COLOR_NAMES.__getitem__, edge), Cube._CANON_SOLVED_STATE[0]):
		ecolor1 = yield f"What color is the sticker on the edge piece ADJACENT TO the {fcolorprompt1} center face of {name}, in the direction of the {fcolorprompt2} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)"
		ecolor2 = yield f"What color is the sticker on the edge piece ADJACENT TO the {fcolorprompt2} center face of {name}, in the direction of the {fcolorprompt1} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)"
		input_edges.append(tuple(map(Cube._COLORS.index, [ecolor1, ecolor2])))

	input_corners = []
	for fcolorprompt1, fcolorprompt2, fcolorprompt3 in map(lambda corner: map(Cube._COLOR_NAMES.__getitem__, corner), Cube._CANON_SOLVED_STATE[1]):
		ccolor1 = yield f"Regarding the corner which is BETWEEN the {fcolorprompt1}, {fcolorprompt2}, and {fcolorprompt3} center faces of {name}: What color is the sticker which is CLOSEST TO the {fcolorprompt1} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)"
		ccolor2 = yield f"Regarding the corner which is BETWEEN the {fcolorprompt1}, {fcolorprompt2}, and {fcolorprompt3} center faces of {name}: What color is the sticker which is CLOSEST TO the {fcolorprompt2} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)"
		ccolor3 = yield f"Regarding the corner which is BETWEEN the {fcolorprompt1}, {fcolorprompt2}, and {fcolorprompt3} center faces of {name}: What color is the sticker which is CLOSEST TO the {fcolorprompt3} center face?\n(Type a single lowercase letter, w or g or r or b or o or y.)"
		input_corners.append(tuple(map(Cube._COLORS.index, [ccolor1, ccolor2, ccolor3])))

	return Cube((input_edges, input_corners, Cube._CANON_SOLVED_STATE[2]))


def bag2data_wizard():
	k = yield "How many cubes do you have?"
	k = int(k)
	bag = []
	for i in range(k):
		input_cube = yield from _cube_input_wizard(name=f"Cube \x23{i+1}")
		bag.append(cube2i(input_cube))
	is_a50 = yield 'Were you expecting a RADIX-50 TEXT message?\nIf so, type "50" (without the quotes) and press Enter. If not, just press Enter.'
	is_a50 = {'': False, '50': True}[is_a50]
	return bag2data(bag, is_a50=is_a50)


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
