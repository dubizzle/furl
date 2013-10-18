# coding=utf-8
"""Test StringLike base and subclasses"""
import unittest

import furl


class StringLikeObjectTestClass(furl.StringLikeObject):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def load(self, value):
        self.value = value


class StringLikeObjectTestCase(unittest.TestCase):
    """StringLikeObject"""
    def _get_test_class(self, value):
        return StringLikeObjectTestClass(value)

    def _assert_raises(self, function):
        try:
            function()
        except:
            pass
        else:
            raise AssertionError()

    def test_enforces_itself_as_abstract_base_class(self):
        self._assert_raises(lambda: furl.StringLikeObject())

        class TestClass(furl.StringLikeObject):
            pass

        self._assert_raises(lambda: TestClass())

        class TestClassTwo(furl.StringLikeObject):
            def __str__(self):
                super(TestClassTwo, self).__str__()

            def load(self, value):
                pass

        self._assert_raises(lambda: str(TestClassTwo()))

    def test_nonzero(self):
        assert not bool(self._get_test_class(''))
        assert bool(self._get_test_class('nonempty'))

    def test_unicode_caster(self):
        assert unicode(self._get_test_class('somevalue')) == u'somevalue'
        assert unicode(self._get_test_class('')) == u''

    def test_representation(self):
        assert repr(self._get_test_class('what')) == "StringLikeObjectTestClass('what')"

    def test_hash(self):
        somedict = {self._get_test_class('abcd'): 1}
        assert self._get_test_class('abcd') in somedict
        assert self._get_test_class('abcde') not in somedict
        assert 'abcd' in somedict
        assert 'abcde' not in somedict

    def test_equality_comparison(self):
        assert self._get_test_class('abcd') == self._get_test_class('abcd')
        assert (self._get_test_class('abcd') == self._get_test_class('abcde')) is False

    def test_negative_equality_comparison(self):
        assert self._get_test_class('abcd') != self._get_test_class('abcde')
        assert (self._get_test_class('abcd') != self._get_test_class('abcd')) is False

    def test_iteration(self):
        assert ''.join(self._get_test_class('abcdefg')) == 'abcdefg'
        assert list(self._get_test_class('abcdefg')) == list('abcdefg')
        assert not bool(list(self._get_test_class('')))

    def test_get_attribute_of_string(self):
        assert self._get_test_class('something').title() == 'Something'
        assert self._get_test_class('SOMETHING').lower() == 'something'
        self._assert_raises(lambda: self._get_test_class('blahblah').some_unknown_func)

    def test_contains(self):
        assert 'something' in self._get_test_class('something')
        assert 'something' in self._get_test_class('something longer')
        assert 'notinhere' not in self._get_test_class('definitely not')

    def test_get_item(self):
        assert 'something'[:5] == self._get_test_class('something')[:5]
        assert 'something'[:-1:-1] == self._get_test_class('something')[:-1:-1]
        assert self._get_test_class('something')[0] == 's'
        self._assert_raises(lambda: self._get_test_class('outofbounds')[9999])

    def test_addition(self):
        assert ('something' + self._get_test_class('else')) == 'somethingelse'
        assert (self._get_test_class('something') + 'else') == 'somethingelse'

    def test_length(self):
        assert len(self._get_test_class('12345')) == 5

    def test_can_be_pickled(self):
        import pickle

        item = self._get_test_class('12345')
        pickled_item = pickle.dumps(item)
        loaded_item = pickle.loads(pickled_item)
        assert item == loaded_item
