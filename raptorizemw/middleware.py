
import BeautifulSoup
import webob

import raptorizemw.resources


class RaptorizeMiddleware(object):
    def __init__(self, app, serve_resources=True, **kw):
        self.app = app
        self.serve_resources = serve_resources
        self.resources_app = raptorizemw.resources.ResourcesApp()

    def __call__(self, environ, start_response):
        __app__ = None
        if self.serve_resources and 'raptorizemw' in environ['PATH_INFO']:
            __app__ = self.resources_app
        else:
            __app__ = self.app

        req = webob.Request(environ)
        resp = req.get_response(__app__, catch_exc_info=True)

        if self.should_raptorize(req, resp):
            resp = self.raptorize(resp)

        return resp(environ, start_response)

    def should_raptorize(self, req, resp):

        if resp.status != "200 OK":
            return False

        content_type = resp.headers.get('Content-Type', 'text/plain').lower()
        if not 'html' in content_type:
            return False

        # TODO -- Add other criteria here.  Path-based, configurable excepts?

        return True

    def raptorize(self, resp):
        soup = BeautifulSoup.BeautifulSoup(resp.body)

        if not soup.html:
            return resp

        if not soup.html.head:
            soup.html.insert(0, BeautifulSoup.Tag(soup, "head"))

        prefix = self.resources_app.prefix
        js_helper = BeautifulSoup.Tag(
            soup, "script", attrs=[
                ('type', 'text/javascript'),
                ('src', prefix + '/js_helper.js'),
            ])
        soup.html.head.insert(len(soup.html.head), js_helper)


        payload_js = BeautifulSoup.Tag(
            soup, "script", attrs=[
                ('type', 'text/javascript'),
            ])
        payload_js.setString(
            """
            run_with_jquery(function() {
                include_js("%s", function() {
                    $(window).load(function() {
                        $('body').raptorize({
                            enterOn: "timer",
                            delayTime: 2000,
                        });
                    });
                })
            });
            """ % (prefix + '/jquery.raptorize.1.0.js')
        )
        soup.html.head.insert(len(soup.html.head), payload_js)

        resp.body = str(soup.prettify())
        return resp


def make_middleware(app=None, **kw):
    app = RaptorizeMiddleware(app, **kw)
    return app