import requests

def query_prom(query):
    # Lógica do Prometheus aqui...
    pass

def get_all_vms():
    # Lógica do Prometheus aqui...
    pass

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