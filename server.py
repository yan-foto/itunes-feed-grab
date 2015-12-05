import webapp2
import json
from grabber import Grabber


class RssGenerator(webapp2.RequestHandler):

    def get(self):
        try:
            # target = json.loads(self.request.body)["target"]
            target = self.request.GET['target']
            g = Grabber(target)
            self.response.headers[
                'Content-Type'] = 'application/rss+xml; charset=utf-8'
            self.response.write(g.grab_rss_feed())
        except ValueError:
            self.response.status = '400 malformed request body'
        except KeyError:
            self.response.status = '400 no target url specified'


app = webapp2.WSGIApplication([
    ('/generate', RssGenerator),
], debug=True)
