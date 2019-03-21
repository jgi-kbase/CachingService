"""User authorization utilities."""
import flask
import functools
import requests

from ..config import Config
from ..exceptions import MissingHeader, UnauthorizedAccess


def requires_service_token(fn):
    """
    Authorize that the requester is a valid, registered service on KBase.
    Validate a token passed in the 'Authorization' header.

    If valid, then set a session value to be the token's username and name.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        token = flask.request.headers.get('Authorization')
        if not token:
            raise MissingHeader('Authorization')
        headers = {'Authorization': token}
        url = Config.kbase_auth_url + '/api/V2/token'
        auth_resp = requests.get(url, headers=headers)
        auth_json = auth_resp.json()
        if 'error' in auth_json:
            raise UnauthorizedAccess(auth_json['error']['message'])
            resp = {
                'error': auth_json['error']['message'],
                'status': 'error',
                'auth_endpoint': Config.kbase_auth_url
            }
            return (flask.jsonify(resp), 403)
        else:
            token_id = ':'.join([Config.kbase_auth_url, auth_json['user']])
            flask.session['token_id'] = token_id
            return fn(*args, **kwargs)
    return wrapper
