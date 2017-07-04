#!env/bin/python
"""Library for interacting with Gravity Forms Web API

https://bitbucket.org/ArlingtonCounty/pygfapi/

ADAPTED BY BLUESHIFT BECAUSE THE ABOVE VERSION DOESNT SEEM TO QUITE WORK WITH OUR VERSION OF GRAVITYFORMS
^ That's why it is in this project, and not the version from the repository.
"""

import datetime
import time
import base64
import urllib
import json
import requests
import hmac
import re
import logging
from hashlib import sha1


class Client(object):
    """
    Main client class.
    """

    def __init__(self, api_url, public_key, private_key, auth=None):
        """
        Constructs a :class:`Client <Client>`.

        :param api_url: Web API base URL, e.g.
                        https://www.example.com/gravityformsapi/
        :type url_base: str

        :param public_key: Web API public key.
        :type url_base: str

        :param private_key: Web API private key.
        :type url_base: str

        :param auth: (optional) Auth tuple or callable to enable HTTP Auth.
        :type auth: tuple

        :return: :class:`Client <Client>` object
        :rtype: pygfapi.Client
        """
        self.log = logging.getLogger(
            "{0.__module__}.{0.__name__}".format(self.__class__)
        )
        self.api_url = api_url
        self.public_key = public_key
        self.private_key = private_key
        self.auth = auth
        self.retry_limit = 6
        self.retry_seconds = 10
        self.page_size = 200

    def __repr__(self):
        return "{0.__module__}.{0.__name__}('{1}', '{2}', '{3}')".format(
            self.__class__,
            self.api_url,
            self.public_key,
            self.private_key
        )

    def convert_entry_args(self, entry_args=None):
        """
        Convert entry retrieval query arguments.

        The GF Web API uses pseudo-nested query args. See https://www.\
        gravityhelp.com/documentation/article/web-api/#querystring-\
        parameters-for-retrieval-routes

        :param entry_args: Entry retrieval arguments.
        :type entry_args: dict

        :return: Query args.
        :rtype: dict
        """
        if not entry_args:
            entry_args = {}
        query_args = {}
        search_args = {}
        # Paging
        if "page_size" in entry_args:
            query_args["paging[page_size]"] = entry_args["page_size"]
        else:
            query_args["paging[page_size]"] = self.page_size
        if "offset" in entry_args:
            query_args["paging[offset]"] = entry_args["offset"]
        else:
            query_args["paging[offset]"] = 0
        # Sorting
        if "sorting_key" in entry_args:
            query_args["sorting[key]"] = entry_args["sorting_key"]
        if "sorting_direction" in entry_args:
            query_args["sorting[direction]"] = entry_args["sorting_direction"]
        # Search criteria
        if "start_date" in entry_args:
            if isinstance(entry_args["start_date"], datetime.date):
                search_args["start_date"] = entry_args["start_date"].isoformat()
            else:
                search_args["start_date"] = entry_args["start_date"]
        if "end_date" in entry_args:
            if isinstance(entry_args["end_date"], datetime.date):
                search_args["end_date"] = entry_args["end_date"].isoformat()
            else:
                search_args["end_date"] = entry_args["end_date"]
        if "status" in entry_args:
            search_args["status"] = entry_args["status"]
        # Field filters
        if "field_filters" in entry_args:
            search_args["field_filters"] = entry_args["field_filters"]
        query_args["search"] = json.dumps(search_args)
        return query_args

    def build_url(self, method, route, query_args=None, expires=None):
        """
        Build signed URL.

        See https://www.gravityhelp.com/documentation/article/web-\
        api/#authentication-for-external-applications

        :param method: GET, POST, PUT, or DELETE.
        :type method: str

        :param route: Route, e.g. "forms/1/".
        :type route: str

        :param query_args: Additional query args appended to URL.
        :type query_args: dict

        :return: Signed URL.
        :rtype: str
        """
        if not expires:
            expires = int(time.time()) + 3600  # seconds

        # BLUESHIFT CHANGE: Strip trailing slash from 'route' to prevent 401 response from Gravity Forms
        string_to_sign = "{0}:{1}:{2}:{3}".format(
            self.public_key,
            method,
            route.strip("/"),
            expires
        )

        sig = hmac.new(self.private_key, string_to_sign, sha1)
        sig_b64 = base64.b64encode(sig.digest())
        required_args = {
            "api_key": self.public_key,
            "signature": sig_b64,
            "expires": expires,
        }
        # Creating URL here rather than passing a dict to requests avoids
        # double-encoding percent signs.
        if query_args:
            query = urllib.urlencode(
                dict(query_args.items() + required_args.items())
            )
        else:
            query = urllib.urlencode(required_args)
        return "{}{}?{}".format(self.api_url, route, query)

    def request(self, method, route, query_args=None, data=None):
        """
        Send request.

        :param method: GET, POST, PUT, or DELETE.
        :type method: str

        :param route: Route, e.g. "forms/1/".
        :type route: str

        :param data: Request body. Will be JSON-encoded automatically.
        :type data: dict

        :param query_args: Additional query args appended to URL.
        :type query_args: dict

        :return: API response (decoded from JSON).
        """
        url = self.build_url(method, route, query_args)

        self.log.debug("Built URL: %s", url)
        try:
            retry_count = 0
            while retry_count <= self.retry_limit:
                r = requests.request(
                    method,
                    url,
                    params=query_args,
                    json=data,
                    auth=self.auth
                )
                r.raise_for_status()
                gf_status = r.json()["status"]
                gf_response = r.json()["response"]
                if gf_status == 202:
                    retry_count += 1
                    time.sleep(self.retry_seconds)
                elif gf_status > 202:
                    raise requests.exceptions.HTTPError("{} {}".format(
                        gf_status,
                        "GF Web API error"
                    ))
                else:
                    return gf_response
            if retry_count > self.retry_limit:
                raise requests.exceptions.RetryError("Retry limit exceeded")
        except (KeyError, ValueError):
            raise requests.exceptions.HTTPError(
                "Unexpected response from GF Web API"
            )

    def get(self, route, query_args=None):
        """
        Generic GET request.

        :param route: Relative URL route.
        :type route: str

        :param query_args: Additional query args (optional).
        :type query_args: dict
        """
        return self.request("GET", route, query_args)

    def get_form(self, form_id):
        """
        Return a form.

        :param form_id: Form ID.
        :type form_id: int
        """
        route = "forms/{}".format(form_id)
        return self.get(route)

    def get_forms(self, form_ids=None):
        """
        Return active forms.

        :param form_ids: Form IDs (optional).
        :type form_ids: list
        """
        route = "forms/"
        if form_ids:
            route += ";".join(str(i) for i in form_ids)
        return self.get(route)

    def get_entry(self, entry_id):
        """
        Return a form entry.

        :param entry_id: Entry ID.
        :type entry_id: int
        """
        route = "entries/{}".format(entry_id)
        return self.get(route)

    def get_entries(self, entry_args=None):
        """
        Return entries across all forms.

        :param entry_args: Additional query args (optional).
        :type entry_args: dict
        """
        return self.get_form_entries(form_id=None, entry_args=entry_args)

    def get_form_entries(self, form_id=None, entry_args=None):
        """
        Return entries for one or all forms.

        :param form_id: Form ID (optional).
        :type form_id: int

        :param entry_args: Additional query args (optional).
        :type entry_args: dict
        """
        if form_id:
            route = "forms/{}/entries".format(form_id)
        else:
            route = "forms/entries"

        query_args = self.convert_entry_args(entry_args)
        logging.debug("query_args: %s", query_args)
        entries = []
        while True:
            response = self.get(route, query_args)
            entries.extend(response[u"entries"])
            total_entries = int(response[u"total_count"])
            if len(entries) < total_entries:
                query_args["paging[offset]"] += query_args["paging[page_size]"]
                logging.debug("query_args: %s", query_args)
            else:
                break
        return entries

    def get_unread_entries(self, form_id=None):
        """
        Return active unread entries for one or all forms.

        :param form_id: Form ID (optional).
        :type form_id: int
        """
        entry_args = {
            "status": "active",
            "field_filters": {
                "mode": "all",
                0: {
                    "key": "is_read",
                    "operator": "is",
                    "value": 0,
                }
            }
        }
        return self.get_form_entries(form_id, entry_args)

    def get_form_results(self, form_id):
        """
        Return aggregate results for each of the fields in the given form.

        :param form_id: Form ID.
        :type form_id: int
        """
        route = "forms/{}/results".format(form_id)
        return self.get(route)

    def get_entry_fields(self, entry_ids, field_ids, entry_args=None):
        """
        Return fields/properties for one or more entries.

        :param entry_ids: Entry IDs.
        :type entry_ids: list

        :param field_ids: Field IDs.
        :type field_ids: list

        :param entry_args: Additional query args (optional).
        :type entry_args: dict
        """
        route = "entries/{0}/fields/{1}".format(
            ";".join(str(i) for i in entry_ids),
            ";".join(str(i) for i in field_ids)
        )
        query_args = self.convert_entry_args(entry_args)
        return self.get(route, query_args)

    def delete(self, route, query_args=None):
        """
        Generic DELETE request.

        :param route: Relative URL route.
        :type route: str

        :param query_args: Additional query args (optional).
        :type query_args: dict
        """
        return self.request("DELETE", route, query_args)

    def delete_form(self, form_id):
        """
        Delete a form.

        :param form_id: Form ID.
        :type form_id: int
        """
        route = "forms/{}".format(form_id)
        return self.delete(route)

    def delete_forms(self, form_ids=None):
        """
        Delete forms.

        :param form_ids: Form IDs.
        :type form_ids: list
        """
        route = "forms/"
        if form_ids:
            route += ";".join(str(i) for i in form_ids)
        return self.delete(route)

    def delete_entry(self, entry_id):
        """
        Delete an entry.

        :param entry_id: Entry ID.
        :type entry_id: int
        """
        route = "entries/{}".format(entry_id)
        return self.delete(route)

    def delete_entries(self, entry_ids):
        """
        Delete entries.

        :param entry_ids: Entry IDs.
        :type entry_ids: list
        """
        route = "entries/"
        if entry_ids:
            route += ";".join(str(i) for i in entry_ids)
        return self.delete(route)

    def put(self, route, query_args=None, body=None):
        """
        Generic PUT request.

        :param route: Relative URL route.
        :type route: str

        :param query_args: Additional query args (optional).
        :type query_args: dict

        :param body: Body (optional).
        :type body: any type that can be encoded by json.encode().
        """
        return self.request("PUT", route, query_args, body)

    def put_entry(self, entry, entry_id=None):
        """
        Update an entry.

        :param entry: Entry.
        :type entry: dict

        :param entry_id: Entry ID (overrides ID in Entry body).
        :type entry_id: int
        """
        if not entry_id:
            entry_id = entry[u"id"]
        route = "entries/{}".format(entry_id)
        return self.put(route, body=entry)

    def put_entries(self, entries):
        """
        Update entries.

        :param entries: Entries.
        :type entrires: list
        """
        route = "entries"
        return self.put(route, body=entries)

    def put_form(self, form, form_id=None):
        """
        Update a form.

        :param form: Form.
        :type form: dict

        :param form_id: Form ID (overrides ID in Form body).
        :type form_id: int
        """
        if not form_id:
            form_id = form[u"id"]
        route = "forms/{}".format(form_id)
        return self.put(route, body=form)

    def put_forms(self, forms):
        """
        Update forms.

        :param forms: Forms.
        :type forms: list
        """
        route = "forms"
        return self.put(route, body=forms)

    def post(self, route, query_args=None, body=None):
        """
        Generic POST request.

        :param route: Relative URL route.
        :type route: str

        :param query_args: Additional query args (optional).
        :type query_args: dict

        :param body: Body (optional).
        :type body: any type that can be encoded by json.encode().
        """
        return self.request("POST", route, query_args, body)

    def post_form(self, form):
        """
        Create a form.

        :param form: Form.
        :type form: dict
        """
        route = "forms"
        return self.post(route, body=form)

    def post_forms(self, forms):
        """
        Create forms.

        :param forms: Forms.
        :type forms: list
        """
        route = "forms"
        return self.post(route, body=forms)

    def post_form_submission(self, form_id, submission):
        """
        Create a submission.

        :param form_id: Form ID.
        :type form_id: int

        :param submission: Submission.
        :type submission: dict
        """
        route = "forms/{}/submissions".format(form_id)
        return self.post(route, body=submission)

    def post_form_submissions(self, form_id, submissions):
        """
        Create submissions.

        :param form_id: Form ID.
        :type form_id: int

        :param submissions: Submissions.
        :type submissions: list
        """
        route = "forms/{}/submission".format(form_id)
        return self.post(route, body=submissions)

    def post_entry(self, entry):
        """
        Create an entry.

        :param entry: Entry.
        :type entry: dict
        """
        route = "entries"
        return self.post(route, body=entry)

    def post_entries(self, entries):
        """
        Create entries.

        :param entries: Entries.
        :type entries: list
        """
        route = "entries"
        return self.post(route, body=entries)

    def post_form_entry(self, form_id, entry):
        """
        Create an entry.

        :param form_id: Form ID.
        :type form_id: int

        :param entry: Entry.
        :type entry: dict
        """
        route = "entries"
        route = "forms/{}/entries".format(form_id)
        return self.post(route, body=entry)

    def post_form_entries(self, form_id, entries):
        """
        Create entries.

        :param form_id: Form ID.
        :type form_id: int

        :param entries: Entries.
        :type entries: list
        """
        route = "forms/{}/entries".format(form_id)
        return self.post(route, body=entries)
