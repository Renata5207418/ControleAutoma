import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from nomes_vm import NOMES_VMS
from config_vms import VMS, get_all_vms, query_prom
import streamlit.components.v1 as components

# 1. Configurações da página
st.set_page_config(page_title="Ops Command Center", layout="wide", initial_sidebar_state="collapsed")

# ==============================================================================
# --- JAVASCRIPT: CHUVA MATRIX ---
# ==============================================================================
matrix_rain_code = """
<script>
    const parentDoc = window.parent.document;
    
    // Só cria o canvas se ele ainda não existir
    if (!parentDoc.getElementById('matrix-canvas')) {
        const canvas = parentDoc.createElement('canvas');
        canvas.id = 'matrix-canvas';
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100vw';
        canvas.style.height = '100vh';
        canvas.style.zIndex = '0'; 
        canvas.style.opacity = '0.06'; 
        canvas.style.pointerEvents = 'none'; 
        parentDoc.body.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        
        function resizeCanvas() {
            canvas.width = parentDoc.documentElement.clientWidth;
            canvas.height = parentDoc.documentElement.clientHeight;
        }
        resizeCanvas();
        parentDoc.defaultView.addEventListener('resize', resizeCanvas);

        const chars = "01".split("");
        const fontSize = 16;
        let columns = Math.floor(canvas.width / fontSize);
        let drops = [];
        for (let x = 0; x < columns; x++) drops[x] = 1;

        function draw() {
            // Fundo que apaga o rastro (mesma cor do tema dark do streamlit)
            ctx.fillStyle = "rgba(14, 17, 23, 0.1)"; 
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Cor verde tech
            ctx.fillStyle = "#00ff00"; 
            ctx.font = fontSize + "px monospace";
            
            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(draw, 50);
    }
</script>
"""
components.html(matrix_rain_code, height=0, width=0)

# ==============================================================================
# --- CSS CUSTOMIZADO  ---
# ==============================================================================
css = """
<style>   
    .stApp { background: transparent !important; }    
   
    [data-testid="stVerticalBlock"] > div:has(div[style*="border"]) {
        background-color: rgba(14, 17, 23, 0.9) !important;
        border: 1px solid #333 !important;
    }
    
    div[data-testid="stMetricValue"] { 
        font-family: 'Fira Code', monospace; 
        font-size: 1.2rem !important; 
        color: #00f2fe !important; 
        white-space: nowrap !important; 
    }

    /* Modal Largo */
    div[data-testid="stDialog"] div[role="dialog"] {
        width: 80vw !important;
        max-width: 1200px !important;
        background-color: rgba(10, 10, 14, 0.98) !important;
        border: 1px solid #4facfe !important;
        box-shadow: 0 0 20px rgba(79, 172, 254, 0.2) !important;
    }

    /* Classes HTML para os cards dentro do modal */
    .tech-container { display: flex; flex-direction: row; gap: 20px; justify-content: center; flex-wrap: wrap; }
    .tech-card { background: #0a0a0c; border: 1px solid #333; border-radius: 8px; padding: 20px; flex: 1; min-width: 250px; font-family: monospace; }
    .tech-title { font-size: 1.1rem; color: #fff; font-weight: bold; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; }
    .tech-data { color: #aaa; font-size: 0.9rem; margin-bottom: 5px; }
    .tech-time { color: #555; font-size: 0.8rem; margin-top: 15px; }
    .status-run { color: #39ff14; font-weight: bold; }
    .status-stop { color: #f5af19; font-weight: bold; }
    .status-err { color: #ff416c; font-weight: bold; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)


# ==============================================================================
# --- FUNÇÃO DO MODAL ---
# ==============================================================================
@st.dialog("Detalhes das Aplicações")
def mostrar_detalhes_apps(vm_ip, apps):
    st.markdown(f"**📡 IP DA MÁQUINA:** `{vm_ip}`")
    
    # Construção da string HTML linha por linha sem espaços de tabulação
    html = "<div class='tech-container'>"
    
    for app in apps:
        try:
            r = requests.get(app["url"], timeout=2).json()
            
            # APURAÇÃO
            if app["tipo"] == "api_json":
                is_run = r.get("is_running", False)
                status = "RUNNING" if is_run else "STOPPED"
                color = "status-run" if is_run else "status-stop"
                msg = r.get("messages", ["Aguardando..."])[-1]
                data = r.get("last_update") or r.get("ultima_atualizacao", "---")
                
                html += "<div class='tech-card'>"
                html += f"<div class='tech-title'><span>🟢 {app['nome']}</span><span class='{color}'>{status}</span></div>"
                html += f"<div class='tech-data'>📍 Ação: {msg}</div>"
                html += f"<div class='tech-time'>🕒 Atualizado: {data}</div>"
                html += "</div>"
                
            # E-MAILS
            elif app["tipo"] == "api_json_simples":
                data = r.get("last_update", "---")
                msg = r.get("message", "Sem registros.")
                
                html += "<div class='tech-card'>"
                html += f"<div class='tech-title'><span>📧 {app['nome']}</span><span style='color:#4facfe;'>STANDBY</span></div>"
                html += f"<div class='tech-data'>📝 Resumo: {msg}</div>"
                html += f"<div class='tech-time'>🕒 Último Envio: {data}</div>"
                html += "</div>"
                
        except:
            # ERRO
            html += "<div class='tech-card' style='border-color: #ff416c;'>"
            html += f"<div class='tech-title'><span>❌ {app['nome']}</span><span class='status-err'>OFFLINE</span></div>"
            html += "<div class='tech-data' style='color:#ff416c;'>Erro de conexão com API.</div>"
            html += "</div>"
            
    html += "</div>"
    
    # Renderiza o HTML final
    st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("FECHAR CONSOLE", use_container_width=True):
        st.rerun()


# HEADER
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("<h2 style='color:#00f2fe; margin-bottom:0;'>SYSTEMS COMMAND CENTER</h2>", unsafe_allow_html=True)
with col2:
    if st.button('🔄 ATUALIZAR'): st.rerun()

st.caption(f"Leitura Sincronizada: {datetime.now().strftime('%H:%M:%S')}")
st.divider()

vms_list = get_all_vms()

if not vms_list:
    st.warning("Nenhuma VM Windows detectada pelo Exporter.")
else:
    cols = st.columns(3)
    
    for i, vm_addr in enumerate(vms_list):
        ip = vm_addr.split(':')[0]
        nome = NOMES_VMS.get(ip, "Desconhecido")
        config = VMS.get(ip, {"apps": []})
        
        with cols[i % 3]:
            with st.container(border=True):
                is_up = query_prom(f'up{{instance="{vm_addr}"}}') == 1.0
                status_icon = "🟢" if is_up else "🔴"
                
                st.subheader(f"{status_icon} {nome}")
                st.caption(f"IP Address: {ip}")
                
                if is_up:
                    cpu = query_prom(f'100 - (avg(rate(windows_cpu_time_total{{instance="{vm_addr}", mode="idle"}}[2m])) * 100)')
                    ram = query_prom(f'100 - ((windows_memory_available_bytes{{instance="{vm_addr}"}} / windows_memory_physical_total_bytes{{instance="{vm_addr}"}}) * 100)')
                    disco = query_prom(f'100 - ((windows_logical_disk_free_bytes{{instance="{vm_addr}", volume="C:"}} / windows_logical_disk_size_bytes{{instance="{vm_addr}", volume="C:"}}) * 100)')
                    
                    c1, c2, c3 = st.columns(3)
                    def format_metric(val):
                        if val is None: return "---"
                        alert = "🔥" if val > 85 else ""
                        return f"{val:.1f}% {alert}"

                    c1.metric("CPU", format_metric(cpu))
                    c2.metric("RAM", format_metric(ram))
                    c3.metric("Disco", format_metric(disco))

                    if config["apps"]:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button(f"⚙️ ABRIR CONSOLE [{len(config['apps'])}]", key=f"btn_{ip}"):
                            mostrar_detalhes_apps(ip, config["apps"])
                    else:
                        st.caption("Nenhuma app mapeada.")
                else:
                    st.error("VM OFFLINE OU SEM COMUNICAÇÃO")