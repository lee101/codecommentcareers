import unittest
from google.appengine.ext import testbed
from google.appengine.ext import ndb
from google.appengine.ext.deferred import deferred
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

    def testWordGamesCrawler(self):
        word_games_crawler = CodeCommentCrawler()
        word_games_crawler.seen_pages_limit = 20
        word_games_crawler.site_url = 'localhost:5000'
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






