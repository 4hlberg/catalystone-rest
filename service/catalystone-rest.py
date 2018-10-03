from flask import Flask, request, Response
import os
import requests
import logging
import sys
import json
import dotdictify

app = Flask(__name__)
logger = None
format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger('catalystone-service')

# Log to stdout

stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(format_string))
logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)

##getting token
def get_token(path):
    headers = {}
    test = path
    logger.info("Creating header")

    if test == "user":
        headers = {
            "client_id":os.environ.get('client_id_user'),
            "client_secret":os.environ.get('client_secret_user'),
            "grant_type":os.environ.get('grant_type')
        }
    elif test == "organization":
        headers = {
            "client_id":os.environ.get('client_id_org'),
            "client_secret":os.environ.get('client_secret_org'),
            "grant_type":os.environ.get('grant_type')
        }
    elif test == "post_user":
        headers = {
            "client_id": os.environ.get('client_id_post'),
            "client_secret": os.environ.get('client_secret_post'),
            "grant_type": os.environ.get('grant_type')
        }
    else:
        logger.info("undefined method")
        sys.exit()

    resp = requests.get(url=os.environ.get('token_url'), headers=headers).json()
    token = dotdictify.dotdictify(resp).response.responseMessage.access_token
    logger.info("Received access token from " + os.environ.get('token_url'))
    return token

class DataAccess:

#main get function check for path and make decisions based on that value
    def __get_all_entities(self, path):
        logger.info("Fetching data from url: %s", path)
        token = get_token(path)
        headers= {'Accept': 'application/json',
                  'content_type': 'application/json'}
        url = os.environ.get('get_url') + "?access_token=" + token
        logger.info("Fetching data from url: %s", path)
        req = requests.get(url, headers=headers)

        if req.status_code != 200:
            logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
            raise AssertionError ("Unexpected response status code: %d with response text %s"%(req.status_code, req.text))
        res = dotdictify.dotdictify(json.loads(req.text))
        if path == "user":
            for entity in res.get(os.environ.get("entities_path_user")):

                yield(entity)
        if path == "organization":
            for entity in res.get(os.environ.get("entities_path_org")):
                yield (entity)
        else:
            logger.info("method not recognized")
        logger.info('Returning entities from %s', path)

    def get_entities(self,path):
        print("getting all")
        return self.__get_all_entities(path)

data_access_layer = DataAccess()

# stream entities
def stream_json(clean):
    first = True
    yield '['
    for i, row in enumerate(clean):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'

@app.route("/<path:path>", methods=["GET", "POST"])
def get_path(path):

    if request.method == 'POST':
        post_url = os.environ.get('post_url') + "?access_token=" + get_token(path)
        logger.info(request.get_json())
        entities = request.get_json()
        headers = json.loads(os.environ.get('post_headers').replace("'", "\""))

        logger.info("Sending entities")
        response= requests.post(post_url, data=entities, headers=headers)
        if response.status_code is not 200:
            logger.error("Got error code: " + str(response.status_code) + "with text: " + response.text)
            return Response(response.text, status=response.status_code, mimetype='application/json')
        logger.info("Prosessed " + str(len(entities)) + " entities")
        return Response(response.text, status=response.status_code, mimetype='application/json')


        # if not isinstance(entities, list):
        #     entities = [entities]
        # for entity in entities:
        #     for k, v in entity.items():
        #         if k == os.environ.get('post_url', 'post_url'):
        #             url = baseurl + v
        #     logger.info("Fetching entity with url: " + str(url))
        #     response = requests.post(url, data=entities, headers=headers)
        #     if response.status_code is not 200:
        #         logger.error("Got Error Code: " + str(response.status_code) + " with text: " + response.text)
        #         return Response(response.text, status=response.status_code, mimetype='application/json')
        #     entity[prop] = {
        #         "status_code": response.status_code,
        #         "response_text": json.loads(response.text)
        #
        #     }
        # logger.info("Prosessed " + str(len(entities)) + " entities")
        # return Response(json.dumps(entities), status=response.status_code, mimetype='application/json')

    elif request.method == "GET":
        path = path

    else:
        logger.info("undefined request method")

    entities = data_access_layer.get_entities(path)
    return Response(
        stream_json(entities),
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True, port=os.environ.get('port',5000))
