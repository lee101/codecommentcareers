import unittest

from google.appengine.ext import testbed

from Models import JobPosting
from bs4 import BeautifulSoup
from crawlers.crawlers import CodeCommentCrawler, Crawler


class CrawlerTests(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_urlfetch_stub()
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

    def test_crawler(self):
        crawler = CodeCommentCrawler()
        crawler.seen_pages_limit = 20
        crawler.site_url = 'http://localhost:5000'
        crawler.go()

    def test_crawler_get_image(self):
        url = 'http://www.wordsmashing.com'

        crawler = Crawler()
        expected_image_url = 'http://img.img/img'
        soup = BeautifulSoup('<html><head><meta name="og:image" content="' + expected_image_url + '"></head></html>')
        image = crawler.get_image(soup, url)
        self.assertEqual(image, expected_image_url)

        expected_image_url = 'http://img.img/img'
        soup = BeautifulSoup('<html><head><img src="' + expected_image_url + '"></head></html>')
        image = crawler.get_image(soup, url)
        self.assertEqual(image, expected_image_url)

        expected_image_url = '/img'
        soup = BeautifulSoup(
            '<html><head><img src="' + expected_image_url + '"><img src="/unimportant.png"></head></html>')
        image = crawler.get_image(soup, url)
        self.assertEqual(image, url + expected_image_url)

        soup = BeautifulSoup('')
        image = crawler.get_image(soup, url)
        self.assertEqual(image, '')

        img_url = '/static/img/logo.png'
        expected_image_url = url + img_url
        soup = BeautifulSoup('<html><head><img src="' + img_url + '"></head></html>')
        image = crawler.get_image(soup, url)
        self.assertEqual(image, expected_image_url)

    def test_crawler_get_description(self):
        crawler = Crawler()
        expected_desc = 'description'
        soup = BeautifulSoup('<html><head><meta name="og:description" content="' + expected_desc + '"></head></html>')
        desc = crawler.get_description(soup)
        self.assertEqual(desc, expected_desc)

        soup = BeautifulSoup('<html><head><meta name="description" content="' + expected_desc + '"></head></html>')
        desc = crawler.get_description(soup)
        self.assertEqual(desc, expected_desc)

        soup = BeautifulSoup('')
        desc = crawler.get_description(soup)
        self.assertEqual(desc, '')

    def test_get_company_name(self):
        crawler = CodeCommentCrawler()
        soup = BeautifulSoup('<html><head><title>awesome company name</title></head></html>')
        company_name = crawler.get_company_name(soup, 'awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = crawler.get_company_name(soup, 'http://www.awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = crawler.get_company_name(soup, 'http://awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = crawler.get_company_name(soup, 'https://www.awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = crawler.get_company_name(soup, 'http://awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = crawler.get_company_name(soup, 'http://www.awesomecompanyname.co.nz')
        self.assertEqual(company_name, 'Awesome Company Name')

    def test_processing_code_comment(self):
        with open('tests/test_job_posting.html') as f:
            posting = f.read(999999)
        soup = BeautifulSoup(posting)
        crawler = CodeCommentCrawler()
        url = 'https://www.awesomecompanyname.com'
        crawler.process(soup, url)
        self.assertEqual(len(crawler.postings), 1)
        job_posting = crawler.postings[0]

        self.assertEqual(set(job_posting.tags), {'html', 'css', 'bootstrap'})
        self.assertEqual(job_posting.code_comment_url, url)
        self.assertEqual(job_posting.title, 'test title')

        return crawler

    def test_processing_robots(self):
        with open('tests/tripadvisor_robots.txt') as f:
            posting = f.read(999999)
        soup = BeautifulSoup(posting)
        crawler = self.test_processing_code_comment()
        url = 'https://www.awesomecompanyname.com/robots.txt'
        crawler.process(soup, url)
        self.assertEqual(len(crawler.postings), 2)
        job_posting = crawler.postings[1]

        self.assertEqual(set(job_posting.tags), {'seo'})
        self.assertEqual(job_posting.code_comment_url, url)

        ## shouldn't add duplicates
        crawler.process(soup, url)
        self.assertEqual(len(crawler.postings), 2)

    def test_processing_wired_with_no_job(self):
        with open('tests/wired-no-job-posting.html') as f:
            posting = f.read(999999)
        soup = BeautifulSoup(posting)
        crawler = self.test_processing_code_comment()
        url = 'https://www.awesomecompanyname.com/science-and-stuff'
        crawler.process(soup, url)
        self.assertEqual(len(crawler.postings), 1)

    def test_get_path(self):
        crawler = CodeCommentCrawler()
        path = crawler.get_path('http://www.awesomecompanyname.co.nz')
        self.assertEqual(path, '')
        path = crawler.get_path('http://www.awesomecompanyname.co.nz/')
        self.assertEqual(path, '/')
        path = crawler.get_path('http://www.awesomecompanyname.co.nz/path')
        self.assertEqual(path, '/path')
        path = crawler.get_path('http://www.awesomecompanyname.co.nz/path?x=1#thing')
        self.assertEqual(path, '/path?x=1#thing')

    def test_insert_job_posting(self):
        job_posting = JobPosting()
        job_posting.title = 'asdf'
        job_posting.urltitle = 'asdf'
        job_posting.company_name = 'company'
        job_posting.company_url = 'http://asdf.asdf'
        job_posting.company_image_url = 'http://www.img.url'
        job_posting.code_comment = 'comment'
        job_posting.code_comment_url = 'url'
        # job_posting.tags = ['test', 'tag']
        job_posting.put()

        job_postings = JobPosting().query().fetch(5)
        self.assertEqual(len(job_postings), 1)

