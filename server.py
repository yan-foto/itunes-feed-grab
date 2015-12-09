'''
iTunes Feed Grabber: transforms iTunes podcasts to RSS XML feeds.

Copyright (C) 2015 Yan Foto

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import webapp2
import json
from grabber import Grabber
from grabexceptions import InvalidTarget
from google.appengine.api import urlfetch


class RssGenerator(webapp2.RequestHandler):

    def get(self):
        try:
            # target = json.loads(self.request.body)["target"]
            target = self.request.GET['target']

            # if target is a number its an ID!
            try:
                target = long(target)
            except ValueError:
                pass

            # This is required so that fetch requests doesn't time out!
            urlfetch.set_default_fetch_deadline(60)
            g = Grabber(target)
            self.response.headers[
                'Content-Type'] = 'application/rss+xml; charset=utf-8'
            self.response.write(g.grab_rss_feed())
        except ValueError:
            self.response.status = '400 malformed request body'
        except KeyError:
            self.response.status = '400 no target url specified'
        except InvalidTarget:
            self.response.status = '400 Could not find ID'


app = webapp2.WSGIApplication([
    ('/generate', RssGenerator),
], debug=True)
