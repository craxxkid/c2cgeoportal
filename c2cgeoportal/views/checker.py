# -*- coding: utf-8 -*-

# Copyright (c) 2011-2015, Camptocamp SA
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.


from pyramid.view import view_config
from pyramid.response import Response

import httplib
from httplib2 import Http
from json import dumps, loads
import logging
from time import sleep

from c2cgeoportal.lib import add_url_params

log = logging.getLogger(__name__)


class Checker(object):  # pragma: no cover

    status_int = httplib.OK
    status = httplib.responses[httplib.OK]

    def __init__(self, request):
        self.request = request
        self.settings = self.request.registry.settings["checker"]

    def set_status(self, code, text):
        if int(code) >= self.status_int:
            self.status_int = int(code)
            self.status = text

    def make_response(self, msg):
        return Response(
            body=msg, status="%i %s" % (self.status_int, self.status), cache_control="no-cache"
        )

    def testurl(self, url):
        h = Http()

        log.info("Checker for url: %s" % url)

        url = url.replace(self.request.environ.get("SERVER_NAME"), "localhost")
        headers = {
            "Host": self.request.environ.get("HTTP_HOST"),
            "Cache-Control": "no-cache",
        }

        resp, content = h.request(url, headers=headers)

        if resp.status != httplib.OK:
            print(resp.items())
            self.set_status(resp.status, resp.reason)
            return url + "<br/>" + content

        return "OK"

    @view_config(route_name="checker_main")
    def main(self):
        _url = self.request.route_url("home")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_viewer")
    def viewer(self):
        _url = self.request.route_url("viewer")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_edit")
    def edit(self):
        _url = self.request.route_url("edit")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_edit_js")
    def edit_js(self):
        _url = self.request.route_url("edit.js")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_api")
    def api_js(self):
        _url = self.request.route_url("apijs")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_xapi")
    def xapi_js(self):
        _url = self.request.route_url("xapijs")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_printcapabilities")
    def printcapabilities(self):
        _url = self.request.route_url("printproxy_info")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_print3capabilities")
    def print3capabilities(self):
        _url = self.request.route_url("printproxy_capabilities")
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_pdf")
    def pdf(self):
        return self.make_response(self._pdf())

    def _pdf(self):
        body = {
            "comment": "Foobar",
            "title": "Bouchon",
            "units": "m",
            "srs": "EPSG:%i" % self.request.registry.settings["srid"],
            "dpi": 254,
            "layers": [],
            "layout": self.settings["print_template"],
            "pages": [{
                "center": [self.settings["print_center_lon"], self.settings["print_center_lat"]],
                "col0": "",
                "rotation": 0,
                "scale": self.settings["print_scale"],
                "table": {
                    "columns": ["col0"],
                    "data": [{
                        "col0": ""
                    }]
                }
            }]
        }
        body = dumps(body)

        _url = add_url_params(self.request.route_url("printproxy_create"), {
            "url": self.request.route_url("printproxy"),
        })
        h = Http()

        log.info("Checker for printproxy request (create): %s" % _url)
        _url = _url.replace(self.request.environ.get("SERVER_NAME"), "localhost")
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Host": self.request.environ.get("HTTP_HOST")
        }
        resp, content = h.request(_url, "POST", headers=headers, body=body)

        if resp.status != httplib.OK:
            self.set_status(resp.status, resp.reason)
            return "Failed creating PDF: " + content

        log.info("Checker for printproxy pdf (retrieve): %s" % _url)
        json = loads(content)
        _url = json["getURL"].replace(self.request.environ.get("SERVER_NAME"), "localhost")
        headers = {"Host": self.request.environ.get("HTTP_HOST")}
        resp, content = h.request(_url, headers=headers)

        if resp.status != httplib.OK:
            self.set_status(resp.status, resp.reason)
            return "Failed retrieving PDF: " + content

        return "OK"

    @view_config(route_name="checker_pdf3")
    def pdf3(self):
        return self.make_response(self._pdf3())

    def _pdf3(self):
        body = dumps(self.settings["print_spec"])

        _url = self.request.route_url("printproxy_report_create", format="pdf")
        h = Http()

        log.info("Checker for printproxy request (create): %s" % _url)
        _url = _url.replace(self.request.environ.get("SERVER_NAME"), "localhost")
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Host": self.request.environ.get("HTTP_HOST")
        }
        resp, content = h.request(_url, "POST", headers=headers, body=body)

        if resp.status != httplib.OK:
            self.set_status(resp.status, resp.reason)
            return "Failed creating the print job: " + content

        job = loads(content)
        _url = self.request.route_url("printproxy_status", ref=job["ref"])
        log.info("Checker for printproxy pdf status: %s" % _url)
        headers = {"Host": self.request.environ.get("HTTP_HOST")}
        done = False
        while not done:
            sleep(1)
            resp, content = h.request(_url, headers=headers)
            if resp.status != httplib.OK:
                self.set_status(resp.status, resp.reason)
                return "Failed get the status: " + content

            status = loads(content)
            print status
            if "error" in status:
                return "Faild to do the printing: %s" % status["error"]
            done = status["done"]

        _url = self.request.route_url("printproxy_report_get", ref=job["ref"])
        log.info("Checker for printproxy pdf retrieve: %s" % _url)
        resp, content = h.request(_url, headers=headers)

        if resp.status != httplib.OK:
            self.set_status(resp.status, resp.reason)
            return "Failed to get the PDF: " + content

        return "OK"

    @view_config(route_name="checker_fts")
    def fts(self):
        return self.make_response(self._fts())

    def _fts(self):
        _url = add_url_params(self.request.route_url("fulltextsearch"), {
            "query": self.settings["fulltextsearch"],
            "limit": "1",
        })
        h = Http()

        log.info("Checker for fulltextsearch: %s" % _url)
        _url = _url.replace(self.request.environ.get("SERVER_NAME"), "localhost")
        headers = {"host": self.request.environ.get("HTTP_HOST")}

        resp, content = h.request(_url, headers=headers)

        if resp.status != httplib.OK:
            self.set_status(resp.status, resp.reason)
            return content

        result = loads(content)

        if len(result["features"]) == 0:
            self.set_status(httplib.BAD_REQUEST, httplib.responses[httplib.BAD_REQUEST])
            return "No result"

        return "OK"

    @view_config(route_name="checker_wmscapabilities")
    def wmscapabilities(self):
        _url = add_url_params(self.request.route_url("mapserverproxy"), {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetCapabilities",
        })
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_wfscapabilities")
    def wfscapabilities(self):
        _url = add_url_params(self.request.route_url("mapserverproxy"), {
            "SERVICE": "WFS",
            "VERSION": "1.1.0",
            "REQUEST": "GetCapabilities",
        })
        return self.make_response(self.testurl(_url))

    @view_config(route_name="checker_theme_errors")
    def themes_errors(self):
        from c2cgeoportal.models import DBSession, Interface

        settings = self.settings["themes"]

        _url = self.request.route_url("themes")
        h = Http()
        default_params = settings.get("default", {}).get("params", {})
        for interface, in DBSession.query(Interface.name).all():
            params = {}
            params.update(default_params)
            params.update(settings.get(interface, {}).get("params", {}))
            params["interface"] = interface
            interface_url = add_url_params(_url, params)

            log.info("Checker for theme: %s" % interface_url)
            interface_url = interface_url.replace(
                self.request.environ.get("SERVER_NAME"),
                "localhost"
            )
            headers = {"host": self.request.environ.get("HTTP_HOST")}

            resp, content = h.request(interface_url, headers=headers)

            if resp.status != httplib.OK:
                self.set_status(resp.status, resp.reason)
                return self.make_response(content)

            result = loads(content)

            if len(result["errors"]) != 0:
                self.set_status(500, "Theme with error")

                return self.make_response("Theme with error for interface '%s'\n%s" % (
                    Interface.name,
                    "\n".join(result["errors"])
                ))

        return self.make_response("OK")

    @view_config(route_name="checker_lang_files")
    def checker_lang_files(self):
        available_locale_names = self.request.registry.settings["available_locale_names"]

        if self.request.registry.settings["default_locale_name"] not in available_locale_names:
            self.set_status(500, "default_locale_name not in available_locale_names")

            return self.make_response((
                "Your `default_locale_names` '%s' is not in your "
                "`available_locale_names` '%s'" % (
                    self.request.registry.settings["default_locale_name"],
                    ", ".join(available_locale_names)
                )
            ))

        result = []
        for _type in self.settings["lang_files"]:
            for lang in available_locale_names:
                if _type == "cgxp":
                    _url = self.request.static_url(
                        "{package}:static/build/lang-{lang}.js".format(
                            package=self.request.registry.settings["package"], lang=lang
                        )
                    )
                elif _type == "cgxp-api":
                    _url = self.request.static_url(
                        "{package}:static/build/api-lang-{lang}.js".format(
                            package=self.request.registry.settings["package"], lang=lang
                        )
                    )
                elif _type == "ngeo":
                    _url = self.request.static_url(
                        "{package}:static-ngeo/build/locale/{lang}/{package}.json".format(
                            package=self.request.registry.settings["package"], lang=lang
                        )
                    )
                else:
                    self.set_status(500, "Unknown lang_files")
                    return self.make_response((
                        "Your language type value '%s' isn't valid, "
                        "available values [cgxp, cgxp-api, ngeo]" % (
                            _type
                        )
                    ))
                result.append(self.testurl(_url))
        return self.make_response(
            "OK" if len(result) == 0 else "\n\n".join(result)
        )
