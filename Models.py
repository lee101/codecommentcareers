from google.appengine.ext import ndb


class JobPosting(ndb.Model):
    title = ndb.StringProperty()
    urltitle = ndb.StringProperty()
    company_name = ndb.TextProperty()
    company_description = ndb.TextProperty()
    company_url = ndb.TextProperty()
    company_image_url = ndb.TextProperty()
    code_comment = ndb.TextProperty()
    code_comment_url = ndb.TextProperty()
    rank = ndb.IntegerProperty()
    tags = ndb.StringProperty(repeated=True)

    @classmethod
    def oneByTitle(cls, title):
        return cls.query(cls.title == title).get()

    @classmethod
    def oneByUrlTitle(cls, urltitle):
        return cls.query(cls.urltitle == urltitle).get()

    @classmethod
    def getAllTitles(cls):
        global all_titles

        if len(all_titles) <= 0:
            all_titles = map(lambda x: x.urltitle, cls.query().fetch(5000, projection=[cls.urltitle]))
        return all_titles

    @classmethod
    def byTag(cls, tag):
        return cls.query(cls.tags == tag)
