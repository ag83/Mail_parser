from bs4 import BeautifulSoup
from StringIO import StringIO
from selenium import webdriver
from pymongo import Connection
from pyvirtualdisplay import Display
import urllib2
import chardet
import os, sys, random

#Informa template


def get_article_links(init_soup, block_name):
   article_refs = []
   for article_header in init_soup.findAll('div', attrs={'class' : block_name}):
      article_refs.append('http://informahealthcare.com'+ article_header.find('a', attrs={'class' : "ref nowrap "}).get('href'))
   return article_refs

def get_js_html(link_a):
   display = Display(visible=0, size=(800, 600))
   display.start()
   drivers = [webdriver.PhantomJS, webdriver.Firefox, webdriver.Chrome]
   drive_eng = random.choice(drivers)()
   drive_eng.set_page_load_timeout(100)
   drive_eng.get(link_a)
   data_html = drive_eng.page_source
   js_soup = BeautifulSoup(data_html)
   drive_eng.quit()
   display.stop()
   return js_soup



connection = Connection('localhost', 27017)
db = connection.journal
articles = db.articles

volumes = ['http://informahealthcare.com/toc/enz/26/5', 'http://informahealthcare.com/toc/enz/26/4', 'http://informahealthcare.com/toc/enz/26/3', 'http://informahealthcare.com/toc/enz/26/2', 'http://informahealthcare.com/toc/enz/26/1', 'http://informahealthcare.com/toc/enz/25/6', 'http://informahealthcare.com/toc/enz/25/5', 'http://informahealthcare.com/toc/enz/25/4', 'http://informahealthcare.com/toc/enz/25/3', 'http://informahealthcare.com/toc/enz/25/2', 'http://informahealthcare.com/toc/enz/25/1'] #collecting volumes links from issues page was failed, manual add

for vols in volumes:
   html_e = get_js_html(vols)
   Volume = html_e.find('div', attrs={'class' : "main_content_text"}).getText()
   articles = get_article_links(html_e, "publication_entry")
   print Volume
   for article_ref in articles:
      for _ in range(2):
         try:
            html_art = get_js_html(article_ref)
            Article_title = html_art.find('div', attrs={'class' : "arttitle"}).getText()
            DOI = html_art.find('div', attrs={'class' : "arttitle"}).findNext('div').getText().split('(')[-1].split(')')[0]
            abst = html_art.find('div', attrs={'class' : "abstractSection"}).find('p').getText()
            Authors = [auth.getText().replace(', ', '').replace('.', '') for auth in html_art.findAll('a', attrs={'class' : "entryAuthor"})]
            corrs = html_art.findAll('div', attrs={'class' : "NLM_corresp"})
            keywords = [ key.getText().replace("; ", "") for key in html_art.find('div', attrs={'class' : "keywords"}).findAll('a') ]
            Corr_author = {}
            for cor in corrs:
               corr_author = cor.getText().split(':', 1)[1].split(',')[0].replace('.', '').replace('\u2002', '')
               corr_mail = cor.find('a', attrs={'class' : "email"}).getText()
               corr_aff = cor.getText().split(':')[1].split(',', 1)[1].split('.')[0]
               country = corr_aff.split(' ')[-1]
               Corr_author.update({corr_author: [corr_mail, corr_aff, country]})
            print Article_title
            db.articles.insert( { 'Type': 'Original Article', 'Journal': 'Journal of Enzyme Inhibition and Medicinal Chemistry', 'Link':article_ref, 'Volume':Volume, 'Title':Article_title, 'DOI':DOI, 'Abstract':abst, 'Authors':Authors, 'corresponding_authors_info':Corr_author, 'keywords':keywords } )
            break
         except Exception, ex: 
            print repr(ex)
            pass



