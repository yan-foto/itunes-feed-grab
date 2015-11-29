from urlparse import urlparse
from urllib import urlencode
from urllib2 import Request, urlopen, HTTPError
from lxml import html, cssselect, etree


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

    # iTunes' XML DTD
    ITUNES_XML_DTD = 'http://www.itunes.com/dtds/podcast-1.0.dtd'

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

        # iTunes specific items
        etree.SubElement(channel, '{%s}image' % ns, href=meta['image'])
        itunes_author = etree.SubElement(channel, '{%s}author' % ns)
        itunes_author.text = meta['author']

        # Items
        for item in self._audio_items_from(content):
            item_el = etree.SubElement(channel, 'item')

            for key in ['title']:
                sub_item = etree.SubElement(item_el, key)
                sub_item.text = item[key]

            # 'link' and 'guid' both as URL
            for key in ['link', 'guid']:
                sub_item = etree.SubElement(item_el, key)
                sub_item.text = item['url']

            # iTunes specific tags
            itunes_author = etree.SubElement(item_el, '{%s}author' % ns)
            itunes_author.text = meta['author']

            # TODO: Figure out length :/
            enc = etree.SubElement(
                item_el,
                'enclosure',
                url=item['url'],
                type='audio/mpeg',
                length="0")

        return etree.tostring(
            root,
            xml_declaration=True,
            encoding='utf-8',
            pretty_print=True)

    def _as_html(self):
        """@return lxml.html object of object's URL"""
        return html.fromstring(self.raw_grab().read())

    def _audio_items_from(self, content):
        """@return an array of audio items from given podcast page (HTML content)"""
        result = []
        sel = cssselect.CSSSelector('[audio-preview-url]')

        for e in sel(content):
            result.append({
                'artist': e.get('preview-artist'),
                'album': e.get('preview-album'),
                'title': e.get('preview-title'),
                'url': e.get('audio-preview-url'),
                'duration': e.get('preview-duration')
            })

        return result

    def _meta_info_from(self, content):
        """Parses podcasts meta information out of given HTML content.
        @return dictionary containing title, author, description, and image"""
        result = {}
        # Title
        sel = cssselect.CSSSelector('.product-info .title h1 a')
        result["title"] = sel(content)[0].text

        # Author
        sel = cssselect.CSSSelector('.product-info .byline h2')
        result["author"] = sel(content)[0].text

        # Description
        sel = cssselect.CSSSelector('.product-info .product-review p')
        result["description"] = sel(content)[0].text

        # Image
        sel = cssselect.CSSSelector('.product .artwork img')
        result["image"] = sel(content)[0].get('src-swap')

        # URL (original URL provided to Grabber)
        result["url"] = self.url

        return result
