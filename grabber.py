from urlparse import urlparse
from urllib import urlencode
from urllib2 import Request, urlopen, HTTPError


class Grabber:
    """Given an iTunes URL, grabber provides various methods to fetch contents
    of that URL as if it was opened in iTunes.
    """

    # Request headers to act as-if we were iTunes
    HEADERS = {
        'X-Apple-Tz': 3600,
        'User-Agent': 'iTunes/9.2.1 (Macintosh; Intel Mac OS X 10.5.8) AppleWebKit/533.16'
    }

    # Valid addresses
    WHITE_ADDRS = [
        'itunes.apple.com'
    ]

    # Podcast hosts for web objects
    POD_HOST = 'https://itunes.apple.com/WebObjects/DZR.woa/wa/viewPodcast'

    def __init__(self, url):
        """Initializes.
        @param url desired iTunes URL
        """
        self.url = url

    def raw_grab(self):
        """Returns the content of given URL as if it was opened in iTunes.
        @return response object if grabbing succeeds
        """
        url = self.url

        # Check if it is an itunes URL
        urlInfo = urlparse(url)
        if urlInfo.netloc not in Grabber.WHITE_ADDRS:
            # TODO: raise error
            return False

        # Follow the redirects to get to actual page with links
        succeeded = False
        while not succeeded:
            try:
                request = Request(url, None, Grabber.HEADERS)
                response = urlopen(request)

                # If we are pointed to a new page
                wo_path = response.info().getheader("x-apple-translated-wo-url")
                if wo_path is not None:
                    wo_query = dict(map(lambda item: item.split(
                        '='), urlparse(wo_path).query.split('&')))
                    url = "{}?{}".format(Grabber.POD_HOST, urlencode(wo_query))
                    continue

                return response
            except HTTPError as e:
                # TODO: raise error
                pass
