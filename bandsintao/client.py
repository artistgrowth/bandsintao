# coding=utf-8
import hashlib
import logging
import operator
import socket
import urllib.parse

# noinspection PyPackageRequirements
import requests
import requests.adapters
import requests_toolbelt.utils.dump as toolbelt

from . import jjson

logger = logging.getLogger(__name__)


class ApiConfig(object):
    AppId = None
    Version = "3.0"
    Format = "json"
    BaseUri = "https://rest.bandsintown.com"
    Debug = False

    @staticmethod
    def init(app_id, uri=None, version=None):
        if not app_id:
            raise ValueError("app_id: Expected something but got \"{}\"".format(app_id))
        ApiConfig.AppId = app_id
        ApiConfig.BaseUri = uri or ApiConfig.BaseUri
        ApiConfig.Version = version or ApiConfig.Version


def polite_request(url, timeout_seconds=30, max_retries=5, **params):
    """
    Tries its hardest not to vomit all over your request. Has retries for the requests
    Session and a timeout for the request. The following exceptions are documented here:
    http://docs.python-requests.org/en/latest/user/quickstart/#errors-and-exceptions
    """
    with requests.Session() as session:
        try:
            session.mount("http://", requests.adapters.HTTPAdapter(max_retries=max_retries))
            session.mount("https://", requests.adapters.HTTPAdapter(max_retries=max_retries))
            logger.debug("Sending request url => %s with params => %s", url, params)
            response = session.get(url=url, timeout=timeout_seconds, params=params)
        except requests.exceptions.ConnectionError:
            logger.exception("ConnectionError: A connection error occurred")
            raise
        except requests.exceptions.Timeout:
            logger.exception("Timeout: The request timed out")
            raise
        except socket.timeout:
            # We also have to catch socket timeouts due to the underlying urllib3 library:
            # https://github.com/kennethreitz/requests/issues/1236
            logger.exception("Socket timeout: The request timed out")
            raise
        except requests.exceptions.TooManyRedirects:
            logger.exception("TooManyRedirects: The url => \"%s\" has too many redirects", url)
            raise
        except requests.exceptions.RequestException:
            logger.exception("IO Error")
            raise

    return response


def send_request(url, expected_type, **params):
    defaults = {
        "api_version": ApiConfig.Version,
        "app_id": ApiConfig.AppId,
        "format": ApiConfig.Format,
    }
    params.update(defaults)
    resolved_url = urllib.parse.urljoin(ApiConfig.BaseUri, url)
    response = polite_request(resolved_url, **params)

    # Ensure datetime objects may be decoded
    payload = jjson.loads(response.content)

    if ApiConfig.Debug and logger.isEnabledFor(logging.DEBUG):
        data = toolbelt.dump_response(response)
        data = data.decode("utf-8").strip().replace("\r\n", "\n")
        boundary = "\n> \n"
        index = data.rfind(boundary) + 4
        raw = data[index:]
        data = data[0:index]
        raw = jjson.loads(raw)
        logger.debug("\n%s\n%s\n", data, jjson.dumps(raw, sort_keys=True, indent=4))

    response.raise_for_status()
    if not isinstance(payload, expected_type):
        message = "Error loading {} with params {}: response expected {} but was {}".format(url,
                                                                                            params,
                                                                                            expected_type,
                                                                                            type(payload))
        raise ValueError(message)
    if "error" in payload:
        raise ValueError("Error loading {} with params {}: {}".format(url, params, payload["error"]))

    return payload


class BaseApiObject(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return jjson.dumps(self, sort_keys=True, indent=4)

    def __setattr__(self, key, value):
        if key in self:
            self[key] = value
        elif not hasattr(self, key):
            self[key] = value
        else:
            raise AttributeError("Cannot set '{}', cls attribute already exists".format(key))

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError

    @property
    def hash(self):
        m = hashlib.md5()
        for key, value in sorted(self.items(), key=operator.itemgetter(0)):
            m.update("{}:{}".format(key, str(value).encode("utf-8")))
        return m.hexdigest()


class Venue(BaseApiObject):
    """
        Venue JSON Format
        [{
            "name": "Curacao North Sea Jazz Festival",
            "city": "Willemstad",
            "region": "",
            "country": "Netherlands",
            "latitude": "51.7",
            "longitude": "4.4333333"
        }]
    """
    pass


class Event(BaseApiObject):
    """
    http://www.bandsintown.com/api/responses#events-json

    Event JSON format:
    [{
        "id": "1009274195",
        "artist_id": "409",
        "datetime": "2018-08-31T19:00:00",
        "description": "",
        "on_sale_datetime": "",
        "url": "https:\/\/www.bandsintown.com\/e\/1009274195?app_id=artistgrowth-dev&came_from=267",
        "offers": [
            {
                "type": "Tickets",
                "url": "https:\/\/www.bandsintown.com\/t\/1009274195?app_id=YOUR_APP_ID&came_from=267",
                "status": "available"
            }
        ],
        "lineup": [
            "Damian Marley"
        ],
        "venue": {
            "name": "Curacao North Sea Jazz Festival",
            "city": "Willemstad",
            "region": "",
            "country": "Netherlands",
            "latitude": "51.7",
            "longitude": "4.4333333"
        }
    }]
    """

    @staticmethod
    def parse(data):
        event = Event(**data)
        event.artists = ArtistLoader(data.get("lineup", []))
        venue = data.get("venue")
        event.venue = Venue(**venue) if venue else None
        return event

    @staticmethod
    def parse_all(data):
        events = [Event.parse(event) for event in data]
        return events

    @staticmethod
    def _generate_params(**kwargs):
        artist_id = kwargs.get("artist_id")
        if not artist_id:
            raise ValueError("artist_id required")
        else:
            kwargs["artists[]"] = artist_id
            del kwargs["artist_id"]

        radius = kwargs.get("radius")
        if radius is not None and radius > 150:
            raise ValueError("Maximum radius is 150")
        per_page = kwargs.get("per_page")
        if per_page is not None and per_page > 100:
            raise ValueError("Maximum 100 per page")

        kwargs.setdefault("date", "upcoming")

        return dict(filter(lambda __: __[0] or False, kwargs.items()))

    @staticmethod
    def search(artist_id=None, location=None, radius=None, date=None, page=None, per_page=None):
        params = Event._generate_params(**locals())
        return Event.parse_all(send_request("/events/search", list, **params))

    @staticmethod
    def recommended(artist_id=None, location=None, radius=None, date=None, only_recs=None, page=None, per_page=None):
        only_recs = only_recs and "true" or "false"
        params = Event._generate_params(**locals())
        return Event.parse_all(send_request("/events/recommended", list, **params))

    @staticmethod
    def daily():
        return Event.parse_all(send_request("/events/daily", list))


class Artist(BaseApiObject):
    """
    Contains information about one artist. Also contains methods for getting
    information about all events for an artist.

    https://www.bandsintown.com/api/responses#artist-json

    Artist JSON format:
    {
        "id": "409",
        "name": "Damian Marley",
        "image_url": "https://s3.amazonaws.com/bit-photos/large/8667699.jpeg",
        "thumb_url": "https://s3.amazonaws.com/bit-photos/thumb/8667699.jpeg",
        "url": "https://www.bandsintown.com/a/409?came_from=267&app_id=YOUR_APP_ID",
        "facebook_page_url": "https://www.facebook.com/damianmarley",
        "mbid": "cbfb9bcd-c5a0-4d7c-865f-2c641c171e1c",
        "upcoming_event_count": 16,
        "tracker_count": 453885
    }
    """

    def __init__(self, *args, **kwargs):
        self._events = None
        super().__init__(*args, **kwargs)

    @property
    def events(self):
        if not self._events:
            data = send_request("/artists/{}/events".format(self.name), list, artist_id=self.id)
            self._events = Event.parse_all(data)

        return self._events

    @staticmethod
    def _clean_slug(val, fb_lookup):
        if val and isinstance(val, str):
            for find, replace in [
                ("/", "%252F"),
                ("?", "%253F"),
                ("*", "%252A"),
                ("\"", "%27C"),
            ]:
                val = val.replace(find, replace)
        elif val and isinstance(val, int):
            val = f"id_{val}" if not fb_lookup else f"fbid_{val}"
        return val

    @staticmethod
    def load(lookup_val, fb_lookup=False, verify_id=None):
        """
        Load the artist payload into a helper object for consumption. You may pass either the artist name, the
        numeric ID, or the Facebook page ID into the lookup_val parameter. Note: If you would like to perform
        an artist lookup by Facebook page ID, you must pass fb_lookup=True into this method.

        You may also pass the expected payload "id" into here for validation of artist payload returned.
        :param lookup_val:
        :param fb_lookup:
        :param verify_id:
        :return:
        """
        slug = Artist._clean_slug(lookup_val, fb_lookup)
        data = send_request("/artists/{}".format(slug), dict)

        if isinstance(verify_id, int):
            verify_id = str(verify_id)
        if isinstance(verify_id, str) and data["id"] != verify_id:
            raise ValueError("Wrong artist payload was returned, somehow")

        data["slug"] = slug
        data["upcoming_event_count"] = data.get("upcoming_event_count", 0)
        return Artist(**data)


class LazyLoader(object):
    loader_klass = None

    def __init__(self, initial_data):
        if self.loader_klass is None:
            raise ValueError("You need to set the loader_klass")

        self._data = initial_data

    def __len__(self):
        return len(self._data)

    def __getitem__(self, item):
        return self._load(item)

    def __iter__(self):
        for i in range(len(self)):
            return self._load(i)

    def _load(self, i):
        item = self._data[i]
        if not isinstance(item, self.loader_klass):
            item = self.loader_klass.load(item)
            self._data[i] = item

        return item


class ArtistLoader(LazyLoader):
    loader_klass = Artist
