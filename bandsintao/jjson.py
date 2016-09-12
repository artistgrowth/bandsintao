# coding=utf-8
from __future__ import unicode_literals

import datetime
import decimal
import json
import logging
import re
import types

import dateutil.parser
import pytz
import six

logger = logging.getLogger(__name__)


def _get_iso_regex():
    """
    Creates a regex that handles a subset of the ISO 8601 format that we care about.

    Date objects should be recognized by the following:
    YYYY-MM-DD.

    Datetime objects should be recognized by the following pattern:

    YYYY-MM-DDTHH:MM:SS[.mmmmmm][+HH:MM]
    """

    def _valid_offsets():
        """
        Get the unique set of all the common timezone offsets
        """
        offsets = []
        for tz in pytz.common_timezones:
            offset = datetime.datetime.now(tz=pytz.timezone(tz)).strftime("%z")
            offsets.append("{}:{}".format(offset[:-2], offset[-2:]).replace("+", "\+"))
        offsets = set(offsets)
        return "|".join(offsets)

    _year_pattern = r"(?P<year>[0-9]{4})"
    _month_pattern = r"(?P<month>(0[1-9])|(1[0-2]))"
    _day_pattern = r"(?P<day>(0[1-9])|(1[0-9])|(2[0-9])|(3[0-1]))"
    _date_pattern = r"{year}-{month}-{day}".format(
        year=_year_pattern,
        month=_month_pattern,
        day=_day_pattern,
    )
    _minute_pattern = r"(?P<minute>[0-5][0-9])"
    _hour_pattern = r"(?P<hour>([0-1][0-9])|(2[0-3]))"
    _second_pattern = r"(?P<second>[0-5][0-9])"
    _microsecond_pattern = r"(?P<microsecond>\.[0-9]{1,6})?"
    _tz_pattern = r"(?P<tz>Z|({offsets}))?".format(offsets=_valid_offsets())
    _time_pattern = r"{hour}:{minute}:{second}{microsecond}{tz}".format(
        hour=_hour_pattern,
        minute=_minute_pattern,
        second=_second_pattern,
        microsecond=_microsecond_pattern,
        tz=_tz_pattern,
    )

    return re.compile(r"^{date}(T{time})?$".format(date=_date_pattern, time=_time_pattern))


_iso_8601_datetime_regex = _get_iso_regex()


def _custom_deserializer(decoded_json_object):
    """
    This is a hook to provide custom deserialization functionality to json
    :param decoded_json_object: An object that has already had the default deserialization performed on it
    :return:
    """
    if isinstance(decoded_json_object, list):
        pairs = enumerate(decoded_json_object)
    elif isinstance(decoded_json_object, dict):
        pairs = decoded_json_object.items()
    else:
        pairs = None

    result = []
    # Iterate through the decoded values and convert any custom types we find
    for key, value in pairs:
        if isinstance(value, types.StringTypes):
            # Attempt to convert string types that match a datetime patterns
            if _iso_8601_datetime_regex.match(value):
                length = len(value)
                try:
                    value = dateutil.parser.parse(value)
                except (ValueError, OverflowError):
                    pass
                else:
                    if length == 10:
                        # Convert it to just a date
                        value = value.date()

        elif isinstance(value, (dict, list)):
            # Recursively dive into the object and convert the values found
            value = _custom_deserializer(value)

        # Append our results for a final processing
        result.append((key, value))

    # Finally return the result of our work using with the same type that was originally deserialized
    if isinstance(decoded_json_object, list):
        # if the original value was a list then return a list of all the converted values
        final_result = [x[1] for x in result]
    elif isinstance(decoded_json_object, dict):
        # if the original value was a dict then return a list of all the converted values
        final_result = dict(result)
    else:
        final_result = None

    return final_result


class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        """
        Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        http://docs.python.org/library/datetime.html#datetime.datetime.isoformat
        [sep] -> string in ISO 8601 format, YYYY-MM-DDTHH:MM:SS[.mmmmmm][+HH:MM].

        sep is used to separate the year from the time, and defaults to 'T'.
        """
        if isinstance(o, datetime.datetime):
            result = o.isoformat()
        elif isinstance(o, datetime.date):
            result = o.strftime("%Y-%m-%d")
        elif isinstance(o, (decimal.Decimal,)):
            # Objects to be converted to unicode prior to json serialization
            result = six.text_type(o)
        else:
            try:
                iterable = iter(o)
            except TypeError:
                result = super(JsonEncoder, self).default(o)
            else:
                result = list(iterable)

        return result


def dumps(obj, sort_keys=False, indent=None, separators=None):
    """Serialize ``obj`` to a JSON formatted ``str``."""
    return json.dumps(obj, sort_keys=sort_keys, indent=indent, separators=separators, cls=JsonEncoder)


def loads(s):
    """Deserialize ``s`` (a ``str`` or ``unicode`` instance containing a JSON document) to a Python object."""
    return json.loads(s, object_hook=_custom_deserializer)
