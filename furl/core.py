#
# furl - URL manipulation made simple.
#
# Arthur Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)
import urlparse
import warnings

from .fragment import FragmentCompositionInterface
from .helpers import urlsplit, urljoin, is_valid_port
from .path import PathCompositionInterface, URLPathCompositionInterface
from .query import QueryCompositionInterface
from .stringlike import StringLikeObject


_absent = object()


# TODO(grun): Subclass Path, PathCompositionInterface, Query, and
# QueryCompositionInterface into two subclasses each - one for the URL and one
# for the Fragment.
#
# Subclasses will clean up the code because the valid encodings are different
# between a URL Path and a Fragment Path and a URL Query and a Fragment Query.
#
# For example, '?' and '#' don't need to be encoded in Fragment Path segments
# but must be encoded in URL Path segments.
#
# Similarly, '#' doesn't need to be encoded in Fragment Query keys and values,
# but must be encoded in URL Query keys and values.
#
class Furl(StringLikeObject, URLPathCompositionInterface, QueryCompositionInterface,
           FragmentCompositionInterface):
    """
    Object for simple parsing and manipulation of a URL and its components.

      scheme://username:password@host:port/path?query#fragment

    Attributes:
      DEFAULT_PORTS: Map of various URL schemes to their default ports. Scheme
        strings are lowercase.
      strict: Boolean whether or not UserWarnings should be raised if improperly
        encoded path, query, or fragment strings are provided to methods that take
        such strings, like load(), add(), set(), remove(), etc.
      username: Username string for authentication. Initially None.
      password: Password string for authentication with <username>. Initially
        None.
      scheme: URL scheme ('http', 'https', etc). All lowercase. Initially None.
      host: URL host (domain, IPv4 address, or IPv6 address), not including
        port. All lowercase. Initially None.
      port: Port. Valid port values are 1-65535, or None meaning no port
        specified.
      netloc: Network location. Combined host and port string. Initially None.
      path: Path object from URLPathCompositionInterface.
      query: Query object from QueryCompositionInterface.
      fragment: Fragment object from FragmentCompositionInterface.
    """
    DEFAULT_PORTS = {
        'ftp': 21,
        'ssh': 22,
        'http': 80,
        'https': 443,
    }

    def __init__(self, url='', strict=False):
        """
        Raises: ValueError on invalid url.
        """
        URLPathCompositionInterface.__init__(self, strict=strict)
        QueryCompositionInterface.__init__(self, strict=strict)
        FragmentCompositionInterface.__init__(self, strict=strict)
        self.strict = strict

        self.load(str(url)) # Raises ValueError on invalid url.

    def load(self, url):
        """
        Parse and load a URL.

        Raises: ValueError on invalid URL (for example malformed IPv6 address or
        invalid port).
        """
        self.username = self.password = self.scheme = self._host = None
        self._port = None

        tokens = urlsplit(url) # Raises ValueError on malformed IPv6 address.

        self.netloc = tokens.netloc # Raises ValueError.
        self.scheme = tokens.scheme.lower() or None
        if not self.port:
            self._port = self.DEFAULT_PORTS.get(self.scheme)
        self.path.load(tokens.path)
        self.query.load(tokens.query)
        self.fragment.load(tokens.fragment)
        return self

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        """
        Raises: ValueError on malformed IPv6 address.
        """
        urlparse.urlsplit('http://%s/' % host) # Raises ValueError.
        self._host = host

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        """
        A port value can 1-65535 or None meaning no port specified. If <port> is
        None and self.scheme is a known scheme in self.DEFAULT_PORTS, the default
        port value from self.DEFAULT_PORTS will be used.

        Raises: ValueError on invalid port.
        """
        if port is None:
            self._port = self.DEFAULT_PORTS.get(self.scheme)
        elif is_valid_port(port):
            self._port = int(str(port))
        else:
            raise ValueError("Invalid port: '%s'" % port)

    @property
    def netloc(self):
        userpass = self.username or ''
        if self.password is not None:
            userpass += ':' + self.password
        if userpass or self.username is not None:
            userpass += '@'

        netloc = self.host or ''
        if self.port and self.port != self.DEFAULT_PORTS.get(self.scheme):
            netloc += ':' + str(self.port)

        netloc = ((userpass or '') + (netloc or ''))
        return netloc if (netloc or self.host == '') else None

    @netloc.setter
    def netloc(self, netloc):
        """
        Params:
          netloc: Network location string, like 'google.com' or 'google.com:99'.
        Raises: ValueError on invalid port or malformed IPv6 address.
        """
        # Raises ValueError on malformed IPv6 addresses.
        urlparse.urlsplit('http://%s/' % netloc)

        username = password = host = port = None

        if '@' in netloc:
            userpass, netloc = netloc.split('@', 1)
            if ':' in userpass:
                username, password = userpass.split(':', 1)
            else:
                username = userpass

        if ':' in netloc:
            # IPv6 address literal.
            if ']' in netloc:
                colonpos, bracketpos = netloc.rfind(':'), netloc.rfind(']')
                if colonpos > bracketpos and colonpos != bracketpos + 1:
                    raise ValueError("Invalid netloc: '%s'" % netloc)
                elif colonpos > bracketpos and colonpos == bracketpos + 1:
                    host, port = netloc.rsplit(':', 1)
                else:
                    host = netloc.lower()
            else:
                host, port = netloc.rsplit(':', 1)
                host = host.lower()
        else:
            host = netloc.lower()

        # Avoid side effects by assigning self.port before self.host so that if an
        # exception is raised when assigning self.port, self.host isn't updated.
        self.port = port # Raises ValueError on invalid port.
        self.host = host or None
        self.username = username or None
        self.password = password or None

    @property
    def url(self):
        return str(self)

    @url.setter
    def url(self, url):
        self.load(url)

    def add(self, args=_absent, path=_absent, fragment_path=_absent,
            fragment_args=_absent, query_params=_absent):
        """
        Add components to a URL and return this Furl instance, <self>.

        If both <args> and <query_params> are provided, a UserWarning is raised
        because <args> is provided as a shortcut for <query_params>, not to be used
        simultaneously with <query_params>. Nonetheless, providing both <args> and
        <query_params> behaves as expected, with query keys and values from both
        <args> and <query_params> added to the query - <args> first, then
        <query_params>.

        Parameters:
          args: Shortcut for <query_params>.
          path: A list of path segments to add to the existing path segments, or a
            path string to join with the existing path string.
          query_params: A dictionary of query keys and values or list of key:value
            items to add to the query.
          fragment_path: A list of path segments to add to the existing fragment
            path segments, or a path string to join with the existing fragment path
            string.
          fragment_args: A dictionary of query keys and values or list of key:value
            items to add to the fragment's query.
        Returns: <self>.
        """
        if args is not _absent and query_params is not _absent:
            warnstr = ('Both <args> and <query_params> provided to Furl.add(). <args>'
                       ' is a shortcut for <query_params>, not to be used with '
                       '<query_params>. See Furl.add() documentation for more '
                       'details.')
            warnings.warn(warnstr, UserWarning)

        if path is not _absent:
            self.path.add(path)
        if args is not _absent:
            self.query.add(args)
        if query_params is not _absent:
            self.query.add(query_params)
        if fragment_path is not _absent or fragment_args is not _absent:
            self.fragment.add(path=fragment_path, args=fragment_args)
        return self

    def set(self, args=_absent, path=_absent, fragment=_absent, scheme=_absent,
            netloc=_absent, fragment_path=_absent, fragment_args=_absent,
            fragment_separator=_absent, host=_absent, port=_absent, query=_absent,
            query_params=_absent, username=_absent, password=_absent):
        """
        Set components of a url and return this Furl instance, <self>.

        If any overlapping, and hence possibly conflicting, parameters are provided,
        appropriate UserWarning's will be raised. The groups of parameters that
        could potentially overlap are

          <netloc> and (<host> or <port>)
          <fragment> and (<fragment_path> and/or <fragment_args>)
          any two or all of <query>, <args>, and/or <query_params>

        In all of the above groups, the latter parameter(s) take precedence over the
        earlier parameter(s). So, for example

          Furl('http://google.com/').set(netloc='yahoo.com:99', host='bing.com',
                                         port=40)

        will result in a UserWarning being raised and the url becoming

          'http://bing.com:40/'

        not

          'http://yahoo.com:99/

        Parameters:
          args: Shortcut for <query_params>.
          path: A list of path segments or a path string to adopt.
          fragment: Fragment string to adopt.
          scheme: Scheme string to adopt.
          netloc: Network location string to adopt.
          query: Query string to adopt.
          query_params: A dictionary of query keys and values or list of key:value
            items to adopt.
          fragment_path: A list of path segments to adopt for the fragment's path or
            a path string to adopt as the fragment's path.
          fragment_args: A dictionary of query keys and values or list of key:value
            items for the fragment's query to adopt.
          fragment_separator: Boolean whether or not there should be a '?' separator
            between the fragment path and fragment query.
          host: Host string to adopt.
          port: Port number to adopt.
          username: Username string to adopt.
          password: Password string to adopt.
        Raises:
          ValueError on invalid port.
          UserWarning if <netloc> and (<host> and/or <port>) are provided.
          UserWarning if <query>, <args>, and/or <query_params> are provided.
          UserWarning if <fragment> and (<fragment_path>, <fragment_args>, and/or
            <fragment_separator>) are provided.
        Returns: <self>.
        """
        if netloc is not _absent and (host is not _absent or port is not _absent):
            warnstr = ('Possible parameter overlap: <netloc> and <host> and/or '
                       '<port> provided. See Furl.set() documentation for more '
                       'details.')
            warnings.warn(warnstr, UserWarning)
        if ((args is not _absent and query is not _absent) or
                (query is not _absent and query_params is not _absent) or
                (args is not _absent and query_params is not _absent)):
            warnstr = ('Possible parameter overlap: <query>, <args>, and/or'
                       '<query_params> provided. See Furl.set() documentation for more'
                       'details.')
            warnings.warn(warnstr, UserWarning)
        if (fragment is not _absent and
                (fragment_path is not _absent or fragment_args is not _absent or
                     (fragment_separator is not _absent))):
            warnstr = ('Possible parameter overlap: <fragment> and (<fragment_path>'
                       'and/or <fragment_args>) or <fragment> and '
                       '<fragment_separator> provided. See Furl.set() documentation'
                       'for more details.')
            warnings.warn(warnstr, UserWarning)

        # Avoid side effects if exceptions are raised.
        oldnetloc, oldport = self.netloc, self.port
        try:
            if netloc is not _absent:
                self.netloc = netloc # Raises ValueError on invalid port or malformed IP.
            if port is not _absent:
                self.port = port # Raises ValueError on invalid port.
        except ValueError:
            self.netloc, self.port = oldnetloc, oldport
            raise

        if username is not _absent:
            self.username = username
        if password is not _absent:
            self.password = password
        if scheme is not _absent:
            self.scheme = scheme
        if host is not _absent:
            self.host = host

        if path is not _absent:
            self.path.load(path)
        if query is not _absent:
            self.query.load(query)
        if args is not _absent:
            self.query.load(args)
        if query_params is not _absent:
            self.query.load(query_params)
        if fragment is not _absent:
            self.fragment.load(fragment)
        if fragment_path is not _absent:
            self.fragment.path.load(fragment_path)
        if fragment_args is not _absent:
            self.fragment.query.load(fragment_args)
        if fragment_separator is not _absent:
            self.fragment.separator = fragment_separator
        return self

    def remove(self, args=_absent, path=_absent, fragment=_absent, query=_absent,
               query_params=_absent, port=False, fragment_path=_absent,
               fragment_args=_absent, username=False, password=False):
        """
        Remove components of this Furl's URL and return this Furl instance, <self>.

        Parameters:
          args: Shortcut for query_params.
          path: A list of path segments to remove from the end of the existing path
            segments list, or a path string to remove from the end of the existing
            path string, or True to remove the path entirely.
          query: If True, remove the query portion of the URL entirely.
          query_params: A list of query keys to remove from the query, if they
            exist.
          port: If True, remove the port from the network location string, if it
            exists.
          fragment: If True, remove the fragment portion of the URL entirely.
          fragment_path: A list of path segments to remove from the end of the
            fragment's path segments or a path string to remove from the end of the
            fragment's path string.
          fragment_args: A list of query keys to remove from the fragment's query,
            if they exist.
          username: If True, remove the username, if it exists.
          password: If True, remove the password, if it exists.
        Returns: <self>.
        """
        if port is True:
            self.port = None
        if username is True:
            self.username = None
        if password is True:
            self.password = None
        if path is not _absent:
            self.path.remove(path)
        if args is not _absent:
            self.query.remove(args)
        if query is not _absent:
            self.query.remove(query)
        if fragment is not _absent:
            self.fragment.remove(fragment)
        if query_params is not _absent:
            self.query.remove(query_params)
        if fragment_path is not _absent:
            self.fragment.path.remove(fragment_path)
        if fragment_args is not _absent:
            self.fragment.query.remove(fragment_args)
        return self

    def join(self, url):
        self.load(urljoin(self.url, str(url)))
        return self

    def copy(self):
        return self.__class__(self)

    def __setattr__(self, attr, value):
        if (not PathCompositionInterface.__setattr__(self, attr, value) and
                not QueryCompositionInterface.__setattr__(self, attr, value) and
                not FragmentCompositionInterface.__setattr__(self, attr, value)):
            object.__setattr__(self, attr, value)

    def __str__(self):
        path, query, fragment = str(self.path), str(self.query), str(self.fragment)
        url = urlparse.urlunsplit((self.scheme, self.netloc, path, query, fragment))

        # Special cases.
        if not self.scheme and url.startswith('//') and not path.startswith('//'):
            url = url[2:]
        elif self.scheme is not None and url == '':
            url += '://'
        elif self.scheme is not None and url == '%s:' % self.scheme:
            url += '//'

        return url
