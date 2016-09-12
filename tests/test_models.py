# coding=utf-8
from __future__ import unicode_literals

import collections
import datetime
import logging
import unittest
import datetime

from requests import HTTPError

from bandsintao.client import Artist, ApiConfig

logger = logging.getLogger(__name__)

ArtistId = collections.namedtuple("ArtistId", ("music_brainz_id", "facebook_id", "name"))

lil_wayne = ArtistId("ac9a487a-d9d2-4f27-bb23-0f4686488345", "fbid_6885814958", "Lil Wayne")
skrillex = ArtistId("ae002c5d-aac6-490b-a39a-30aa9e2edf2b", "", "Skrillex")


class GeneralTestCase(unittest.TestCase):
    __test__ = True
    longMessage = True
    maxDiff = None

    def tearDown(self):
        ApiConfig.AppId = None

    def test_get_without_app_id(self):
        with self.assertRaises(HTTPError):
            obj = Artist.load(name=lil_wayne.name, artist_id=lil_wayne.facebook_id)
            logger.debug("obj => %s", obj)

    def test_get(self):
        ApiConfig.init(app_id="testing")
        obj = Artist.load(name=lil_wayne.name, artist_id=lil_wayne.facebook_id)
        logger.debug("obj => %s", obj)

    def test_events(self):
        ApiConfig.init(app_id="testing")
        obj = Artist.load(name=skrillex.name, artist_id=skrillex.music_brainz_id)
        self.assertIsNotNone(obj.events)


class LocationTestCase(unittest.TestCase):
    __test__ = True
    longMessage = True
    maxDiff = None

    def test_event(self):
        ApiConfig.init(app_id="testing")
        obj = Artist.load(name=skrillex.name, artist_id=skrillex.music_brainz_id)
        self.assertIsNotNone(obj.events)
        logger.debug("There are %s events to observe...", len(obj.events))
        for event in obj.events:
            # Ensure that the event datetime is parsed into a datetime object
            self.assertIsInstance(event.datetime, datetime.datetime)
            logger.debug("event.venue => %s", event.venue)
