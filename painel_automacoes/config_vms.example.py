import requests

# ==============================================================================
# --- LÓGICA PROMETHEUS (Pode manter original) ---
# ==============================================================================
def query_prom(query):
    try:
        # Altere para o IP do seu servidor Prometheus se não for localhost
        url = "http://localhost:9090/api/v1/query"
        r = requests.get(url, params={'query': query}, timeout=2).json()
        if r['data']['result']: return float(r['data']['result'][0]['value'][1])
        return None
    except: return None

def get_all_vms():
    try:
        url = "http://localhost:9090/api/v1/label/instance/values"
        vms = requests.get(url).json()['data']
        # Filtra instâncias que rodam o Node Exporter (porta padrão 9182)
        return [vm for vm in vms if "9182" in vm]
    except: return []

# ==============================================================================
# --- ESTRUTURA DE CONFIGURAÇÃO (Exemplo Mascarado) ---
# ==============================================================================

VMS = {
    "192.168.1.10": {
        "nome": "Servidor_Alpha",
        "apps": [
            {
                "nome": "App Demonstração", 
                "url": "http://192.168.1.10:5000/status", 
                "tipo": "api_json"
            }
        ]
    }
}