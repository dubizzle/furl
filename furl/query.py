import abc
import urllib
import urlparse
import warnings

from .helpers import is_valid_encoded_query_key
from .helpers import is_valid_encoded_query_value
from .helpers import fix_encoding
from .multidict import OneDimensionalOrderedMultidict
from .stringlike import StringLikeObject


class Query(StringLikeObject):
    """
    Represents a URL query comprised of zero or more unique parameters and their
    respective values.

      http://tools.ietf.org/html/rfc3986#section-3.4


    All interaction with Query.params is done with unquoted strings. So

      f.query.params['a'] = 'a%5E'

    means the intended value for 'a' is 'a%5E', not 'a^'.


    Query.params is implemented as an OneDimensionalOrderedMultidict object - a one dimensional ordered
    multivalue dictionary. This provides support for repeated URL parameters, like
    'a=1&a=2'. OneDimensionalOrderedMultidict is a subclass of omdict, an ordered multivalue
    dictionary. Documentation for omdict can be found here

      https://github.com/gruns/orderedmultidict

    The one dimensional aspect of OneDimensionalOrderedMultidict means that a list of values is
    interpreted as multiple values, not a single value which is itself a list of
    values. This is a reasonable distinction to make because URL query parameters
    are one dimensional - query parameter values cannot themselves be composed of
    sub-values.

    So what does this mean? This means we can safely interpret

      f = Furl('http://www.google.com')
      f.query.params['arg'] = ['one', 'two', 'three']

    as three different values for 'arg': 'one', 'two', and 'three', instead of a
    single value which is itself some serialization of the python list ['one',
    'two', 'three']. Thus, the result of the above will be

      f.query.allitems() == [('arg','one'), ('arg','two'), ('arg','three')]

    and not

      f.query.allitems() == [('arg', ['one', 'two', 'three'])]

    The latter doesn't make sense because query parameter values cannot be
    composed of sub-values. So finally

      str(f.query) == 'arg=one&arg=two&arg=three'

    Attributes:
      params: Ordered multivalue dictionary of query parameter key:value
        pairs. Parameters in self.params are maintained URL decoded - 'a b' not
        'a+b'.
      strict: Boolean whether or not UserWarnings should be raised if improperly
        encoded query strings are provided to methods that take such strings, like
        load(), add(), set(), remove(), etc.
    """
    SAFE_KEY_CHARS = "/?:@-._~!$'()*,"
    SAFE_VALUE_CHARS = "/?:@-._~!$'()*,="

    def __init__(self, query='', strict=False):
        self.strict = strict
        self._params = OneDimensionalOrderedMultidict()

        self.load(query)

    def load(self, query):
        self.params.load(self._items(query))
        return self

    def add(self, args):
        for param, value in self._items(args):
            self.params.add(param, value)
        return self

    def set(self, mapping):
        """
        Adopt all mappings in <mapping>, replacing any existing mappings with the same
        key. If a key has multiple values in <mapping>, they are all adopted.

        Examples:
          Query({1:1}).set([(1,None),(2,2)]).params.allitems() == [(1,None),(2,2)]
          Query({1:None,2:None}).set([(1,1),(2,2),(1,11)]).params.allitems()
            == [(1,1),(2,2),(1,11)]
          Query({1:None}).set([(1,[1,11,111])]).params.allitems()
            == [(1,1),(1,11),(1,111)]

        Returns: <self>.
        """
        self.params.updateall(mapping)
        return self

    def remove(self, query):
        if query is True:
            self.load('')
        else:
            keys = [query]
            if hasattr(query, '__iter__') and callable(query.__iter__):
                keys = query
            for key in keys:
                self.params.pop(key, None)
        return self

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, params):
        items = self._items(params)

        self._params.clear()
        for key, value in items:
            self._params.add(key, value)

    def encode(self, delimeter='&'):
        """
        Examples:
          Query('a=a&b=#').encode() == 'a=a&b=%23'
          Query('a=a&b=#').encode(';') == 'a=a;b=%23'

        Returns: A URL encoded query string using <delimeter> as the delimeter
        separating key:value pairs. The most common and default delimeter is '&',
        but ';' can also be specified. ';' is W3C recommended.
        """
        pairs = []
        for key, value in self.params.iterallitems():
            key = fix_encoding(key)
            value = fix_encoding(value)
            pair = '='.join((urllib.quote_plus(str(key), self.SAFE_KEY_CHARS),
                             urllib.quote_plus(str(value), self.SAFE_VALUE_CHARS)))
            pairs.append(pair)
        return delimeter.join(pairs)

    def __nonzero__(self):
        return len(self.params) > 0

    def __str__(self):
        return self.encode()

    def _items(self, items):
        """
        Extract and return the key:value items from various containers. Some
        containers that could hold key:value items are

          - List of (key,value) tuples.
          - Dictionaries of key:value items.
          - Multivalue dictionary of key:value items, with potentially repeated
            keys.
          - Query string with encoded params and values.

        Keys and values are passed through unmodified unless they were passed in
        within an encoded query string, like 'a=a%20a&b=b'. Keys and values passed
        in within an encoded query string are unquoted by urlparse.parse_qsl(),
        which uses urllib.unquote_plus() internally.

        Returns: List of items as (key, value) tuples. Keys and values are passed
        through unmodified unless they were passed in as part of an encoded query
        string, in which case the final keys and values that are returned will be
        unquoted.

        Raises: UserWarning if <path> is an improperly encoded path string and self.strict
        is True.
        """
        if not items:
            items = []
        # Multivalue Dictionary-like interface. i.e. {'a':1, 'a':2, 'b':2}
        elif hasattr(items, 'allitems') and callable(items.allitems):
            items = list(items.allitems())
        elif hasattr(items, 'iterallitems') and callable(items.iterallitems):
            items = list(items.iterallitems())
        # Dictionary-like interface. i.e. {'a':1, 'b':2, 'c':3}
        elif hasattr(items, 'iteritems') and callable(items.iteritems):
            items = list(items.iteritems())
        elif hasattr(items, 'items') and callable(items.items):
            items = list(items.items())
        # Encoded query string. i.e. 'a=1&b=2&c=3'
        elif isinstance(items, basestring):
            # Raise a warning if self.strict is True and the user provided an
            # improperly encoded query string.
            if self.strict:
                pairstrs = [s2 for s1 in items.split('&') for s2 in s1.split(';')]
                pairs = map(lambda item: item.split('=', 1), pairstrs)
                pairs = map(lambda p: (p[0], '') if len(p) == 1 else (p[0], p[1]), pairs)
                for key, value in pairs:
                    if (not is_valid_encoded_query_key(key) or
                            not is_valid_encoded_query_value(value)):
                        warnstr = (("Improperly encoded query string received: '%s'. "
                                    "Proceeding, but did you mean '%s'?") %
                                   (items, urllib.urlencode(pairs)))
                        warnings.warn(warnstr, UserWarning)
                        break

            # Keys and values will be unquoted from the query string.
            items = urlparse.parse_qsl(items, keep_blank_values=True)
        # Default to list of key:value items interface. i.e. [('a','1'), ('b','2')]
        else:
            items = list(items)

        # Ensure utf-8 encoding
        items = [(fix_encoding(key), fix_encoding(value)) for key, value in items]

        return items


class QueryCompositionInterface(object):
    """
    Abstract class interface for a parent class that contains a Query.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        self._query = Query(strict=strict)

    @property
    def query(self):
        return self._query

    @property
    def args(self):
        """
        Shortcut method to access the query parameters, self._query.params.
        """
        return self._query.params

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False otherwise.
        """
        if attr == 'args' or attr == 'query':
            self._query.load(value)
            return True
        return False
