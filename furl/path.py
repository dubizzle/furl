import abc
import urllib
import warnings

from .helpers import join_path_segments
from .helpers import remove_path_segments
from .helpers import is_valid_encoded_path_segment
from .helpers import fix_encoding
from .stringlike import StringLikeObject


class Path(StringLikeObject):
    """
    Represents a URL path comprised of zero or more path segments.

      http://tools.ietf.org/html/rfc3986#section-3.3

    Path parameters aren't supported.

    Attributes:
      _force_absolute: Function whos boolean return value specifies whether
        self.isabsolute should be forced to True or not. If _force_absolute(self)
        returns True, isabsolute is read only and raises an AttributeError if
        assigned to. If _force_absolute(self) returns False, isabsolute is mutable
        and can be set to True or False. URL paths use _force_absolute and return
        True if the netloc is non-empty (not equal to ''). Fragment paths are
        never read-only and their _force_absolute(self) always returns False.
      segments: List of zero or more path segments comprising this path. If the
        path string has a trailing '/', the last segment will be '' and self.isdir
        will be True and self.isfile will be False. An empty segment list
        represents an empty path, not '/' (though they have the same meaning).
      isabsolute: Boolean whether or not this is an absolute path or not. An
        absolute path starts with a '/'. self.isabsolute is False if the path is
        empty (self.segments == [] and str(path) == '').
      strict: Boolean whether or not UserWarnings should be raised if improperly
        encoded path strings are provided to methods that take such strings, like
        load(), add(), set(), remove(), etc.
    """
    SAFE_SEGMENT_CHARS = ":@-._~!$&'()*+,;="

    def __init__(self, path='', force_absolute=lambda _: False, strict=False):
        self.segments = []

        self.strict = strict
        self._isabsolute = False
        self._force_absolute = force_absolute

        self.load(path)

    def __nonzero__(self):
        # Necessary to override default string-like object behaviour
        return len(self.segments) > 0

    def __str__(self):
        segments = list(self.segments)
        if self.isabsolute:
            if not segments:
                segments = ['', '']
            else:
                segments.insert(0, '')

        return self._path_from_segments(segments, quoted=True)

    def load(self, path):
        """
        Load <path>, replacing any existing path. <path> can either be a list of
        segments or a path string to adopt.

        Returns: <self>.
        """
        if not path:
            segments = []
        elif hasattr(path, 'split') and callable(path.split): # String interface.
            segments = self._segments_from_path(path)
        else: # List interface.
            segments = fix_encoding(path)

        if self._force_absolute(self):
            self._isabsolute = True if segments else False
        else:
            self._isabsolute = (segments and segments[0] == '')

        if self.isabsolute and len(segments) > 1 and segments[0] == '':
            segments.pop(0)
        self.segments = [urllib.unquote(segment) for segment in segments]

        return self

    def add(self, path):
        """
        Add <path> to the existing path. <path> can either be a list of segments or
        a path string to append to the existing path.

        Returns: <self>.
        """
        newsegments = path # List interface.
        if hasattr(path, 'split') and callable(path.split): # String interface.
            newsegments = self._segments_from_path(path)

        # Preserve the opening '/' if one exists already (self.segments == ['']).
        if self.segments == [''] and newsegments and newsegments[0] != '':
            newsegments.insert(0, '')

        self.load(join_path_segments(self.segments, newsegments))
        return self

    def set(self, path):
        self.load(path)
        return self

    def remove(self, path):
        if path is True:
            self.load('')
        else:
            segments = path # List interface.
            if isinstance(path, basestring): # String interface.
                segments = self._segments_from_path(path)
            base = ([''] if self.isabsolute else []) + self.segments
            self.load(remove_path_segments(base, segments))
        return self

    @property
    def isabsolute(self):
        if self._force_absolute(self):
            return True
        return self._isabsolute

    @isabsolute.setter
    def isabsolute(self, isabsolute):
        """
        Raises: AttributeError if _force_absolute(self) returns True.
        """
        if self._force_absolute(self):
            s = ('Path.isabsolute is True and read-only for URLs with a netloc (a '
                 'username, password, host, and/or port). A URL path must start with '
                 "a '/' to separate itself from a netloc.")
            raise AttributeError(s)
        self._isabsolute = isabsolute

    @property
    def isdir(self):
        """
        Returns: True if the path ends on a directory, False otherwise. If True, the
        last segment is '', representing the trailing '/' of the path.
        """
        return self.segments == [] or (self.segments and self.segments[-1] == '')

    @property
    def isfile(self):
        """
        Returns: True if the path ends on a file, False otherwise. If True, the last
        segment is not '', representing some file as the last segment of the path.
        """
        return not self.isdir

    def _segments_from_path(self, path):
        """
        Returns: The list of path segments from the path string <path>.

        Raises: UserWarning if <path> is an improperly encoded path string and self.strict
        is True.
        """
        # Raise a warning if self.strict is True and the user provided an improperly
        # encoded path string.
        segments = [fix_encoding(item) for item in path.split('/')]
        if self.strict:
            for segment in segments:
                if not is_valid_encoded_path_segment(segment):
                    warnstr = (("Improperly encoded path string received: '%s'. "
                                "Proceeding, but did you mean '%s'?") %
                               (path, self._path_from_segments(segments, quoted=True)))
                    warnings.warn(warnstr, UserWarning)
                    break
        return map(urllib.unquote, segments)

    def _path_from_segments(self, segments, quoted=True):
        """
        Combine the provided path segments <segments> into a path string. If
        <quoted> is True, each path segment will be quoted. If <quoted> is False,
        each path segment will be unquoted.

        Returns: A path string, with either quoted or unquoted path segments.
        """
        segments_str = ''.join(segments)
        if quoted and '%' not in segments_str:
            segments = map(lambda s: urllib.quote(s, self.SAFE_SEGMENT_CHARS),
                           segments)
        elif not quoted and '%' in segments_str:
            segments = map(urllib.unquote, segments)
        return '/'.join(segments)


class PathCompositionInterface(object):
    """
    Abstract class interface for a parent class that contains a Path.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        """
        Params:
          force_absolute: See Path._force_absolute.

        Assignments to <self> in __init__() must be added to __setattr__() below.
        """
        self._path = Path(force_absolute=self._force_absolute, strict=strict)

    @property
    def path(self):
        return self._path

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False otherwise.
        """
        if attr == '_path':
            self.__dict__[attr] = value
            return True
        elif attr == 'path':
            self._path.load(value)
            return True
        return False

    @abc.abstractmethod
    def _force_absolute(self, path):
        """
        Subclass me.
        """
        pass


class URLPathCompositionInterface(PathCompositionInterface):
    """
    Abstract class interface for a parent class that contains a URL Path.

    A URL path's isabsolute attribute is absolute and read-only if a netloc is
    defined. A path cannot start without '/' if there's a netloc. For example, the
    URL 'http://google.coma/path' makes no sense. It should be
    'http://google.com/a/path'.

    A URL path's isabsolute attribute is mutable if there's no netloc. The scheme
    doesn't matter. For example, the isabsolute attribute of the URL path in
    'mailto:user@domain.com', with scheme 'mailto' and path 'user@domain.com', is
    mutable because there is no netloc. See

      http://en.wikipedia.org/wiki/URI_scheme#Examples
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        PathCompositionInterface.__init__(self, strict=strict)

    def _force_absolute(self, path):
        return bool(path) and self.netloc
