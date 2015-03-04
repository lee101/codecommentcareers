#!/usr/bin/env python

import os

import jinja2
from google.appengine.datastore.datastore_query import Cursor

from crawlers.crawlers import *
import awgutils
from ws import ws

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


class BaseHandler(webapp2.RequestHandler):
    def render(self, view_name, extraParams={}):
        template_values = {
            'ws': ws,
            'awgutils': awgutils,
            'url': self.request.uri,
        }
        template_values.update(extraParams)

        template = JINJA_ENVIRONMENT.get_template(view_name)
        self.response.write(template.render(template_values))

class MainHandler(BaseHandler):
    def get(self):
        curs = Cursor(urlsafe=self.request.get('cursor'))
        job_postings, next_curs, more = JobPosting.query().fetch_page(40, start_cursor=curs)

        if more and next_curs:
            next_page_cursor = next_curs.urlsafe()
        else:
            next_page_cursor = None
        extraParams = {'job_postings': job_postings,
                       'next_page_cursor': next_page_cursor}
        self.render('/templates/index.jinja2', extraParams)



class ContactHandler(BaseHandler):
    def get(self):
        self.render('/templates/contact.jinja2')


class AboutHandler(BaseHandler):
    def get(self):
        self.render('/templates/about.jinja2')


class PrivacyHandler(BaseHandler):
    def get(self):
        self.render('/templates/privacy-policy.jinja2')


class TermsHandler(BaseHandler):
    def get(self):
        self.render('/templates/terms.jinja2')


class SitemapHandler(webapp2.RequestHandler):
    def get(self):
        titles = JobPosting.getAllTitles()
        self.response.headers['Content-Type'] = 'text/xml'
        template = JINJA_ENVIRONMENT.get_template("/templates/sitemap.xml")
        self.response.write(template.render({'titles': titles}))


class LoadGamesHandler(BaseHandler):
    def get(self):
        try:
            urltitle = self.request.get('title')
            curs = Cursor(urlsafe=self.request.get('cursor'))
            if urltitle:

                job_postings, next_curs, more = JobPosting.query().fetch_page(40, start_cursor=curs)
            else:
                job_postings, next_curs, more = JobPosting.query().fetch_page(40, start_cursor=curs)

            if more and next_curs:
                next_page_cursor = next_curs.urlsafe()
            else:
                next_page_cursor = None
            extraParams = {'job_postings': job_postings,
                           'next_page_cursor': next_page_cursor}
        except Exception, err:
            logging.error(Exception)
            logging.error(err)
            import traceback

            traceback.print_exc()
            self.response.write(err)
        self.render('/templates/loadgames.jinja2', extraParams)


class GameHandler(BaseHandler):
    def get(self, urltitle):
        job_posting = JobPosting.oneByUrlTitle(urltitle)
        curs = Cursor(urlsafe=self.request.get('cursor'))
        job_postings, next_curs, more = JobPosting.randomOrder(urltitle).fetch_page(40, start_cursor=curs)

        if more and next_curs:
            next_page_cursor = next_curs.urlsafe()
        else:
            next_page_cursor = None
        extraParams = {'job_posting': job_posting,
                       'job_postings': job_postings,
                       'next_page_cursor': next_page_cursor,
                       'urltitle': urltitle}
        self.render('/templates/game.jinja2', extraParams)


class TagHandler(BaseHandler):
    def get(self, tag):
        curs = Cursor(urlsafe=self.request.get('cursor'))
        job_postings, next_curs, more = JobPosting.byTag(tag).fetch_page(40, start_cursor=curs)

        if more and next_curs:
            next_page_cursor = next_curs.urlsafe()
        else:
            next_page_cursor = None
        extraParams = {
            'job_postings': job_postings,
            'next_page_cursor': next_page_cursor,
            'tag': tag,
            'tagtitle': awgutils.titleDecode(tag),
        }
        self.render('/templates/tag.jinja2', extraParams)


class TestHandler(BaseHandler):
    def get(self):
        test_crawler = CodeCommentCrawler()
        test_crawler.site_url = 'http://localhost:5000'
        test_crawler.go()


class LogoutHandler(BaseHandler):
    def get(self):
        if self.current_user is not None:
            self.session['user'] = None

        self.redirect('/')

# class Thumbnailer(webapp2.RequestHandler):
# def get(self, title):
#         if self.request.get("id"):
#             photo = Photo.get_by_id(int(self.request.get("id")))
#
#             if photo:
#                 img = images.Image(photo.full_size_image)
#                 img.resize(width=80, height=100)
#                 #img.im_feeling_lucky()
#                 thumbnail = img.execute_transforms(output_encoding=images.JPEG)
#
#                 self.response.headers['Content-Type'] = 'image/jpeg'
#                 self.response.out.write(thumbnail)
#                 return
#
#         # Either "id" wasn't provided, or there was no image with that ID
#         # in the datastore.
#         self.error(404)


app = ndb.toplevel(webapp2.WSGIApplication([
                                               ('/', MainHandler),
                                               ('/logout', LogoutHandler),
                                               ('/privacy-policy', PrivacyHandler),
                                               ('/terms', TermsHandler),
                                               ('/about', AboutHandler),
                                               ('/contact', ContactHandler),
                                               ('/job/(.*)', GameHandler),
                                               ('/jobs/(.*)', TagHandler),
                                               ('/gotest', TestHandler),
                                               ('/loadjob_postings', LoadGamesHandler),
                                               ('/sitemap', SitemapHandler),


                                           ], debug=ws.debug))
