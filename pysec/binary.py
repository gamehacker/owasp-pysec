#!/usr/bin/python -OOBRStt
""""""
SPECIAL_CHARS = '\\', '*', '?', '!', '[', ']', '{', '}', '-', ',', '#', '@'

ALPHA = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
DIGITS = '0123456789'
LOWER = 'abcdefghijklmnopqrstuvwxyz'
UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ALPHANUMERIC = DIGITS + ALPHA
HEXDIGITS = '0123456789abcdefABCDEF'
PRINTABLE = tuple(chr(ch) for ch in xrange(0x20, 0x7F))
NOT_PRINTABLE = tuple(chr(ch) for ch in xrange(0x00, 0x20))
VISIBLE = tuple(chr(ch) for ch in xrange(0x21, 0x7F))
NOT_VISIBLE = tuple(chr(ch) for ch in xrange(0x00, 0x21))
ASCII_CHAR = tuple(chr(ch) for ch in xrange(0x00, 0x7F))


BACKSLASH_ORD = ord('\\')


MASK_NONE_CHAR = 0
MASK_ALL_CHAR = 2 ** 257 - 1
MASK_PRINT = reduce(lambda a, b: a | b, (1 << ord(ch) for ch in PRINTABLE))
MASK_NOT_PRINT = (2 ** 0x20) - 1
MASK_ALPHNUM = reduce(lambda a, b: a | b, (1 << ord(ch) for ch in ALPHANUMERIC))
MASK_NUM = 1111111111 << 49
MASK_ALPH = reduce(lambda a, b: a | b, (1 << ord(ch) for ch in ALPHA))
MASK_VIS = reduce(lambda a, b: a | b, (1 << ord(ch) for ch in VISIBLE))
MASK_NOT_VIS = reduce(lambda a, b: a | b, (1 << ord(ch) for ch in NOT_VISIBLE))
MASK_ASCII = 2 ** 129 - 1
MASK_EXT = (2 ** 129 - 1) << 128

"""
for name, value in locals().copy().iteritems():
    if name.startswith('MASK'):
        print '%s:\t%s' % (name, bin(value)[2:])
import sys
sys.exit()
"""

class WildSyntaxError(ValueError):
    pass


def minimize_pattern(pattern):
    new_pattern = []
    i = 0
    p_len = len(pattern)
    while i < p_len:
        ch = pattern[i]
        if ch == '?':
            new_pattern.append(MASK_ALL_CHAR)
        elif ch == '.':
            new_pattern.append(MASK_NOT_PRINT)
        elif ch == '$':
            new_pattern.append(MASK_ALPHNUM)
        elif ch == '#':
            new_pattern.append(MASK_NUM)
        elif ch == '@':
            new_pattern.append(MASK_ALPH)
        elif ch == '-':
            new_pattern.append(MASK_VIS)
        elif ch == '_':
            new_pattern.append(MASK_NOT_VIS)
        elif ch == '%':
            new_pattern.append(MASK_ASCII)
        elif ch == '+':
            new_pattern.append(MASK_EXT)
        elif ch == '\\':
            i += 1
            if i >= p_len:
                raise WildSyntaxError()
            ch = pattern[i]
            if ch in SPECIAL_CHARS:
                new_pattern.append(ord(ch))
            elif ch == 'x':
                i += 2
                if i >= p_len:
                    raise WildSyntaxError()
                hx = pattern[i-1:i+1]
                if hx[0] in HEXDIGITS and hx[1] in HEXDIGITS:
                    new_pattern.append(chr(int(hx, 16)))
                else:
                    raise WildSyntaxError()
            elif ch == '\\':
                new_pattern.append(BACKSLASH_ORD)
            elif ch == '[':
                raise NotImplementedError
            else:
                raise WildSyntaxError()
        else:
            new_pattern.append(ch)
        i += 1
    return new_pattern


def byte_search(text, pattern, offset=0):
    pattern = minimize_pattern(pattern)
    p = 0
    p_len = len(pattern)
    t = int(offset)
    t_len = len(text)
    while t < t_len and p <= t_len and p < p_len:
        tc = text[t]
        pc = pattern[p]
        if isinstance(pc, str):
            if pc == tc:
                p += 1
            else:
                p = 0
        elif isinstance(pc, (int, long)):
            if pc & (1 << (ord(tc) + 1)):
                p += 1
            else:
                p = 0
        else:
            raise Exception("unknown token: %r" % pc)
        t += 1
    return t - p_len if p >= p_len else -1



class SearchTree(object):

    def __init__(self, token=None, eop=None, parent=None, name=None):
        self.parent = parent
        self.token = token
        self.eop = bool(eop)
        self.children = {}
        self.name = name

    def add(self, token, eop=None):
        node = SearchTree(token, eop, self)
        self.children[token] = node
        return node

    def __getitem__(self, token):
        return self.children[token]

    def tokens(self):
        return self.children.keys()

    def items(self):
        return self.children.items()

    def ancestors(self):
        node = self
        while node:
            yield node
            node = node.parent


def byte_msearch(text, patterns, offset=0):
    if isinstance(patterns, dict):
        patterns = patterns.iteritems()
    else:
        patterns = ((p, None) for p in patterns)
    root = SearchTree()
    for pattern, name in patterns:
        tree = root
        for tk in minimize_pattern(pattern):
            if tk in tree.children:
                tree = tree.children[tk]
            else:
                tree = tree.add(tk)
        tree.eop = 1
        tree.name = name
    t = int(offset)
    if t < 0:
        raise ValueError("negative offset: %d" % t)
    t_len = len(text)
    root.eop = 0
    actual_trees = set([root])
    while t < t_len and actual_trees:
        tc = text[t]
        next_trees = set()
        while actual_trees:
            tree = actual_trees.pop()
            if tree.eop:
                yield t, [node.token for node in reversed(tuple(node.ancestors())[:-1])], tree.name
                tree.eop = 0
            for pc, node in tree.items():
                if isinstance(pc, str):
                    if pc == tc:
                        next_trees.add(node)
                    else:
                        next_trees.add(root)
                elif isinstance(pc, (int, long)):
                    if pc & (1 << (ord(tc) + 1)):
                        next_trees.add(node)
                    else:
                        next_trees.add(root)
                else:
                    raise Exception("unknown token: %r" % pc)
        actual_trees = next_trees
        t += 1
