# coding=utf-8
from __future__ import unicode_literals

import hashlib
import logging
import operator
import re
import socket
import urlparse

# noinspection PyPackageRequirements
import bs4
import requests
import requests.adapters
import requests_toolbelt.utils.dump as toolbelt
import six

import jjson

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
    Tries it's hardest not to vomit all over your request. Has retries for the requests
    Session and a timeout for the request. The following exceptions are documented here:
    http://docs.python-requests.org/en/latest/user/quickstart/#errors-and-exceptions
    """
    response = None
    with requests.Session() as session:
        try:
            session.mount("http://", requests.adapters.HTTPAdapter(max_retries=max_retries))
            session.mount("https://", requests.adapters.HTTPAdapter(max_retries=max_retries))
            logger.debug("Sending request url => %s with params => %s", url, params)
            response = session.get(url=url, timeout=timeout_seconds, params=params)
        except requests.exceptions.ConnectionError:
            logger.exception("ConnectionError: A connection error occurred")
        except requests.exceptions.Timeout:
            logger.exception("Timeout: The request timed out")
        except socket.timeout:
            # We also have to catch socket timeouts due to the underlying urllib3 library:
            # https://github.com/kennethreitz/requests/issues/1236
            logger.exception("Socket timeout: The request timed out")
        except requests.exceptions.TooManyRedirects:
            logger.exception("TooManyRedirects: The url => \"%s\" has too many redirects", url)
        except requests.exceptions.RequestException:
            logger.exception("Error")

    return response


def send_request(url, **params):
    defaults = {
        "api_version": ApiConfig.Version,
        "app_id": ApiConfig.AppId,
        "format": ApiConfig.Format,
    }
    params.update(defaults)
    resolved_url = urlparse.urljoin(ApiConfig.BaseUri, url)
    response = polite_request(resolved_url, **params)

    # Ensure datetime objects may be decoded
    payload = response.json(object_hook=jjson.custom_deserializer)

    if ApiConfig.Debug and logger.isEnabledFor(logging.DEBUG):
        data = toolbelt.dump_response(response)
        data = data.decode("utf-8").strip().replace("\r\n", "\n")
        boundary = "\n> \n"
        index = data.rfind(boundary) + 4
        raw = data[index:]
        data = data[0:index]
        raw = jjson.loads(raw)
        logger.debug("\n%s\n%s\n", data, jjson.dumps(raw, sort_keys=True, indent=4))

    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    return payload


@six.python_2_unicode_compatible
class BaseApiObject(dict):
    def __init__(self, *args, **kwargs):
        super(BaseApiObject, self).__init__(*args, **kwargs)
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __str__(self):
        return jjson.dumps(self, sort_keys=True, indent=4)

    def __setattr__(self, key, value):
        if key in self.keys():
            self[key] = value
        elif not hasattr(self, key):
            self[key] = value
        else:
            raise AttributeError("Cannot set '{}', cls attribute already exists".format(key))

    def __getattr__(self, key):
        if key in self.keys():
            return self[key]
        raise AttributeError

    @property
    def hash(self):
        m = hashlib.md5()
        for key, value in sorted(self.iteritems(), key=operator.itemgetter(0)):
            m.update("{}:{}".format(key, six.text_type(value).encode("utf-8")))
        return m.hexdigest()


class Venue(BaseApiObject):
    """
        Venue JSON Format
        [{
            "city": "Lovelaceville",
            "name": "SBT Ranch",
            "country": "United States",
            "region": "KY",
            "longitude": "-88.8308333",
            "latitude": "36.9686111"
        }]
    """
    pass


class Event(BaseApiObject):
    """

    http://www.bandsintown.com/api/responses#events-json

    Event JSON format:
    [{
        "id": 4189861,
        "title": "Nas @ UB Stadium in Buffalo, NY",
        "datetime": "2011-04-29T19:00:00",
        "formatted_datetime": "Friday, April 29, 2011 at 7:00pm",
        "formatted_location": "Buffalo, NY",
        "ticket_url": "http://www.bandsintown.com/event/4189861/buy_tickets?artist=Nas",
        "ticket_type": "Tickets",
        "ticket_status": "available",
        "on_sale_datetime": "2011-03-08T10:00:00",
        "facebook_rsvp_url": "http://www.bandsintown.com/event/4189861?artist=Nas",
        "description": "2011 Block Party: featuring Kid Cudi, Damian Marley, Nas & Spec. Guest",
        "artists": [{
            "name": "Nas",
            "mbid": "cfbc0924-0035-4d6c-8197-f024653af823",
            "image_url": "http://www.bandsintown.com/Nas/photo/medium.jpg",
            "thumb_url": "http://www.bandsintown.com/Nas/photo/small.jpg",
            "facebook_tour_dates_url": "http://bnds.in/e5CP5L"
        }],
        "venue": {
            "name": "UB Stadium",
            "city": "Buffalo",
            "region": "NY",
            "country": "United States",
            "latitude": 43.0004710,
            "longitude" : -78.7802170
        }
    }]
    """

    @staticmethod
    def parse(data):
        event = Event(**data)
        event.artists = [Artist(**__) for __ in data.get("artists", []) if __]
        event.venue = Venue(**data.get("venue", {}))
        return event

    @staticmethod
    def parse_all(data):
        events = []
        for event in data:
            events.append(Event.parse(event))
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

        return dict(filter(lambda __: __[0] or False, kwargs.iteritems()))

    @staticmethod
    def search(artist_id=None, location=None, radius=None, date=None, page=None, per_page=None):
        params = Event._generate_params(**locals())
        return Event.parse_all(send_request("/events/search", **params))

    @staticmethod
    def recommended(artist_id=None, location=None, radius=None, date=None, only_recs=None, page=None, per_page=None):
        only_recs = only_recs and "true" or "false"
        params = Event._generate_params(**locals())
        return Event.parse_all(send_request("/events/recommended", **params))

    @staticmethod
    def daily():
        return Event.parse_all(send_request("/events/daily"))


class Artist(BaseApiObject):
    """
    Contains information about one artists. Also methods for getting
    information about one artist or all events for an artist

    https://www.bandsintown.com/api/responses#artist-json

    Artist JSON format:
    {
        "name": "Damian Marley",
        "image_url": "http://www.bandsintown.com/DamianMarley/photo/medium.jpg",
        "thumb_url": "http://www.bandsintown.com/DamianMarley/photo/small.jpg",
        "facebook_tour_dates_url": "http://bnds.in/jrHVeT",
        "mbid": "cbfb9bcd-c5a0-4d7c-865f-2c641c171e1c",
        "upcoming_events_count": 7
    }
    """

    def __init__(self, *args, **kwargs):
        self._events = None
        super(Artist, self).__init__(*args, **kwargs)

    @property
    def events(self):
        if not self._events:
            data = send_request("/artists/{}/events".format(self.name), artist_id=self.artist_id)
            self._events = Event.parse_all(data)

        return self._events

    @staticmethod
    def _clean_slug(val):
        if val and isinstance(val, six.string_types):
            val = re.sub(" ", "", val, flags=re.UNICODE)
        return val

    @staticmethod
    def _extract_meta(response):
        """
        Extract the actual identifier from loading the corresponding bandsintown page

        Yes this is a hack, but there's really no other way to do this....
        :param response: The http response
        :return: The bandsintown artist id
        """
        identifier = None
        if response.status_code != requests.codes.ok:
            logger.debug("Unable to extract identifier, status code %s", response.status_code)
            return identifier

        soup = bs4.BeautifulSoup(response.content, "html.parser")

        # Prefer the <meta property="og:title"> tag first, this helps to minimize encoding/decoding issues
        # We do this first because Bandsintown is not properly encoding artist names with ampersands
        element = soup.find("meta", attrs={"property": "og:title"})
        if element:
            identifier = element.get("content", "")

        # Fallback and attempt to extract the artist id from one of the meta tags
        if not element or not identifier:
            for meta in soup.find_all("meta"):
                content_attr = meta.get("content", "")
                if content_attr.startswith("bitcon://") or content_attr.startswith("bitintent://"):
                    # Url encoding uses ASCII codepoints only - make sure we don't pass something in UTF-8
                    content_attr = content_attr.encode("ASCII")
                    content_url_parsed = urlparse.urlparse(content_attr)
                    if content_url_parsed and content_url_parsed.query:
                        query_data = urlparse.parse_qs(content_url_parsed.query)
                        if "artist" in query_data or "artist_name" in query_data:
                            # Found it
                            identifier = query_data.get("artist", query_data.get("artist_name"))
                            if isinstance(identifier, list):
                                identifier = identifier[0]
                                # We also need to unquote this value (i.e. it's url encoded)
                                identifier = urlparse.unquote(identifier)
                            else:
                                raise ValueError("Invalid condition - identifer could not be ... identified")
                            break

        if identifier is not None and isinstance(identifier, six.binary_type):
            identifier = identifier.decode("utf-8")

        return identifier

    _url_pattern_domain = "(?:https?://)?(?:(?:www\.)?bandsintown\.com)?/"
    _url_pattern_numslug = "(?:{}a/(?P<numslug>\\d+).*)".format(_url_pattern_domain)
    _url_pattern_slug = "(?:{}(?P<slug>[^/]+).*)".format(_url_pattern_domain)
    _url_pattern = r"^{}$".format("|".join((_url_pattern_numslug, _url_pattern_slug)))
    _url_regex = re.compile(_url_pattern, re.UNICODE | re.IGNORECASE)

    @staticmethod
    def get_identifier(url_or_slug_or_id):
        match = Artist._url_regex.match(url_or_slug_or_id)
        if match:
            groups = match.groupdict()
            slug = groups.get("numslug") or groups.get("slug")
            slug = Artist._clean_slug(slug)
        else:
            slug = url_or_slug_or_id

        if re.match(r"\d+", slug):
            slug = "a/{}".format(slug)
        url = "https://www.bandsintown.com/{}".format(slug)
        response = polite_request(url)
        identifier = Artist._extract_meta(response)
        slug = Artist._clean_slug(identifier)

        if not identifier:
            raise ValueError("Could not extract identifer from %s", url)

        return identifier, slug

    @staticmethod
    def load(artist_id, slug=None):
        if not slug:
            slug = Artist._clean_slug(artist_id)

        data = send_request("/artists/{}".format(slug), artist_id=artist_id)
        data["artist_id"] = artist_id
        data["slug"] = slug
        data["upcoming_events_count"] = data.get("upcoming_events_count") or 0
        return Artist(**data)
