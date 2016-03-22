from __future__ import unicode_literals, division, absolute_import

import pytest

from flexget.entry import Entry
from flexget.plugins.list.imdb_list import ImdbEntrySet


@pytest.mark.online
class TestIMDBList(object):
    config = """
      'tasks': {}
    """
    VCR_RECORD_MODE = 'all'

    imdb_config = {'login': 'siysbijz@sharklasers.com',
                   'password': 'flexget16',
                   'list': 'watchlist'}

    def test_imdb_list_add(self):
        imdb_set = ImdbEntrySet(self.imdb_config)
        # Clearing existing list
        imdb_set.clear()

        entry = Entry(title='the matrix', imdb_id='tt0133093')

        assert entry not in imdb_set
        imdb_set.add(entry)

        assert entry in imdb_set