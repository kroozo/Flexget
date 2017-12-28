from __future__ import unicode_literals, division, absolute_import
from builtins import *  # noqa pylint: disable=unused-import, redefined-builtin

import pytest

from flexget.manager import Session
from flexget.plugins.filter.upgrade import EntryUpgrade


class TestUpgrade(object):
    config = """
        tasks:
          first_download:
            accept_all: yes
            mock:
              - {title: 'Movie.720p.WEB-DL.X264.AC3', 'id': 'Movie'}
          no_tracking:
            accept_all: yes
            upgrade:
              tracking: no
            mock:
              - {title: 'Movie.BRRip.x264.720p', 'id': 'Movie'} 
          upgrade_quality:
            upgrade: yes
            mock:
              - {title: 'Movie.1080p.720p WEB-DL X264 AC3', 'id': 'Movie'}
              - {title: 'Movie.720p.WEB-DL.X264.AC3', 'id': 'Movie'}
              - {title: 'Movie.BRRip.x264.720p', 'id': 'Movie'}
          reject_lower:
            upgrade:
              on_lower: reject
            mock:
              - {title: 'Movie.1080p.BRRip.X264.AC3', 'id': 'Movie'}
              - {title: 'Movie.1080p.720p WEB-DL X264-EVO', 'id': 'Movie'}
              - {title: 'Movie.BRRip.x264.720p', 'id': 'Movie'}
    """

    def test_learn(self, execute_task):
        execute_task('first_download')
        with Session() as session:
            query = session.query(EntryUpgrade).all()
            assert len(query) == 1, 'There should be one tracked entity present.'
            assert query[0].id == 'movie', 'Should of tracked name `Movie`.'

    def test_no_tracking(self, execute_task):
        execute_task('no_tracking')
        with Session() as session:
            assert len(session.query(EntryUpgrade).all()) == 0, 'There should be one tracked entity present.'

    def test_upgrade_quality(self, execute_task):
        execute_task('first_download')
        task = execute_task('upgrade_quality')
        entry = task.find_entry('accepted', title='Movie.1080p.720p WEB-DL X264 AC3')
        assert entry, 'Movie.1080p.720p WEB-DL X264 AC3 should have been accepted'

    def test_reject_lower(self, execute_task):
        execute_task('first_download')
        task = execute_task('reject_lower')
        entry = task.find_entry('accepted', title='Movie.1080p.BRRip.X264.AC3')
        assert entry, 'Movie.1080p.BRRip.X264.AC3 should have been accepted'
        entry = task.find_entry('rejected', title='Movie.1080p.720p WEB-DL X264-EVO')
        assert entry, 'Movie.1080p.720p WEB-DL X264-EVO should have been rejected'
        entry = task.find_entry('rejected', title='Movie.BRRip.x264.720p')
        assert entry, 'Movie.BRRip.x264.720p should have been rejected'


class TestUpgradeTarget(object):
    config = """
        tasks:
          existing_download_480p:
            accept_all: yes
            mock:
              - {title: 'Movie.480p.WEB-DL.X264.AC3', 'id': 'Movie'}
          existing_download_1080p:
            accept_all: yes
            mock:
              - {title: 'Movie.1080p.WEB-DL.X264.AC3', 'id': 'Movie'}
          target_outside_range:
            upgrade:
              target: 720p-1080p
            mock:
              - {title: 'Movie.HDRip.XviD.AC3', 'id': 'Movie'}
          target_within_range:
            upgrade:
              target: 720p-1080p
            mock:
              - {title: 'Movie.2160p WEB-DL X264 AC3', 'id': 'Movie'}
              - {title: 'Movie.1080p WEB-DL X264 AC3', 'id': 'Movie'}
              - {title: 'Movie.720p.WEB-DL.X264.AC3', 'id': 'Movie'}
          target_quality_1080p:
            upgrade:
              target: 1080p
            mock:
              - {title: 'Movie.1080p WEB-DL X264 AC3', 'id': 'Movie'}
              - {title: 'Movie.720p.WEB-DL.X264.AC3', 'id': 'Movie'}
    """

    def test_target_outside_range(self, execute_task):
        execute_task('existing_download_480p')
        task = execute_task('target_outside_range')
        entry = task.find_entry('undecided', title='Movie.HDRip.XviD.AC3')
        assert entry, 'Movie.HDRip.XviD.AC3 should have been undecided'

    def test_target_within_range(self, execute_task):
        execute_task('existing_download_480p')
        task = execute_task('target_within_range')
        entry = task.find_entry('accepted', title='Movie.1080p WEB-DL X264 AC3')
        assert entry, 'Movie.1080p WEB-DL X264 AC3 should have been accepted'

        for title in ['Movie.2160p WEB-DL X264 AC3', 'Movie.720p.WEB-DL.X264.AC3']:
            entry = task.find_entry('undecided', title=title)
            assert entry, '%s should have been undecided' % title

    def test_target_quality_1080p(self, execute_task):
        execute_task('existing_download_480p')
        task = execute_task('target_quality_1080p')
        entry = task.find_entry('accepted', title='Movie.1080p WEB-DL X264 AC3')
        assert entry, 'Movie.1080p WEB-DL X264 AC3 should have been accepted'
        entry = task.find_entry('undecided', title='Movie.720p.WEB-DL.X264.AC3')
        assert entry, 'Movie.720p.WEB-DL.X264.AC3 should have been undecided'

    def test_at_target(self, execute_task):
        execute_task('existing_download_1080p')
        task = execute_task('target_quality_1080p')
        entry = task.find_entry('undecided', title='Movie.1080p WEB-DL X264 AC3')
        assert entry, 'Movie.1080p WEB-DL X264 AC3 should have been accepted'
        entry = task.find_entry('undecided', title='Movie.720p.WEB-DL.X264.AC3')
        assert entry, 'Movie.720p.WEB-DL.X264.AC3 should have been undecided'


class TestUpgradeIdentifiers(object):
    config = """
        tasks:
          first_download:
            accept_all: yes
            mock:
              - {title: 'Smoke.720p.WEB-DL.X264.AC3', 'id': 'Smoke'}
          identified_by:
            upgrade:
              identified_by: "{{ movie_name }}"
            mock:
              - {title: 'Smoke.1080p.BRRip.X264.AC3', 'id': 'Smoke', 'movie_name': 'Smoke'}
          imdb_download:
            accept_all: yes
            imdb_lookup: yes
            mock:
              - {title: 'Smoke.720p.WEB-DL.X264.AC3'}
          imdb_upgrade:
            accept_all: yes
            imdb_lookup: yes
            mock:
              - {title: 'Smoke.1080p.BRRip.X264.AC3'}
    """

    @pytest.mark.online
    def test_imdb(self, execute_task):
        execute_task('imdb_download')
        task = execute_task('imdb_upgrade')
        entry = task.find_entry('accepted', title='Smoke.1080p.BRRip.X264.AC3')
        assert entry, 'Smoke.1080p.BRRip.X264.AC3 should have been accepted'

    def test_identified_by(self, execute_task):
        execute_task('first_download')
        task = execute_task('identified_by')
        entry = task.find_entry('accepted', title='Smoke.1080p.BRRip.X264.AC3')
        assert entry, 'Smoke.1080p.BRRip.X264.AC3 should have been accepted'
