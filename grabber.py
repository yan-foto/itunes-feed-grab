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

from urlparse import urlparse
from urllib import urlencode
from urllib2 import Request, urlopen, HTTPError
from lxml import html, etree
from time import mktime
from datetime import datetime
from email.Utils import formatdate
from grabexceptions import *
import re

__author__ = "Yan Foto"
__version__ = "0.3.0"


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
    # We used to use 'https://itunes.apple.com/WebObjects/DZR.woa/wa/viewPodcast'
    # URL, but it didn't support some of older podcasts ('Not available in market'
    # error), so we use this one and instead look for possible redirects
    POD_HOST = 'https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewPodcast'

    # Host for courses as they are not enlisted as podcasts and trying to fetch
    # them as podcasts returns the usual and misleading 'Not available ...' error
    COURSE_HOST = 'https://itunes.apple.com/course'

    # iTunes' XML DTD
    ITUNES_XML_DTD = 'http://www.itunes.com/dtds/podcast-1.0.dtd'

    def __init__(self, url_or_id, course = False):
        """Initializes.
        @param url_or_id: URL or ID of iTunes podcast
        """
        if isinstance(url_or_id, (int, long)):
            self.id = url_or_id
        elif isinstance(url_or_id, (str, unicode)):
            id = re.search('id=?(\d+)', url_or_id)
            if id is None:
                raise InvalidTarget("Couldn't find ID of requested item")
            self.id = id.group(1) if id else query['id']
        else:
            raise InvalidTarget(
                "Target must be an ID (number) or string (URL)! (given: {})".format(
                    type(url_or_id)))

        self.course = course
        if course:
            self.url = "{}/id{}".format(Grabber.COURSE_HOST, self.id)
        else:
            self.url = "{}?{}".format(Grabber.POD_HOST, urlencode({'id': self.id}))

    def raw_grab(self):
        """Returns the content of given URL as if it was opened in iTunes.
        @return response object if grabbing succeeds
        """
        # Check if it is an itunes URL
        urlInfo = urlparse(self.url)
        if urlInfo.netloc not in Grabber.WHITE_ADDRS:
            # TODO: raise error
            return False

        # Follow the redirects to get to actual page with links
        finished = False
        while not finished:
            try:
                request = Request(self.url, None, Grabber.HEADERS)
                response = urlopen(request)
                content = response.read()
                response.close()
                redirect_url = self._redirect_url(content)
                if redirect_url is None:
                    finished = True
                    return content
                else:
                    self.url = redirect_url
            except HTTPError as e:
                # TODO: raise error
                pass

    def grab_audio_items(self):
        """@return an array of all audio items w/ artist, album, title, and url info"""
        return self._audio_items_from(self._as_html())

    def grab_meta_info(self):
        """@return dictionary of meta information"""
        return self._meta_info_from(self._as_html())

    def grab_rss_feed(self):
        """Creates an RSS 2.0 XML feed from the object's URL.
        @return an RSS string"""
        content = self._as_html()
        ns = Grabber.ITUNES_XML_DTD

        root = etree.Element(
            'rss',
            version='2.0',
            nsmap={'itunes': ns})

        channel = etree.SubElement(root, "channel")

        # Podcast info
        meta = self._meta_info_from(content)
        for key in ['title', 'description']:
            item = etree.SubElement(channel, key)
            item.text = meta[key]

        image = etree.SubElement(channel, 'image')
        image_url = etree.SubElement(image, 'url')
        image_url.text = meta['image']
        image_title = etree.SubElement(image, 'title')
        image_title.text = meta['title']

        for linkable in [image, channel]:
            linkable_link = etree.SubElement(linkable, 'link')
            linkable_link.text = self.url

        for date in ['pubDate', 'lastBuildDate']:
            date_field = etree.SubElement(channel, date)
            date_field.text = formatdate(mktime(datetime.now().timetuple()))

        # iTunes specific items
        etree.SubElement(channel, '{%s}image' % ns, href=meta['image'])
        itunes_author = etree.SubElement(channel, '{%s}author' % ns)
        itunes_author.text = meta['author']

        # Items
        for item in self._audio_items_from(content):
            item_el = etree.SubElement(channel, 'item')

            # Title
            sub_item = etree.SubElement(item_el, 'title')
            sub_item.text = item['name']

            # Description
            sub_item = etree.SubElement(item_el, 'description')
            sub_item.text = etree.CDATA(item['description'])

            # 'link' and 'guid' both as URL
            for key in ['link', 'guid']:
                sub_item = etree.SubElement(item_el, key)
                sub_item.text = item['url']

            # Publication date
            # TODO: this looks really messy!
            # If no release-date is given (e.g. courses) use now!
            if 'release-date' in item:
                dt = datetime.strptime(item['release-date'], '%Y/%m/%d')
            else:
                dt = datetime.now()
            sub_item = etree.SubElement(item_el, 'pubDate')
            sub_item.text = formatdate(mktime(dt.timetuple()))

            # iTunes specific tags
            itunes_author = etree.SubElement(item_el, '{%s}author' % ns)
            itunes_author.text = meta['author']

            # If duration is provided
            try:
                # Duration is provided in miliseconds
                duration = int(item['time']) / 1000
                m, s = divmod(duration, 60)
                h, m = divmod(m, 60)
                itunes_duration = etree.SubElement(
                    item_el, '{%s}duration' % ns)
                if h > 0:
                    itunes_duration.text = '{:02d}:{:02d}:{:02d}'.format(
                        h, m, s)
                else:
                    itunes_duration.text = '{:02d}:{:02d}'.format(m, s)
            except ValueError:
                # No duration provided
                pass

            # Enclosure: url must have http scheme and not https!
            # TODO: Figure out length :/
            url = re.sub(r'^https://', 'http://', item['url'])
            enc = etree.SubElement(
                item_el,
                'enclosure',
                url=url,
                type='audio/mpeg',
                length=item['size'])

        return etree.tostring(
            root,
            xml_declaration=True,
            encoding='utf-8',
            pretty_print=True)

    def _redirect_url(self, response):
        """Checks if server response denotes a redirection.
        @param response: response from server in string
        @return redirect URL or None if response is already valid
        """
        try:
            root = etree.fromstring(response)
            candidates = root.xpath(
                './/key[text()="url"]/following-sibling::string')

            if len(candidates) > 0:
                return candidates[0].text

        except etree.XMLSyntaxError:
            # Response is HTML and not XML: we're good to parse further
            pass

    def _as_html(self):
        """@return lxml.html object of object's URL"""
        return html.fromstring(self.raw_grab())

    def _audio_items_from(self, content):
        """@return an array of audio items from given podcast page (HTML content)"""
        result = []

        rows = content.xpath(
            "//table[contains(@class, 'tracklist-table')]/tbody//tr")
        if self.course:
            columns = 'index,name,description,time,price'
        else:
            columns = 'index,name,time,release-date,description,popularity,price'
        columns = columns.split(',')
        for e in rows:
            track = {}

            for i in range(0, len(columns)):
                col = columns[i]
                track[col] = e.find('.//td[%d]' % (i + 1)).get('sort-value')
            audio_url = e.get('audio-preview-url')
            if audio_url is None:
                # TODO: append also video links!
                continue

            track['url'] = audio_url

            # Fetch size in octets using a HEAD request
            request = Request(audio_url, None, Grabber.HEADERS)
            request.get_method = lambda: 'HEAD'
            response = urlopen(request)
            track['size'] = response.headers['content-length']

            result.append(track)

        return result

    def _meta_info_from(self, content):
        """Parses podcasts meta information out of given HTML content.
        @return dictionary containing title, author, description, and image"""
        result = {}

        # Title and Author
        result["title"] = content.find(
            ".//button[@podcast-name]").get('podcast-name')
        result["author"] = content.find(
            ".//button[@artist-name]").get('artist-name')

        # Description
        # TODO: this is not working for courses
        product_info = content.find(".//div[@class='product-info']")
        description = product_info.xpath(
            ".//div[contains(@class, 'product-review')]/p")
        result["description"] = description[0].text if description else ''

        # Image
        image = content.find(".//div[@class='artwork']/img")
        result["image"] = image.get('src-swap')

        # URL (original URL provided to Grabber)
        result["url"] = self.url

        return result
