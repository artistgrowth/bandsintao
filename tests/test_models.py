# coding=utf-8
from __future__ import unicode_literals

import codecs
import collections
import datetime
import logging
import os
import unittest
import inspect

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


class ArtistId(collections.namedtuple("ArtistId", ("artist_id", "slug", "music_brainz_id", "facebook_id", "expected"))):
    @staticmethod
    def load_from_slug(slug, expected=None):
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
        return ArtistId(data.get("name"), slug, data.get("mbid"), None, expected)


class lazy_property(object):
    """
    Meant to be used for lazy evaluation of an object attribute.
    property should represent non-mutable data, as it replaces itself.
    """

    def __init__(self, fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        return value


class ArtistData(object):
    @lazy_property
    def lil_wayne(self):
        return ArtistId.load_from_slug("Lil Wayne")

    @lazy_property
    def skrillex(self):
        return ArtistId.load_from_slug("Skrillex")

    @lazy_property
    def metallica(self):
        return ArtistId.load_from_slug("Metallica")

    @lazy_property
    def rhcp(self):
        return ArtistId.load_from_slug("Red Hot Chili Peppers")

    @lazy_property
    def kings_of_leon(self):
        return ArtistId.load_from_slug("Kings of Leon")

    @lazy_property
    def ty_dolla(self):
        return ArtistId.load_from_slug("Ty Dolla $ign")

    @lazy_property
    def ti3sto(self):
        return ArtistId.load_from_slug("Tiësto", "Tiesto")

    @lazy_property
    def judah_and_the_lion(self):
        return ArtistId.load_from_slug("Judah & The Lion")


_data = ArtistData()


class ArtistTestCase(unittest.TestCase):
    def _test_get_identifier(self, entity, slug_only=False):
        logger.debug("Testing with entity => %s", entity)

        with mock.patch("bandsintao.client.polite_request") as mocked_request:
            # Retain everything else from the Response object
            response = requests.models.Response()
            # Requests can handles the encoding
            content = _load_test_file_raw("artist.html", dir_name=os.path.join("data", entity.slug))
            response._content = content
            response.status_code = requests.codes.ok
            mocked_request.return_value = response
            if slug_only:
                url_or_slug = entity.slug
            else:
                url_or_slug = "https://www.bandsintown.com/{}".format(entity.slug)
            identifier, slug = Artist.get_identifier(url_or_slug)
            self.assertEqual(slug, entity.expected or entity.slug)
            self.assertEqual(identifier, entity.artist_id)
            return identifier, slug

    def test_get_identifier(self):
        self._test_get_identifier(_data.rhcp)
        self._test_get_identifier(_data.judah_and_the_lion)

    def test_get_identifier_only_slug(self):
        self._test_get_identifier(_data.kings_of_leon, True)

    def test_get_identifier_special_characters_only_slug(self):
        self._test_get_identifier(_data.ty_dolla, True)

    def test_get_identifier_special_characters(self):
        self._test_get_identifier(_data.ty_dolla, False)

    def test_testio(self):
        """
        Ensure these types of URLs work:

            https://www.bandsintown.com/a/30843-tiesto
            https://www.bandsintown.com/a/30843

        :return:
        """
        self._test_get_identifier(_data.ti3sto, True)

    def test_get_identifier_with_ampersands(self):
        self._test_get_identifier(_data.judah_and_the_lion)


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
            response.status_code = requests.codes.ok
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
            Artist.load(slug=_data.lil_wayne.artist_id, artist_id=_data.lil_wayne.facebook_id)

    def test_get(self):
        ApiConfig.init(app_id="testing")
        self._make_request(_data.lil_wayne)
        self._make_request(_data.judah_and_the_lion)

    def test_events(self):
        ApiConfig.init(app_id="testing")
        obj = self._make_request(_data.skrillex)
        self.assertIsNotNone(obj)
        self.assertIsNotNone(obj.events)

    def test_events2(self):
        ApiConfig.init(app_id="testing")
        for name, artist_id in inspect.getmembers(_data, lambda __: isinstance(__, ArtistId)):
            obj = self._make_request(artist_id)
            self.assertIsNotNone(obj)
            self.assertIsNotNone(obj.events)
            self.assertEqual(obj["mbid"], artist_id.music_brainz_id)


class LocationTestCase(TestCaseBase):
    __test__ = True

    def test_event(self):
        ApiConfig.init(app_id="testing")
        entity = _data.skrillex

        obj = self._make_request(entity)
        self.assertIsNotNone(obj)

        with mock.patch("requests_toolbelt.utils.dump.dump_response", new=mock.MagicMock()):
            with mock.patch("bandsintao.client.polite_request") as mocked_polite_request:
                # Retain everything else from the Response object
                response = requests.models.Response()
                # Requests can handles the encoding
                content = _load_test_file_raw("upcoming.json", dir_name=os.path.join("data", entity.slug))
                response._content = content
                response.status_code = requests.codes.ok
                mocked_polite_request.return_value = response

                self.assertIsNotNone(obj.events)
                logger.debug("There are %s events to observe...", len(obj.events))
                for event in obj.events:
                    # Ensure that the event datetime is parsed into a datetime object
                    self.assertIsInstance(event.datetime, datetime.datetime)
                    logger.debug("event.venue => %s", event.venue)
