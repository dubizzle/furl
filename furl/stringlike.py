import abc


class StringLikeObject(object):
    """Represents a string-like object"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __str__(self):
        raise NotImplementedError()

    def __len__(self):
        return len(str(self))

    def __nonzero__(self):
        return bool(str(self))

    def __unicode__(self):
        return unicode(str(self))

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        try:
            is_equal = str(self) == str(other)
        except Exception:
            is_equal = False

        return is_equal

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self):
        return iter(str(self))

    def __getattr__(self, item):
        try:
            return getattr(str(self), item)
        except AttributeError:
            raise AttributeError('%s has not attribute %s'
                                 % (self.__class__.__name__, item))

    def __contains__(self, item):
        return item in str(self)

    def __getitem__(self, item):
        return str(self)[item]

    def __add__(self, other):
        return str(self) + other

    def __radd__(self, other):
        return other + str(self)

