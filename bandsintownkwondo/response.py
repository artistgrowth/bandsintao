from napi import custom_json


class Response(object):
    response = None

    def __init__(self, response, *args, **kwargs):
        self.response = custom_json.loads(response)

    def __unicode__(self):
        return unicode(self.__str__())

    def __str__(self):
        return custom_json.dumps(self.response, indent=4)
