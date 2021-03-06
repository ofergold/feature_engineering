from features.title import TitleExtractor
from features.main_text import MainTextExtractor
from features.images import ImagesExtractor
from features.sentiment import getSentimentText, findSentiment
from features.keywords import KeywordsExtractor
from features.entities import Entities
from features.author import AuthorExtractor
from features.category import Classifier
from goose import Goose
from lxml import etree
from pyteaser_c import Summarize
from pyteaser_c import SummarizePage
from pyteaser_c import GetArticle
from pyteaser_c import keywords
from textblob import TextBlob
import langid


class NoMainTextException(Exception):
    pass


class Link(object):
	@classmethod
	def extract(self, link, entity_description=False, sentiment=False, data_path='./data/'):
		errors, summaries, categories, entities, keywords = [], [], [], [], []
		article = Goose().extract(link)

		if not article.raw_doc:
			raise NoMainTextException

		authors = AuthorExtractor.extract(link, article.raw_html)
		publish_date = article.publish_date if article.publish_date else None

		if not article.title:
			article.title = TitleExtractor.extract(
				article.raw_html, article.raw_doc)[0]

		k = KeywordsExtractor(num_kewyords=20, verbose=True, data_path=data_path)

		if article.top_node is not None:
			main_body = etree.tostring(article.top_node)
		else:
			cleant_text_suggestions = MainTextExtractor.extract(article.raw_html, article.raw_doc)
			article.cleaned_text = cleant_text_suggestions[1]
			if not article.cleaned_text:
				article.cleaned_text = cleant_text_suggestions[2]
			if not article.cleaned_text:
				raise NoMainTextException
			main_body = 'Sorry, we could not detect the main HTML content for this article'

		try:
			summaries = Summarize(
				article.title, article.cleaned_text.encode('utf-8', 'ignore'))
		except Exception, e:
			summaries.append('We could not make summaries at this time.')

		try:
			text_sentiment = getSentimentText(article.cleaned_text)
		except Exception, e:
			text_sentiment = None
		text = article.title + " " + article.cleaned_text
		keywords = k.extract([text], None, None, 'news')[0]

		# Get keywords from meta tag
		if not keywords:
			keywords = article.meta_keywords.split(',')

		# Get keywords from Goose
		if not keywords:
			keywords = [t for t in article.tags]

		if sentiment:
			keywords = findSentiment(keywords)

		ent = Entities()
		try:
			entities = ent.extract(text, entity_description)
		except Exception, e:
			entities.append('We could not extract entities at this time.')

		if sentiment:
			entities = findSentiment(entities)

		language = article.meta_lang

		if not language:
			language = langid.classify(article.cleaned_text)[0]

		if language in ['en', 'eo']:
			clf = Classifier(data_path=data_path)
			article.categories = clf.predict(text)
		else:
			article.categories = ["Article classification not ready for: " + language[0]]

		if article.top_image:
			thumbnail = article.top_image.src
		else:
			images = ImagesExtractor.extract(link, article.raw_html)
			thumbnail = images[0] if images else None

		return {
			"title": article.title,
			"link": article.final_url,
			"author": authors,
			"cleaned_text": article.cleaned_text,
			"text_sentiment": text_sentiment,
			"main_body": main_body,
			"image": thumbnail,
			"date": article.publish_date,
			"tags": keywords,
			"entities": entities,
			"language": language,
			"summary": summaries,
			"categories": article.categories
		}

if __name__ == '__main__':
	l = Link()
	l = l.extract('http://techcrunch.com/2016/03/18/twitter-says-few-users-have-opted-out-of-its-new-algorithmic-timeline/')
	print l
