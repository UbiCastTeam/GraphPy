import re
from types import MethodType

class DictList(list):
    '''List that can only contain dictionaries.
    
    Provide lookup functionality'''
    
    def __init__(self, iterable=None):
        list.__init__(self)
        self._dict_properties = set()
        if iterable is not None:
            if isinstance(iterable, dict):
                self.append(iterable)
            else:
                self.extend(iterable)
    
    def _add_key(self, key):
        if key not in self._dict_properties:
            self._dict_properties.add(key)
            def get_by_key(self, value):
                return self.get_key(key, value)
            def get_all_by_key(self, value):
                return self.get_all_key(key, value)
            setattr(self, 'get_by_%s' % key, MethodType(get_by_key, self, self.__class__))
            setattr(self, 'get_all_by_%s' % key, MethodType(get_all_by_key, self, self.__class__))
    
    def _after_add_dict(self, dct):
        for key in dct:
            self._add_key(key)
        self._synchronize_properties()
    
    def _after_extend_list(self, dict_list):
        for dct in dict_list:
            for key in dct:
                self._add_key(key)
        self._synchronize_properties()
    
    def _check_item(self, item):
        if not isinstance(item, dict):
            raise TypeError('DictList item type must be %s (%s found)' % (dict, type(item)))
        for key in item:
            self._check_key(key)
    
    def _check_key(self, key):
        match = re.search(r'[^a-z0-9_]', key)
        if match is not None:
            raise ValueError('Key can only contain small letters, digits and underscores, "%s" is invalid' % key)
    
    def _check_list(self, l):
        for item in l:
            self._check_item(item)
    
    def _synchronize_properties(self):
        for dct in self:
            for prop in self._dict_properties:
                if prop not in dct:
                    dct[prop] = None
    
    def get_all_key(self, key, value):
        result = list()
        try:
            for item in self:
                if item[key] == value:
                    result.append(item)
        except KeyError:
            raise KeyError('Items of this list have no key "%s"' % key)
        return result
    
    def get_key(self, key, value):
        try:
            for item in self:
                if item[key] == value:
                    return item
        except KeyError:
            raise KeyError('Items of this list have no key "%s"' % key)
        return None
    
    def __add__(self, dict_list):
        self.extend(dict_list)
    
    def __setitem__(self, index, dct):
        copied_dict = dict(dct)
        self._check_item(copied_dict)
        list.__setitem__(self, index, copied_dict)
        self._after_add_dict(copied_dict)
    
    def __getslice__(self, i, j):
        return DictList(list.__getslice__(self, i, j))
    
    def __setslice__(self, i, j, dict_list):
        copied_dict_list = list()
        for dct in dict_list:
            copied_dict_list.append(dict(dct))
        self._check_list(copied_dict_list)
        list.__setslice__(self, i, j, copied_dict_list)
        self._after_extend_list(copied_dict_list)
    
    def append(self, dct):
        copied_dict = dict(dct)
        self._check_item(copied_dict)
        list.append(self, copied_dict)
        self._after_add_dict(copied_dict)
    
    def copy(self):
        new_dict_list = list()
        for dct in self:
            new_dict_list.append(dict(dct))
        return new_dict_list
    
    def extend(self, dict_list):
        copied_dict_list = list()
        for dct in dict_list:
            copied_dict_list.append(dict(dct))
        self._check_list(copied_dict_list)
        list.extend(self, copied_dict_list)
        self._after_extend_list(copied_dict_list)
    
    def insert(self, index, dct):
        copied_dict = dict(dct)
        self._check_item(copied_dict)
        list.insert(self, index, copied_dict)
        self._after_add_dict(copied_dict)
    
    def sort_by(self, key):
        self.sort(key=lambda d: d[key])

try:
    from collections import OrderedDict
except ImportError:
    # Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
    # Passes Python2.7's test suite and incorporates all the latest updates.

    try:
        from thread import get_ident as _get_ident
    except ImportError:
        from dummy_thread import get_ident as _get_ident

    try:
        from _abcoll import KeysView, ValuesView, ItemsView
    except ImportError:
        pass

