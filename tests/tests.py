import unittest
from google.appengine.ext import testbed
from google.appengine.ext import ndb
from google.appengine.ext.deferred import deferred
from Models import JobPosting
from bs4 import BeautifulSoup
from crawlers import *
from crawlers.crawlers import Crawler, CodeCommentCrawler


class CrawlerTests(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

    def test_crawler(self):
        word_games_crawler = CodeCommentCrawler()
        word_games_crawler.seen_pages_limit = 20
        word_games_crawler.site_url = 'http://localhost:5000'
        word_games_crawler.go()

    def test_get_company_name(self):
        word_games_crawler = CodeCommentCrawler()
        soup = BeautifulSoup('<html><head><title>awesome company name</title></head></html>')
        company_name = word_games_crawler.get_company_name(soup, 'awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = word_games_crawler.get_company_name(soup, 'http://www.awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = word_games_crawler.get_company_name(soup, 'http://awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = word_games_crawler.get_company_name(soup, 'https://www.awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = word_games_crawler.get_company_name(soup, 'http://awesomecompanyname.com')
        self.assertEqual(company_name, 'Awesome Company Name')
        company_name = word_games_crawler.get_company_name(soup, 'http://www.awesomecompanyname.co.nz')
        self.assertEqual(company_name, 'Awesome Company Name')


    def test_processing_code_comment(self):
        with open('tests/test_job_posting.html') as f:
            posting = f.read(999999)
        soup = BeautifulSoup(posting)
        word_games_crawler = CodeCommentCrawler()
        url = 'https://www.awesomecompanyname.com'
        word_games_crawler.process(soup, url)
        job_postings = JobPosting().query().fetch(5)
        self.assertEqual(len(job_postings), 1)

        self.assertEqual(set(job_postings.tags), {'html', 'css', 'bootstrap'})
        self.assertEqual(job_postings.code_comment_url, url)



