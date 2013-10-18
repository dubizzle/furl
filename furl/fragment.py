import abc
import warnings
from .stringlike import StringLikeObject
from .path import PathCompositionInterface
from .query import QueryCompositionInterface


_absent = object()


class FragmentPathCompositionInterface(PathCompositionInterface):
    """
    Abstract class interface for a parent class that contains a Fragment Path.

    Fragment Paths they be set to absolute (self.isabsolute = True) or not
    absolute (self.isabsolute = False).
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        PathCompositionInterface.__init__(self, strict=strict)

    def _force_absolute(self, path):
        return False


class Fragment(StringLikeObject, FragmentPathCompositionInterface,
               QueryCompositionInterface):
    """
    Represents a URL fragment, comprised internally of a Path and Query optionally
    separated by a '?' character.

      http://tools.ietf.org/html/rfc3986#section-3.5

    Attributes:
      path: Path object from FragmentPathCompositionInterface.
      query: Query object from QueryCompositionInterface.
      separator: Boolean whether or not a '?' separator should be included in the
        string representation of this fragment. When False, a '?' character will
        not separate the fragment path from the fragment query in the fragment
        string. This is useful to build fragments like '#!arg1=val1&arg2=val2',
        where no separating '?' is desired.
    """
    def __init__(self, fragment='', strict=False):
        FragmentPathCompositionInterface.__init__(self, strict=strict)
        QueryCompositionInterface.__init__(self, strict=strict)
        self.strict = strict
        self.separator = True

        self.load(fragment)

    def load(self, fragment):
        self.path.load('')
        self.query.load('')

        toks = fragment.split('?', 1)
        if len(toks) == 0:
            self._path.load('')
            self._query.load('')
        elif len(toks) == 1:
            # Does this fragment look like a path or a query? Default to path.
            if '=' in fragment: # Query example: '#woofs=dogs'.
                self._query.load(fragment)
            else: # Path example: '#supinthisthread'.
                self._path.load(fragment)
        else:
            # Does toks[1] actually look like a query? Like 'a=a' or 'a=' or '=a'?
            if '=' in toks[1]:
                self._path.load(toks[0])
                self._query.load(toks[1])
            # If toks[1] doesn't look like a query, the user probably provided a
            # fragment string like 'a?b?' that was intended to be adopted as-is, not a
            # two part fragment with path 'a' and query 'b?'.
            else:
                self._path.load(fragment)

    def add(self, path=_absent, args=_absent):
        if path is not _absent:
            self.path.add(path)
        if args is not _absent:
            self.query.add(args)
        return self

    def set(self, path=_absent, args=_absent, separator=_absent):
        if path is not _absent:
            self.path.load(path)
        if args is not _absent:
            self.query.load(args)
        if separator is True or separator is False:
            self.separator = separator
        return self

    def remove(self, fragment=_absent, path=_absent, args=_absent):
        if fragment is True:
            self.load('')
        if path is not _absent:
            self.path.remove(path)
        if args is not _absent:
            self.query.remove(args)
        return self

    def __setattr__(self, attr, value):
        if (not PathCompositionInterface.__setattr__(self, attr, value) and
                not QueryCompositionInterface.__setattr__(self, attr, value)):
            object.__setattr__(self, attr, value)

    def __nonzero__(self):
        return bool(self.path) or bool(self.query)

    def __str__(self):
        path, query = str(self._path), str(self._query)

        # If there is no query or self.separator is False, decode all '?' characters
        # in the path from their percent encoded form '%3F' to '?'. This allows for
        # fragment strings containg '?'s, like '#dog?machine?yes'.
        if path and (not query or not self.separator):
            path = path.replace('%3F', '?')

        if query and path:
            return path + ('?' if self.separator else '') + query
        return path + query


class FragmentCompositionInterface(object):
    """
    Abstract class interface for a parent class that contains a Fragment.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        self._fragment = Fragment(strict=strict)

    @property
    def fragment(self):
        return self._fragment

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False otherwise.
        """
        if attr == 'fragment':
            self.fragment.load(value)
            return True
        return False
