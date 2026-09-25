import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler

# Vercel inyecta automáticamente estas variables cuando creas la base de datos KV
KV_REST_API_URL = os.environ.get('KV_REST_API_URL')
KV_REST_API_TOKEN = os.environ.get('KV_REST_API_TOKEN')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req_json = json.loads(post_data.decode('utf-8'))
            
            action = req_json.get("action")
            hw_hash = req_json.get("hw_hash")
            
            if not hw_hash:
                self._send_json(400, {"status": "error", "message": "Missing hw_hash"})
                return
            
            # --- ACCIÓN 1: RESPALDAR LICENCIA ---
            if action == "backup":
                payload = req_json.get("payload")
                if self._kv_set(hw_hash, payload):
                    self._send_json(200, {"status": "success", "message": "Backup saved"})
                else:
                    self._send_json(500, {"status": "error", "message": "KV Storage Failed"})
                    
            # --- ACCIÓN 2: RECUPERAR LICENCIA ---
            elif action == "recover":
                payload = self._kv_get(hw_hash)
                if payload:
                    self._send_json(200, {"status": "success", "payload": payload})
                else:
                    self._send_json(404, {"status": "error", "message": "No backup found"})
            
            else:
                self._send_json(400, {"status": "error", "message": "Invalid action"})
                
        except Exception as e:
            self._send_json(500, {"status": "error", "message": str(e)})

    def _send_json(self, status_code, data_dict):
        """Utilidad para responder JSON correctamente formateado"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        # Permitir CORS por si en el futuro conectas un dashboard web
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        self.wfile.write(json.dumps(data_dict).encode('utf-8'))

    def _kv_set(self, key, value):
        """Guarda un dato en Vercel KV vía REST"""
        if not KV_REST_API_URL: return False
        url = f"{KV_REST_API_URL}/set/{key}"
        req = urllib.request.Request(url, data=json.dumps(value).encode('utf-8'), method='POST')
        req.add_header('Authorization', f'Bearer {KV_REST_API_TOKEN}')
        try:
            urllib.request.urlopen(req)
            return True
        except:
            return False

    def _kv_get(self, key):
        """Recupera un dato de Vercel KV vía REST"""
        if not KV_REST_API_URL: return None
        url = f"{KV_REST_API_URL}/get/{key}"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {KV_REST_API_TOKEN}')
        try:
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read().decode('utf-8'))
                return res.get("result")
        except:
            return None