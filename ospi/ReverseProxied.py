# coding=utf-8

__author__ = "Gina Häußge <osd@foosel.net>, Christopher Bright <christopher.bright@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

class ReverseProxied(object):
	"""
	Wrap the application in this middleware and configure the
	front-end server to add these headers, to let you quietly bind
	this to a URL other than / and to an HTTP scheme that is
	different than what is used locally.

	In nginx:
		location /myprefix {
			proxy_pass http://192.168.0.1:5001;
			proxy_set_header Host $host;
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header X-Forwarded-Proto $scheme;
			proxy_set_header X-Script-Name /myprefix;
		}

	:param app: the WSGI application
	"""

	def __init__(self, app):
		self.app = app

	def __call__(self, environ, start_response):
		script_name = environ.get('HTTP_X_SCRIPT_NAME', '')

		if script_name:
			environ['SCRIPT_NAME'] = script_name
			path_info = environ['PATH_INFO']
			if path_info.startswith(script_name):
				environ['PATH_INFO'] = path_info[len(script_name):]

		scheme = environ.get('X-Forwarded-Proto', '')

		if scheme:
			environ['wsgi.url_scheme'] = scheme

		host = environ.get('HTTP_X_FORWARDED_HOST', '')

		if host:
			environ['HTTP_HOST'] = host

		return self.app(environ, start_response)
