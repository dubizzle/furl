import re
import urlparse


# TODO(grun): These functions need to be expanded to reflect the fact that the
# valid encoding for a URL Path segment is different from a Fragment Path
# segment, and valid URL Query key and value encoding is different than valid
# Fragment Query key and value encoding.
#
# For example, '?' and '#' don't need to be encoded in Fragment Path segments
# but they must be encoded in URL Path segments.
#
# Similarly, '#' doesn't need to be encoded in Fragment Query keys and values,
# but must be encoded in URL Query keys and values.
#
# Perhaps merge them with URLPath, FragmentPath, URLQuery, and FragmentQuery
# when those new classes are created (see the TODO currently at the top of the
# source, 02/03/2012).
#

# RFC 3986
#   unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
#
#   pct-encoded = "%" HEXDIG HEXDIG
#
#   sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
#                 / "*" / "+" / "," / ";" / "="
#
#   pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
#
#   ====
#   Path
#   ====
#   segment       = *pchar
#
#   =====
#   Query
#   =====
#   query       = *( pchar / "/" / "?" )
#
VALID_ENCODED_PATH_SEGMENT_REGEX = re.compile(
    r"^([\w\-\.~:@!\$&'\(\)\*\+,;=]|(%[\da-fA-F][\da-fA-F]))*$")
VALID_ENCODED_QUERY_KEY_REGEX = re.compile(
    r"^([\w\-\.~:@!\$&'\(\)\*\+,;/\?]|(%[\da-fA-F][\da-fA-F]))*$")
VALID_ENCODED_QUERY_VALUE_REGEX = re.compile(
    r"^([\w\-\.~:@!\$&'\(\)\*\+,;/\?=]|(%[\da-fA-F][\da-fA-F]))*$")


def _get_scheme(url):
    i = url.find(':')
    if i > 0:
        return url[:i] or ''
    return ''


def _set_scheme(url, newscheme):
    scheme = _get_scheme(url)
    if scheme:
        return newscheme + url[len(scheme):]
    return url


#urlparse.urlsplit() and urlparse.urljoin() don't separate the query string from
#the path for schemes not in the list urlparse.uses_query, but Furl should
#support proper parsing of query strings and paths for all schemes users may use.
#
#As a workaround, use 'http' (a scheme in urlparse.uses_query) for the purposes
#of urlparse.urlsplit() and urlparse.urljoin(), but then revert back to the
#original scheme provided once urlsplit() or urljoin() has completed.
#
#_get_scheme() and _change_scheme() are helper methods for getting and setting
#the scheme of URL strings. Used to change the scheme to 'http' and back again.
def urlsplit(url):
    """
    Parameters:
      url: URL string to split.

    Returns: urlparse.SplitResult tuple subclass, just like urlparse.urlsplit()
    returns, with fields (scheme, netloc, path, query, fragment, username,
    password, hostname, port). See the url below for more details on urlsplit().

      http://docs.python.org/library/urlparse.html#urlparse.urlsplit
    """
    # If a scheme wasn't provided, we shouldn't add one by setting the scheme to
    # 'http'. We can use urlparse.urlsplit(url) as-is.
    if '://' not in url:
        return urlparse.urlsplit(url)

    def _change_urltoks_scheme(tup, scheme):
        l = list(tup)
        l[0] = scheme
        return tuple(l)

    original_scheme = _get_scheme(url)
    toks = urlparse.urlsplit(_set_scheme(url, 'http'))
    return urlparse.SplitResult(*_change_urltoks_scheme(toks, original_scheme))


def urljoin(base, url):
    """
    Parameters:
      base: Base URL to join with <url>.
      url: Relative or absolute URL to join with <base>.

    Returns: The resultant URL from joining <base> and <url>.
    """
    base_scheme, url_scheme = _get_scheme(base), _get_scheme(url)
    httpbase = _set_scheme(base, 'http')
    joined = urlparse.urljoin(httpbase, url)
    if not url_scheme:
        joined = _set_scheme(joined, base_scheme)
    return joined


def join_path_segments(*args):
    """
    Join multiple lists of path segments together, intelligently handling path
    segments borders to preserve intended slashes of the final constructed path.

    This function is not encoding aware - it does not test for or change the
    encoding of path segments it is passed.

    Examples:
      join_path_segments(['a'], ['b']) == ['a','b']
      join_path_segments(['a',''], ['b']) == ['a','b']
      join_path_segments(['a'], ['','b']) == ['a','b']
      join_path_segments(['a',''], ['','b']) == ['a','','b']
      join_path_segments(['a','b'], ['c','d']) == ['a','b','c','d']

    Returns: A list containing the joined path segments.
    """
    finals = []
    for segments in args:
        if not segments or segments == ['']:
            continue
        elif not finals:
            finals.extend(segments)
        else:
            # Example #1: ['a',''] + ['b'] == ['a','b']
            # Example #2: ['a',''] + ['','b'] == ['a','','b']
            if finals[-1] == '' and (segments[0] != '' or len(segments) > 1):
                finals.pop(-1)
            # Example: ['a'] + ['','b'] == ['a','b']
            elif finals[-1] != '' and segments[0] == '' and len(segments) > 1:
                segments = segments[1:]
            finals.extend(segments)
    return finals


def remove_path_segments(segments, remove):
    """
    Removes the path segments of <remove> from the end of the path segments
    <segments>.

    Examples:
      # '/a/b/c' - 'b/c' == '/a/'
      remove_path_segments(['','a','b','c'], ['b','c']) == ['','a','']
      # '/a/b/c' - '/b/c' == '/a'
      remove_path_segments(['','a','b','c'], ['','b','c']) == ['','a']

    Returns: The list of all remaining path segments after the segments in
    <remove> have been removed from the end of <segments>. If no segments from
    <remove> were removed from <segments>, <segments> is returned unmodified.
    """
    # [''] means a '/', which is properly represented by ['', ''].
    if segments == ['']:
        segments.append('')
    if remove == ['']:
        remove.append('')

    ret = None
    if remove == segments:
        ret = []
    elif len(remove) > len(segments):
        ret = segments
    else:
        toremove = list(remove)

        if len(remove) > 1 and remove[0] == '':
            toremove.pop(0)

        if toremove and toremove == segments[-1 * len(toremove):]:
            ret = segments[:len(segments) - len(toremove)]
            if remove[0] != '' and ret:
                ret.append('')
        else:
            ret = segments

    return ret


def is_valid_port(port):
    port = str(port)
    if not port.isdigit() or int(port) == 0 or int(port) > 65535:
        return False
    return True


def is_valid_encoded_path_segment(segment):
    return bool(VALID_ENCODED_PATH_SEGMENT_REGEX.match(segment))


def is_valid_encoded_query_key(key):
    return bool(VALID_ENCODED_QUERY_KEY_REGEX.match(key))


def is_valid_encoded_query_value(value):
    return bool(VALID_ENCODED_QUERY_VALUE_REGEX.match(value))


def fix_encoding(item):
    if isinstance(item, unicode):
        item = item.encode('utf-8')

    return item
