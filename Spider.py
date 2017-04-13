
# encoding: UTF-8
import os
import urllib.request
import urllib
from urllib import parse
import re
from collections import deque
from bs4 import BeautifulSoup
import operator
from html.parser import HTMLParser
from urllib.request import urlopen
from urllib import parse
from doc import Document
from doc import Dictionary
import copy


class Spider:
    def __init__(self,url,pagelimit):
        self.visited = set()
        self.disallow=set()
        self.tovisit=deque()
        self.disallow = []
        self.brokenUrl=set()
        self.disall=set()
        self.url=url
        self.pagelimit=pagelimit
        self.outUrl = set()
        self.docNumber=0
        self.docList = []
        self.term = Dictionary()
        self.allurl=set()
        self.titles=set()
        self.stopword = ['this', 'it', 'are', 'you', 'is', 'for', 'to', 'and', 'The', '1', '2', '3', '4', '5', 'the',
                         'which', 'a', 'be', 'I', 'of', 'in', 'at', 'there','if','there','0','i','s','var','return','26','not','here']

    def parse(self,url):
        content = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(content)
        title=soup.title
        self.titles.add(title)
        text=soup.get_text()


        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = []
        for line in lines:
            for phrase in line.split("  "):
                chunks.append(phrase.strip())
        # drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        self.docNumber += 1
        filename = "doc" + str(self.docNumber) + ".txt"
        with open(filename, 'w') as f:
            f.write(text)
        document = Document(url, self.docNumber, filename, 'html')
        document.setTitle(title)
        # self.docList.append(document)
        # term stemming and collection
        document.stem()
        document.collection()

        # duplicate detection
        duplicate = 0
        for d in self.docList:
            print(d.getID())
            if self.duplicateDetection(document, d) == 1:
                print('duplicate to %d' % d.getID())
                duplicate = 1
                break
        if duplicate == 0:
            self.docList.append(document)
            return 0
        else:
            return 1

    def duplicateDetection(self, doc1, doc2):

        dTerm1 = doc1.getTerm()
        dTerm2 = doc2.getTerm()
        termSet1 = set(dTerm1.keys())
        termSet2 = set(dTerm2.keys())

        Jaccard = len(termSet1 & termSet2) / len(termSet1 | termSet2)
        print("Jaccard: %f" % Jaccard)
        if Jaccard > 0.9:
            return 1
        else:
            return 0

    def robots(self):
        '''fetch robots.txt and get disallow url'''
        mark = re.compile(r'Disallow:')
        robotsUrl = self.url + '/robots.txt'
        urlop = urllib.request.urlopen(robotsUrl)
        for line in urlop:
            line = line.decode('utf-8')
            if mark.match(line):
                disallow = re.split(': ', line)
                disallow_url = disallow[1].strip()
                dis=self.url+disallow_url
                # print(disallow_url)
                self.disallow.append(disallow_url)
                self.disall.add(self.url+disallow_url)
                print(self.url+disallow_url)

    def urlFormalize(self, currentUrl, rawUrl):
        ''' ensure urls do not go out of root direction
            transfer relative url to absolute url
        '''
        components = parse.urlparse(rawUrl)
        formalUrl = rawUrl
        if self.checkPermit(components.path) == 1:  # if url is disallow
            formalUrl = ''
            return formalUrl
        if components.scheme == "http":  # absolute url
            if components.netloc != 'lyle.smu.edu':  # out of root
                self.outUrl |= {rawUrl}
                formalUrl = ''
                print('    out of root')
            else:
                mark = re.compile('/~fmoore')
                if mark.match(components.path) is None:  # out of root
                    self.outUrl |= {rawUrl}
                    formalUrl = ''
                    print("    out of root")
        elif components.scheme == "":  # relative url
            # transfer relative url to absolute url
            formalUrl = parse.urljoin(currentUrl, rawUrl)
            mark = re.compile(self.url)
            if mark.match(formalUrl) is None:  # out of root
                formalUrl = ''
        else:
            formalUrl = ''

        # if url end with /, add index.html to the url
        # if formalUrl != '' and formalUrl[-1] == '/':
        #    formalUrl = formalUrl + 'index.html'

        return formalUrl

    def checkPermit(self, url):
        ''' check weather access the url is disallow
            @return 0: allow
                    1: disallow
        '''
        for disallow_url in self.disallow:
            mark = re.compile(disallow_url)
            if mark.match(url):
                return 1
        return 0
    def collection(self):
        '''term collection'''
        for d in self.docList:
            dTerm = d.getTerm()
            for key in dTerm.keys():
                if self.term[key] != 0:
                    self.term[key] += dTerm[key]
                else:
                    self.term[key] = dTerm[key]
        #print(self.term)

    def stop_word(self):
        self.new_term = copy.copy(self.term)
        for t in self.term.keys():
            if t in self.stopword:
                self.new_term.pop(t, 1)
        print('Now we have eliminated stop words: ')
        print(str(self.new_term) + '\n')

    def fetch(self):
        i=0            #for page limit
        self.tovisit.append(self.url)
        while self.tovisit:

            url = self.tovisit.popleft()
            if url in self.visited:  # url has been crawled
                print("duplication!!!")
                continue
            i=i+1
            print(i)
            self.allurl.add(url)

            if url in self.disall:#detemind robots.txt
                continue

            if i>self.pagelimit:
                break

            req = urllib.request.Request(url)
            try:
                urlop = urllib.request.urlopen(req)
            except urllib.error.HTTPError:
                self.brokenUrl.add(url)
                print(" HTTPError")
                continue
            except urllib.error.URLError:
                self.brokenUrl.add(url)
                continue

            fileType = urlop.getheader('Content-Type')
            if 'text' in fileType:  # text file include txt, htm, html
                print('   text file %s' % urlop.geturl())
                # address exception
                try:
                    data = urlop.read().decode('utf-8')
                except:

                    continue

                # parse data
                self.parse(url)

                # fetch url from page
                linkre = re.compile('href="(.+?)"')
                for x in linkre.findall(data):
                    print("   fetch %s" % x)
                    #self.allUrl |= {x}
                    formalUrl = self.urlFormalize(urlop.geturl(), x)
                    if formalUrl != '':
                        d = self.urlDuplicate(formalUrl)  # duplicattion check
                        if d == 0:
                            self.tovisit.append(formalUrl)
                            print( formalUrl)
                        else:
                            print("duplication")

            elif 'image' in fileType:  # image
                print("image ")
                #self.image |= {url}

                continue
            else:  # other type like pdf
                print("application")
                #self.application |= {url}

                continue



            # soup = BeautifulSoup(content)
            #newurls = soup.find_all('a')
            #for link in newurls:
               #self.tovisit.append(link)

            self.visited.add(url)
            print(url)

    def report(self):
        print('visited url')
        for i in self.visited:
            print(i)

        print('queue')
        print(self.tovisit)

        print(len(self.docList))
        for d in self.docList:
            print(d.getUrl())



        self.collection()
        self.stop_word()

        # ranking

        sorted_term = sorted(self.new_term.items(), key=operator.itemgetter(1))
        # print(sorted_term)
        i = 1
        while i <= 20:
            print(sorted_term[-i])
            i += 1
        for url in self.outUrl:
            print(url)


    def urlDuplicate(self, url):
        ''' eliminate duplicate url
            @return 0: not duplicate
                    1: duplicate
        '''
        duplication = 0
        if url in self.visited:
            duplication = 1
        if url in self.tovisit:
            duplication = 1
        return duplication


spider = Spider('http://lyle.smu.edu/~fmoore',20)
spider.fetch()
spider.report()







