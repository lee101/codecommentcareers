from collections import Counter
import re
from collections import defaultdict
import urllib2
import logging
from urlparse import urljoin

import webapp2
from google.appengine.api import urlfetch
from google.appengine.api import images

from Models import *
import awgutils
from bs4 import BeautifulSoup
import fixtures
import cloudstorage as gcs



# TODO see http://www.tripadvisor.com/robots.txt
# Retry can help overcome transient urlfetch or GCS issues, such as timeouts.
my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)
# All requests to GCS using the GCS client within current GAE request and
# current thread will use this retry params as default. If a default is not
# set via this mechanism, the library's built-in default will be used.
# Any GCS client function can also be given a more specific retry params
# that overrides the default.
# Note: the built-in default is good enough for most cases. We override
# retry_params here only for demo purposes.
gcs.set_default_retry_params(my_default_retry_params)

IMG_BUCKET = '/commentcareers/'
WORD_GAMES_SWF_BUCKET = '/games.addictingwordgames.com/'


class Crawler(webapp2.RequestHandler):
    def create_callback(self, callback, rpc):
        def f():
            try:
                callback(rpc.get_result())
            except Exception, err:
                logging.error(Exception)
                logging.error(err)

        return f

    def getUrl(self, url, callback):
        try:
            rpc = urlfetch.create_rpc()
            rpc.callback = self.create_callback(callback, rpc)
            urlfetch.make_fetch_call(rpc, url)
        except Exception, err:
            logging.error(Exception)
            logging.error(err)

    def process(self, soup, url):
        '''
        called for each page
        '''
        raise NotImplementedError("Implement this method")

    seen = set()
    seen_domains = Counter()
    seen_pages_limit = 50000
    seen_domain_pages_limit = 30

    def get_host(self, url):
        return urllib2.splithost('//' + re.sub(r'(http://)|(https://)|(www.)', '', url))[0]

    def get_path(self, url):
        return urllib2.splithost('//' + re.sub(r'(http://)|(https://)|(www.)', '', url))[1]

    def get_domain(self, url):
        return urllib2.splithost(url[url.find('://') + 1:])


    def full_url_to(self, url, base_path):
        if not url:
            return ''
        return urljoin(base_path, url)

    def dfs(self, current_url):
        '''
        calls process for each page in the site
        '''
        try:
            result = urlfetch.fetch(current_url)

            if result.status_code == 200:
                soup = BeautifulSoup(result.content)

                if self.is_item(soup, current_url):
                    self.process(soup, current_url)

                self.seen.add(current_url)
                host = self.get_domain(current_url)
                if self.seen_domains[host] == 0:
                    # visit homepage of new urls we find.
                    self.seen_domains[host] += 1
                    self.dfs(urljoin(current_url, '/'))
                else:
                    self.seen_domains[host] += 1
                # find new links
                new_urls = []
                for link in soup.find_all('a'):
                    links_href = link.get('href')
                    if not links_href or links_href.startswith('#') or links_href.startswith('javascript:') or links_href.startswith(
                            'mailto:'):
                        continue

                    new_url = urljoin(current_url, links_href)

                    links_host = self.get_domain(new_url)

                    # todo improve performance with custom url exclusions
                    if new_url not in self.seen and len(self.seen) < self.seen_pages_limit and \
                                    self.seen_domains[links_host] < self.seen_domain_pages_limit:
                        new_urls.append(new_url)
                for url in new_urls:
                    self.dfs(url)
        except Exception, err:
            print err
            return


    def get(self):
        self.go()

    def go(self):
        self.dfs(self.site_url)
        self.post_process()


    def get_description(self, soup):
        description = ''
        try:
            description = soup.find('meta', attrs={'name': "og:description"}).get('content')
        except Exception, err:
            pass
        if not description:
            meta_description = soup.find('meta', attrs={'name': "description"})
            if meta_description:
                description = meta_description.get('content')
        return description

    def get_image(self, soup, url):
        image_url = ''
        try:
            image_url = soup.find('meta', attrs={'name': "og:image"}).get('content')
        except Exception, err:
            pass
        if not image_url:
            try:
                image_url = soup.find('img').get('src')
            except AttributeError, err:
                pass

        return self.full_url_to(image_url, url)


    def getTitle(self, soup):
        return soup.title.text

    def is_item(self, soup, current_url):
        return True

    def post_process(self):
        pass


job_posting_words = defaultdict(int, {
    'job': 0.5,
    'taleo': 1,
    'career': 1,
    'apply': 0.5,
    'team': 0.5,
    'join': 0.5,
    'work': 0.5,
    'company': 0.2,
    'technology': 0.2,
    'you': 0.2,
    'planet': 0.2,
    'email': 0.2,
    'visit': 0.2,
    'hi': 0.2,
    'best': 0.2,
    'awesome': 0.2,
    'bright': 0.2,
    'future': 0.2,
    'hundreds': 0.2,
    'interest': 0.2,
    'interested': 0.2,
    'global': 0.2,
    'open': 0.2,
    'contribute': 0.2,
    'millions': 0.2,
    'developer': 0.2,
    'seo': 0.2,
    'hacker': 0.2,
    'coder': 0.2,
})


class CodeCommentCrawler(Crawler):
    def is_homepage(self, url):
        return len(self.get_path(url)) <= 1

    def get_interesting_level_domain(self, url):
        host = self.get_host(url)
        return host.split('.')[0]

    def get_company_name(self, soup, url):

        title = soup.title.text
        host = self.get_interesting_level_domain(url)

        # collapse title find the hostname and map it back
        collapsed_word_indexes = []
        i = 0
        for letter in title:
            if re.match(r'\s', letter):
                i += 1
                continue
            collapsed_word_indexes.append(i)
            i += 1
        collapsed_title = re.sub(r'\s*', '', title)
        start_idx = collapsed_title.find(host)
        if start_idx == -1:
            return None
        end_idx = start_idx + len(host) - 1
        maped_start_idx = collapsed_word_indexes[start_idx]
        maped_end_idx = collapsed_word_indexes[end_idx]
        return title[maped_start_idx: maped_end_idx + 1].title()


    def get_job_posting(self, soup, url):
        comments = soup.find_all(text=lambda text: text.output_ready().startswith('<!--'))
        if not comments:
            comments = soup.find_all(text=lambda text: text.output_ready().startswith('#'))
        total_probability = 0
        comments_probabilitys = []
        for comment in comments:
            comments_probability = 0
            for word in re.split(r'[\s\.@]*', comment):
                comments_probability += job_posting_words[word.lower()]
            total_probability += comments_probability
            comments_probabilitys.append(comments_probability)
        if total_probability > 1:
            job_post_start_idx = 0
            job_post_end_idx = len(comments_probabilitys) - 1
            for i in xrange(len(comments_probabilitys)):
                if comments_probabilitys[i]:
                    job_post_start_idx = i
                    break
            for i in xrange(len(comments_probabilitys) - 1, -1, -1):
                if comments_probabilitys[i]:
                    job_post_end_idx = i
                    break
            code_comment = '\n'.join(comments[job_post_start_idx: job_post_end_idx + 1])
            if self.is_homepage(url):
                self.title = self.getTitle(soup)
                self.urltitle = awgutils.urlEncode(self.title)
                self.company_name = self.get_company_name(soup, url)
                self.company_description = self.get_description(soup)

            job_posting = JobPosting()
            job_posting.company_url = url.replace(self.get_path(url), '')
            job_posting.company_image_url = self.get_image(soup, url)
            job_posting.code_comment = code_comment
            job_posting.code_comment_url = url
            job_posting.tags = set(re.split(r'\s*', code_comment.lower())).intersection(fixtures.tag_words)
            return job_posting

    def __init__(self, **kwargs):
        super(CodeCommentCrawler, self).__init__(**kwargs)
        self.postings = []
        self.postings_tags = set([])

    def process(self, soup, url):
        posting = self.get_job_posting(soup, url)
        if posting is not None:
            posting.title = self.title
            posting.urltitle = self.urltitle
            posting.company_name = self.company_name
            posting.company_description = self.company_description
            new_tags = set(posting.tags).difference(self.postings_tags)
            if len(new_tags) >= 1:
                self.postings_tags.update(new_tags)
                self.postings.append(posting)

    def post_process(self):
        ndb.put_multi(self.postings)
        self.postings = []
        self.postings_tags = set([])


def getContentType(image):
    if image.format == images.JPEG:
        return 'image/jpeg'
    elif image.format == images.PNG:
        return 'image/png'
    elif image.format == images.BMP:
        return 'image/bmp'
    elif image.format == images.GIF:
        return 'image/gif'


def saveImage(url, title):
    '''
    saves image in cloud storage
    '''
    response = urlfetch.fetch(url)
    if response.status_code == 200:
        image = images.Image(response.content)
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        gcs_file = gcs.open(title,
                            'w',
                            content_type=getContentType(image),
                            options={'x-goog-acl': 'public-read'},
                            retry_params=write_retry_params)
        gcs_file.write(response.content)
        gcs_file.close()
        return image.width, image.height
    return (0, 0)


def saveUrl(url, title):
    '''
    saves object at url in cloud storage
    '''
    response = urlfetch.fetch(url)
    if response.status_code == 200:
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        if not response.headers['content-type']:
            logging.error('no content-type header returned')
            logging.error(response.headers)
        gcs_file = gcs.open(title,
                            'w',
                            content_type=response.headers['content-type'],
                            options={'x-goog-acl': 'public-read'},
                            retry_params=write_retry_params)
        gcs_file.write(response.content)
        gcs_file.close()





