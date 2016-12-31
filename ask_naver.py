import sublime
import sublime_plugin
import socket
import types
import threading
import http.client
import time
import urllib.request
import json
import configparser
import os

gPrevHttpRequest = ""

CHECK_DOWNLOAD_THREAD_TIME_MS = 1000


def monitorDownloadThread(downloadThread):
    if downloadThread.is_alive():
        msg = downloadThread.getCurrentMessage()
        sublime.status_message(msg)
        sublime.set_timeout(lambda: monitorDownloadThread(downloadThread), CHECK_DOWNLOAD_THREAD_TIME_MS)
    else:
        downloadThread.showResultToPresenter()


class HttpRequester(threading.Thread):

    REQUEST_TYPE_GET = "GET"
    REQUEST_TYPE_POST = "POST"
    REQUEST_TYPE_DELETE = "DELETE"
    REQUEST_TYPE_PUT = "PUT"

    httpRequestTypes = [REQUEST_TYPE_GET, REQUEST_TYPE_POST, REQUEST_TYPE_PUT, REQUEST_TYPE_DELETE]

    HTTP_URL = "http://"
    HTTPS_URL = "https://"

    httpProtocolTypes = [HTTP_URL, HTTPS_URL]

    HTTP_POST_BODY_START = "POST_BODY:"

    HTTP_PROXY_HEADER = "USE_PROXY"

    HTTPS_SSL_CLIENT_CERT = "CLIENT_SSL_CERT"
    HTTPS_SSL_CLIENT_KEY = "CLIENT_SSL_KEY"

    CONTENT_LENGTH_HEADER = "Content-lenght"

    MAX_BYTES_BUFFER_SIZE = 8192

    FILE_TYPE_HTML = "html"
    FILE_TYPE_JSON = "json"
    FILE_TYPE_XML = "xml"

    HTML_CHARSET_HEADER = "CHARSET"
    htmlCharset = "utf-8"

    httpContentTypes = [FILE_TYPE_HTML, FILE_TYPE_JSON, FILE_TYPE_XML]

    HTML_SHOW_RESULTS_SAME_FILE_HEADER = "SAME_FILE"
    showResultInSameFile = False

    DEFAULT_TIMEOUT = 10
    TIMEOUT_KEY = "TIMEOUT"

    def __init__(self, resultsPresenter):
        self.totalBytesDownloaded = 0
        self.contentLenght = 0
        self.resultsPresenter = resultsPresenter
        threading.Thread.__init__(self)

    def request(self, selection):
        self.selection = selection
        self.start()
        sublime.set_timeout(lambda: monitorDownloadThread(self), CHECK_DOWNLOAD_THREAD_TIME_MS)

    def run(self):
        selection = self.selection

        respText = ""
        fileType = ""

        config = configparser.ConfigParser()
        my_file = (os.path.join(os.getcwd(), 'AskNaver/conf-secure.ini'))
        config.read(my_file)

        client_id = config.get('credentials', 'client_id')
        client_secret = config.get('credentials', 'client_secret')

        encText = urllib.parse.quote(selection)
        data = "source=ko&target=en&text=" + encText
        url = "https://openapi.naver.com/v1/language/translate"

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        response = urllib.request.urlopen(request, data=data.encode("utf-8"))
        rescode = response.getcode()
        translation = ""

        if (rescode == 200):
            data = json.loads(response.read().decode("utf-8"));
            translation = data['message']['result']['translatedText']
        else:
            print("Error Code:" + rescode)

        self.respText = translation
        self.fileType = 'html'


    def getResponseTextForPresentation(self, respHeaderText, respBodyText, latencyTimeMilisec, downloadTimeMilisec):
        return respHeaderText + "\n" + "Latency: " + str(latencyTimeMilisec) + "ms" + "\n" + "Download time:" + str(downloadTimeMilisec) + "ms" + "\n\n\n" + respBodyText

    def getCurrentMessage(self):
        return "HttpRequester downloading " + str(self.totalBytesDownloaded) + " / " + str(self.contentLenght)

    def showResultToPresenter(self):
        self.resultsPresenter.createWindowWithText(self.respText, self.fileType, self.showResultInSameFile)


class HttpRequesterRefreshCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        global gPrevHttpRequest
        selection = gPrevHttpRequest

        resultsPresenter = ResultsPresenter()
        httpRequester = HttpRequester(resultsPresenter)
        httpRequester.request(selection)


class HttpRequesterTextWriter(sublime_plugin.TextCommand):

    def run(self, edit, **args):
        self.view.insert(edit, 0, args["text"])


class ResultsPresenter():

    def __init__(self):
        pass

    def createWindowWithText(self, textToDisplay, fileType, showResultInSameFile):
        if not(showResultInSameFile):
            view = sublime.active_window().new_file()
            openedNewView = True
        else:
            view = self.findHttpResponseView()
            openedNewView = False
            if view is None:
                view = sublime.active_window().new_file()
                openedNewView = True
        
        if not(openedNewView):
            view.run_command("http_requester_text_writer", { "text": "\n\n\n"} )

        view.run_command("http_requester_text_writer", { "text": textToDisplay })
        view.set_scratch(True)
        view.set_read_only(False)
        view.set_name("http response")

        if fileType == HttpRequester.FILE_TYPE_HTML:
            view.set_syntax_file("Packages/HTML/HTML.tmLanguage")
        if fileType == HttpRequester.FILE_TYPE_JSON:
            view.set_syntax_file("Packages/JavaScript/JSON.tmLanguage")
        if fileType == HttpRequester.FILE_TYPE_XML:
            view.set_syntax_file("Packages/XML/XML.tmLanguage")

        return view.id()

    def findHttpResponseView(self):
        for window in sublime.windows():
            for view in window.views():
                if view.name() == "http response":
                    return view


class HttpRequesterCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        global gPrevHttpRequest
        selection = ""
        if self.has_selection():
            for region in self.view.sel():
                # Concatenate selected regions together.
                selection += self.view.substr(region)
        else:
            # Use entire document as selection
            entireDocument = sublime.Region(0, self.view.size())
            selection = self.view.substr(entireDocument)

        gPrevHttpRequest = selection
        resultsPresenter = ResultsPresenter()
        httpRequester = HttpRequester(resultsPresenter)
        httpRequester.request(selection)

    def has_selection(self):
        has_selection = False

        # Only enable menu option if at least one region contains selected text.
        for region in self.view.sel():
            if not region.empty():
                has_selection = True

        return has_selection