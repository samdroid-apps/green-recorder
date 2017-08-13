import urllib.parse


def url_to_filepath(url: str):
    '''
    Takes a url (or filepath) and returns a file path
    '''
    res = urllib.parse.urlparse(url)
    assert (not res.scheme) or (res.scheme == 'file')
    return res.path
