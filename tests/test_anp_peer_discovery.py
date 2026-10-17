import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent_provider/octopus'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
with patch.dict(os.environ,{'DEBUG':'false'}):
    from octopus.api.auth_middleware import auth_middleware
    from octopus.api.chat_router import router


class PeerDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.app=FastAPI()
        self.app.middleware('http')(auth_middleware)
        self.app.include_router(router,prefix='/v1')

    def test_native_ui_can_discover_without_did_authorization_header(self):
        with patch.dict(os.environ,{'OCTOPUS_GROUP_FILE':''}):
            response=TestClient(self.app).get('/v1/chat/anp/peers')
        self.assertEqual(response.status_code,200,response.text)
        self.assertFalse(response.json()['managed'])

    def test_discovery_rejects_remote_client_and_cross_origin(self):
        response=TestClient(self.app,client=('192.0.2.10',1234)).get('/v1/chat/anp/peers')
        self.assertEqual(response.status_code,403)
        response=TestClient(self.app).get('/v1/chat/anp/peers',headers={'origin':'https://untrusted.example'})
        self.assertEqual(response.status_code,403)


if __name__=='__main__':unittest.main()
