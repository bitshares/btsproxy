#!/usr/bin/python3.5

import functools
import binascii
import hashlib
import logging
import struct
import time
import json
import sys
import os

import tornado.web
import tornado.gen
import tornado.ioloop
import tornado.websocket
import tornado.httpclient

logging.basicConfig(level=logging.INFO)

class ESClient:
    def __init__(self, es_url):
        self.es_url = es_url
        self.http = tornado.httpclient.AsyncHTTPClient()

    async def es_search(self, **data):
        url = self.es_url + 'graphene-*/data/_search'
        logging.info("ES request: %s" % json.dumps(data))

        response = await self.http.fetch(
            url,
            method='POST',
            body=json.dumps(data),
            headers={'Content-Type': 'application/json'},
        )
        ret = json.loads(response.body.decode('utf-8'))

        err = ret.get('error')
        if err:
            raise RPCError(err['reason'])

        return list(map(lambda x: x['_source'], ret['hits']['hits']))

    async def get_op_list(self, account, start, end, limit):
        logging.info("get_op_list(%s, %d, %d, %d)" % (account, start, end, limit))

        if end == 0: end = 999999999 # Large enough currently before es plugin update
        
        ns = len(str(start))          # 12
        ne = len(str(end))            # 9876

        assert ns <= ne
        if ns == ne:
            return await self._real_get_op_list(account, start, end, limit)

        right_start = 10 ** (ne - 1)  # 1000
        left_end = right_start - 1    # 999

        ret = await self.get_op_list(account, right_start, end, limit)
        limit -= len(ret)
        if limit > 0: # We don't have enough in current digit, so recurse.
            ret += await self.get_op_list(account, start, left_end, limit)

        return ret
    
    async def _real_get_op_list(self, account, start, end, limit):
        logging.info("Get %s account history within [%d, %d]" % (account, start, end))

        id_range = {'gte': '1.11.%d' % start, 'lte': '1.11.%d' % end}
        assert len(id_range['gte']) == len(id_range['lte'])
        query_clause = {
            'must': {'term': {"account_history.account": account}},
            'filter':{'range': {'account_history.operation_id': id_range}},
        }
        valid_length = len(id_range['gte'])

        raw_ops = await self.es_search(
            query={'bool': query_clause},
            sort={"account_history.sequence": 'desc'},
            size=limit,
        )

        ret = []
        for i in raw_ops:
            if len(i['account_history']['operation_id']) != valid_length:
                logging.info("Removed invalid op %s from [%d, %d]" % (
                    i['account_history']['operation_id'], start, end,
                ))
                continue

            ret.append({
                'block_num': i['block_data']['block_num'],
                'trx_in_block': i['operation_history']['trx_in_block'],
                'op_in_trx': i['operation_history']['op_in_trx'],
                'id': i['account_history']['operation_id'],
                'op': json.loads(i['operation_history']['op']),
                'result': i['operation_history']['operation_result'],
                'virtual_op': i['operation_history']['virtual_op'],
            })

        return ret

class RPCHandler(tornado.web.RequestHandler):
    pass

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    async def open(self):
        self._client = await tornado.websocket.websocket_connect(
            os.environ['WS_URL'], on_message_callback=self.on_server_message,
        )

    def on_server_message(self, message):
        if not message:
            # Remote server closed
            logging.debug("Remote closed.")
            self.close()
            return

        logging.debug('> %s' % message)
        self.write_message(message)

    async def on_message(self, message):
        if not getattr(self, '_client', None):
            logging.warning("No client?!")
            self._client = await tornado.websocket.websocket_connect(
                os.environ['WS_URL'], on_message_callback=self.on_server_message,
            )

        if (await self.handle_history_message(message)): return

        logging.debug("< %s" % message)
        self._client.write_message(message)

    def on_close(self):
        logging.debug("Close code: %s, reason: %s" % (self.close_code, self.close_reason))
        self._client.close(self.close_code, self.close_reason)

    async def handle_history_message(self, message):
        try:
            req = json.loads(message)
            if not (req['method'] == 'call'
                    and req['params'][1] == 'get_account_history'):
                return False
        except Exception as e:
            # Possibly malformed message or whatever :)
            return False

        try:
            id = req['id']
            args = req['params'][2]
            account, start, limit, end = args

            n_start = int(start.split('.')[2])
            n_end   = int(  end.split('.')[2])
            limit   = int(limit)
            assert limit >= 0
        except Exception as e:
            # Still possibly malformed message
            return False

        op_list = await ES.get_op_list(account, n_start, n_end, limit)

        ret = {
            'id': id,
            'jsonrpc': "2.0",
            'result': op_list,
        }

        self.write_message(json.dumps(ret))
        return True


def main():
    ioloop = tornado.ioloop.IOLoop.current()

    globals()['ES'] = ESClient(os.environ['ES_URL'])

    app = tornado.web.Application([
        (r"/ws", WebSocketHandler),
        (r"/rpc", RPCHandler),
    ])
    cert = os.environ.get('SSL_CERT')
    if cert:
        ssl_options = {'certfile': cert, 'keyfile': os.environ['SSL_KEY']}
        port = 443
    else:
        print("Warning: No SSL is configured.")
        ssl_options = None
        port = 80
    port = int(os.environ.get('LISTEN_PORT', port))

    svr = tornado.httpserver.HTTPServer(app, ssl_options=ssl_options)
    svr.listen(port)

    logging.info("BTSProxy server ready to serve at port %d" % port)
    sys.stdout.flush()

    ioloop.start()

if __name__ == "__main__":
    main()
