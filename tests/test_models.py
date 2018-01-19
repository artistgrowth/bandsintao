# coding=utf-8
from __future__ import unicode_literals

import codecs
import collections
import datetime
import logging
import os
import unittest

import mock
import requests
from requests import HTTPError

from bandsintao import jjson
from bandsintao.client import Artist, ApiConfig

logger = logging.getLogger(__name__)


def _load_test_file_raw(filename, dir_name="", encoding="utf-8"):
    # Get paths relative to the current object
    if dir_name:
        dir_name = os.path.join(os.path.dirname(__file__), dir_name)
    else:
        dir_name = os.path.join(os.path.dirname(__file__))

    file_path = os.path.join(dir_name, filename)
    with codecs.open(file_path, "r", encoding=encoding) as test_file:
        output = test_file.read()
    return output


class ArtistId(collections.namedtuple("ArtistId", ("artist_id", "slug", "music_brainz_id", "facebook_id"))):
    @staticmethod
    def load_from_slug(slug):
        """
        Loads the artist.json file, e.g.:

            {
                "name": "Ty Dolla $ign",
                "image_url": "https://s3.amazonaws.com/bit-photos/large/6937821.jpeg",
                "thumb_url": "https://s3.amazonaws.com/bit-photos/thumb/6937821.jpeg",
                "facebook_tour_dates_url": "http://www.bandsintown.com/TyDolla%24ign/facebookapp?came_from=67",
                "facebook_page_url": "https://www.facebook.com/tydollasign",
                "mbid": null,
                "tracker_count": 330440,
                "upcoming_event_count": 3
            }


        :param slug:
        :return: A new instance of `ArtistId`
        """
        raw = _load_test_file_raw(filename="artist.json", dir_name=os.path.join("data", slug))
        data = jjson.loads(raw)
        return ArtistId(data.get("name"), slug, data.get("mbid"), None)


lil_wayne = ArtistId.load_from_slug("LilWayne")
skrillex = ArtistId.load_from_slug("Skrillex")
metallica = ArtistId.load_from_slug("Metallica")
rhcp = ArtistId.load_from_slug("RedHotChiliPeppers")
kings_of_leon = ArtistId.load_from_slug("KingsofLeon")
ty_dolla = ArtistId.load_from_slug("TyDolla$ign")


class ArtistTestCase(unittest.TestCase):
    def _test_get_identifier(self, entity, slug_only=False):
        logger.debug("Testing with entity => %s", entity)

        with mock.patch("bandsintao.client.polite_request") as mocked_request:
            # Retain everything else from the Response object
            response = requests.models.Response()
            # Requests can handles the encoding
            content = _load_test_file_raw("artist.html", dir_name=os.path.join("data", entity.slug), encoding=None)
            response._content = content
            response.status_code = requests.codes.ok
            mocked_request.return_value = response
            if slug_only:
                url_or_slug = entity.slug
            else:
                url_or_slug = "http://www.bandsintown.com/{}".format(entity.slug)
            identifier, slug = Artist.get_identifier(url_or_slug)
            self.assertEqual(slug, entity.slug)
            self.assertEqual(identifier, entity.artist_id)

    def test_get_identifier(self):
        self._test_get_identifier(rhcp)

    def test_get_identifier_only_slug(self):
        self._test_get_identifier(kings_of_leon, True)

    def test_get_identifier_special_characters_only_slug(self):
        self._test_get_identifier(ty_dolla, True)

    def test_get_identifier_special_characters(self):
        self._test_get_identifier(ty_dolla, False)


class TestCaseBase(unittest.TestCase):
    __test__ = False
    longMessage = True
    maxDiff = None

    def tearDown(self):
        ApiConfig.AppId = None

    def _make_request(self, entity, filename="artist.json"):
        def our_mocked_polite_request(url, *args, **kwargs):
            # Retain everything else from the Response object
            response = requests.models.Response()
            # Requests can handles the encoding
            content = _load_test_file_raw(filename, dir_name=os.path.join("data", entity.slug))
            response._content = content
            mocked_request = mock.MagicMock(url=url)
            response.request = mocked_request
            return response

        with mock.patch("requests_toolbelt.utils.dump.dump_response", new=mock.MagicMock()):
            with mock.patch("bandsintao.client.polite_request") as mocked_polite_request:
                mocked_polite_request.side_effect = our_mocked_polite_request

                obj = Artist.load(slug=entity.slug, artist_id=entity.artist_id)
                self.assertIsNotNone(obj)
                logger.debug("obj => %s", obj)
        return obj


class GeneralTestCase(TestCaseBase):
    __test__ = True

    def test_get_without_app_id(self):
        with self.assertRaises(HTTPError):
            Artist.load(slug=lil_wayne.artist_id, artist_id=lil_wayne.facebook_id)

    def test_get(self):
        ApiConfig.init(app_id="testing")
        self._make_request(lil_wayne)

    def test_events(self):
        ApiConfig.init(app_id="testing")
        obj = self._make_request(skrillex)
        self.assertIsNotNone(obj)
        self.assertIsNotNone(obj.events)


class LocationTestCase(TestCaseBase):
    __test__ = True

    def test_event(self):
        ApiConfig.init(app_id="testing")
        entity = skrillex

        obj = self._make_request(entity)
        self.assertIsNotNone(obj)

        with mock.patch("requests_toolbelt.utils.dump.dump_response", new=mock.MagicMock()):
            with mock.patch("bandsintao.client.polite_request") as mocked_polite_request:
                # Retain everything else from the Response object
                response = requests.models.Response()
                # Requests can handles the encoding
                content = _load_test_file_raw("upcoming.json", dir_name=os.path.join("data", entity.slug))
                response._content = content
                mocked_polite_request.return_value = response

                self.assertIsNotNone(obj.events)
                logger.debug("There are %s events to observe...", len(obj.events))
                for event in obj.events:
                    # Ensure that the event datetime is parsed into a datetime object
                    self.assertIsInstance(event.datetime, datetime.datetime)
                    logger.debug("event.venue => %s", event.venue)
