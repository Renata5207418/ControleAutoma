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
    
    if (!parentDoc.getElementById('matrix-canvas')) {
        const canvas = parentDoc.createElement('canvas');
        canvas.id = 'matrix-canvas';
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100vw';
        canvas.style.height = '100vh';
        canvas.style.zIndex = '0'; 
        canvas.style.opacity = '0.08'; 
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
            ctx.fillStyle = "rgba(10, 10, 14, 0.1)"; 
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
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
# --- CSS CUSTOMIZADO (CLEAN & MODERN) ---
# ==============================================================================
css = """
<style>   
    /* Força fundo transparente e esconde menu padrão do Streamlit */
    .stApp { background: transparent !important; }    
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
   
    /* Estilo dos Cards das VMs: Ajuste direto no wrapper do Streamlit */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(10, 12, 16, 0.7) !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
        padding: 5px !important;
        box-shadow: none !important;
        transition: border-color 0.3s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #334155 !important;
    }

    /* Modal Largo */
    div[data-testid="stDialog"] div[role="dialog"] {
        width: 80vw !important;
        max-width: 1200px !important;
        background-color: rgba(10, 10, 14, 0.98) !important;
        border: 1px solid #1e293b !important;
        box-shadow: 0 0 30px rgba(0, 0, 0, 0.8) !important;
        border-radius: 12px !important;
    }

    /* Estilização Global dos Botões */
    .stButton button {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364) !important;
        border: 1px solid #334155 !important;
        color: #e2e8f0 !important;
        border-radius: 6px !important;
        font-family: monospace !important;
        letter-spacing: 1px !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        border-color: #4facfe !important;
        color: #fff !important;
        box-shadow: 0 0 10px rgba(79, 172, 254, 0.2) !important;
    }

    /* Classes HTML para os cards dentro do modal */
    .tech-container { display: flex; flex-direction: row; gap: 20px; justify-content: center; flex-wrap: wrap; }
    .tech-card { background: #0a0a0c; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; flex: 1; min-width: 250px; font-family: monospace; }
    .tech-title { font-size: 1.1rem; color: #fff; font-weight: bold; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 10px; }
    .tech-data { color: #aaa; font-size: 0.9rem; margin-bottom: 5px; display: flex; align-items: center; gap: 8px;}
    .tech-time { color: #555; font-size: 0.8rem; margin-top: 15px; display: flex; align-items: center; gap: 8px;}
    
    .status-run { color: #39ff14; font-weight: bold; text-shadow: 0 0 5px rgba(57,255,20,0.5); }
    .status-stop { color: #f5af19; font-weight: bold; }
    .status-err { color: #ff416c; font-weight: bold; text-shadow: 0 0 5px rgba(255,65,108,0.5); }
    
    /* Métricas Modernas (Sem caixas duplas) */
    .metric-box { display: flex; flex-direction: column; align-items: flex-start; background: transparent; padding: 0; border: none; width: 30%; }
    .metric-label { font-size: 0.75rem; color: #64748b; display: flex; align-items: center; gap: 5px; text-transform: uppercase; letter-spacing: 1px;}
    .metric-val { font-size: 1.2rem; font-family: 'Fira Code', monospace; color: #38bdf8; margin-top: 5px; font-weight: bold;}
    .metric-val.alert { color: #ff416c; animation: pulse 1.5s infinite; }
    
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.1; } 100% { opacity: 1; } }
    @keyframes pulse { 0% { text-shadow: 0 0 0px #ff416c; } 50% { text-shadow: 0 0 10px #ff416c; } 100% { text-shadow: 0 0 0px #ff416c; } }
</style>
"""
st.markdown(css, unsafe_allow_html=True)


# ==============================================================================
# --- FUNÇÕES DE STATUS E UI ---
# ==============================================================================
def verificar_alerta_apps(apps):
    """Pinga as aplicações com margem de 2s e apita APENAS se houver erro real (Offline/Timeout/500)."""
    for app in apps:
        try:
            # Requisita a API e tenta converter para JSON. Se o app estiver dormindo (STOPPED),
            # a API ainda responde um JSON válido, então não apita.
            requests.get(app["url"], timeout=2.0).json()
        except Exception:
            # Cai aqui somente se a conexão for recusada, der timeout pesado ou retornar HTML/Erro
            return True 
    return False

@st.dialog("Detalhes das Aplicacoes")
def mostrar_detalhes_apps(vm_ip, apps):
    st.markdown(f"<div style='display: flex; align-items: center; gap: 10px; color: #fff; margin-bottom: 20px;'><img src='https://api.iconify.design/lucide/satellite-dish.svg?color=%234facfe' width='20'> <b>IP DA MAQUINA:</b> <code style='color: #00f2fe; background: transparent;'>{vm_ip}</code></div>", unsafe_allow_html=True)
    
    html = "<div class='tech-container'>"
    
    for app in apps:
        try:
            r = requests.get(app["url"], timeout=2).json()
            
            # APURAÇÃO / ROBO
            if app["tipo"] == "api_json":
                is_run = r.get("is_running", False)
                status = "RUNNING" if is_run else "STOPPED"
                color = "status-run" if is_run else "status-stop"
                icon = "play-circle" if is_run else "pause-circle"
                icon_color = "%2339ff14" if is_run else "%23f5af19"
                msg = r.get("messages", ["Aguardando..."])[-1]
                data = r.get("last_update") or r.get("ultima_atualizacao", "---")
                
                html += "<div class='tech-card'>"
                html += f"<div class='tech-title'><span><img src='https://api.iconify.design/lucide/terminal-square.svg?color={icon_color}' width='20' style='vertical-align: middle; margin-right: 8px;'> {app['nome']}</span><span class='{color}'><img src='https://api.iconify.design/lucide/{icon}.svg?color={icon_color}' width='16' style='vertical-align: middle; margin-right: 5px;'>{status}</span></div>"
                html += f"<div class='tech-data'><img src='https://api.iconify.design/lucide/activity.svg?color=%23888' width='16'> Acao: {msg}</div>"
                html += f"<div class='tech-time'><img src='https://api.iconify.design/lucide/clock.svg?color=%23555' width='14'> Atualizado: {data}</div>"
                html += "</div>"
                
            # E-MAILS
            elif app["tipo"] == "api_json_simples":
                data = r.get("last_update", "---")
                msg = r.get("message", "Sem registros.")
                
                html += "<div class='tech-card'>"
                html += f"<div class='tech-title'><span><img src='https://api.iconify.design/lucide/mail.svg?color=%234facfe' width='20' style='vertical-align: middle; margin-right: 8px;'> {app['nome']}</span><span style='color:#4facfe; font-weight: bold;'>STANDBY</span></div>"
                html += f"<div class='tech-data'><img src='https://api.iconify.design/lucide/file-text.svg?color=%23888' width='16'> Resumo: {msg}</div>"
                html += f"<div class='tech-time'><img src='https://api.iconify.design/lucide/clock.svg?color=%23555' width='14'> Ultimo Envio: {data}</div>"
                html += "</div>"
                
        except:
            # ERRO
            html += "<div class='tech-card' style='border-color: #ff416c; box-shadow: inset 0 0 10px rgba(255,65,108,0.1);'>"
            html += f"<div class='tech-title'><span><img src='https://api.iconify.design/lucide/server-crash.svg?color=%23ff416c' width='20' style='vertical-align: middle; margin-right: 8px;'> {app['nome']}</span><span class='status-err'>OFFLINE</span></div>"
            html += "<div class='tech-data' style='color:#ff416c;'><img src='https://api.iconify.design/lucide/wifi-off.svg?color=%23ff416c' width='16'> Erro de conexao com API.</div>"
            html += "</div>"
            
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("FECHAR CONSOLE", use_container_width=True):
        st.rerun()


# ==============================================================================
# --- HEADER ---
# ==============================================================================
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("""
<div style="display: flex; align-items: center; gap: 15px; margin-top: 10px;">
    <img src="https://api.iconify.design/lucide/command.svg?color=%2339ff14" width="40" style="animation: flicker 1.5s infinite alternate;">
    <h2 style="
        color: #39ff14; margin-bottom: 0; font-weight: 900; letter-spacing: 4px; padding-top: 10px;
        text-shadow: 0 0 5px #39ff14, 0 0 10px #39ff14, 0 0 20px #00ff99, 0 0 40px #00ff99;
        animation: flicker 1.5s infinite alternate;
    ">
        SYSTEMS COMMAND CENTER
    </h2>
</div>
<style>@keyframes flicker { 0% { opacity: 1; } 100% { opacity: 0.85; } }</style>
""", unsafe_allow_html=True)

with col2:
    if st.button('REFRESH SYSTEM', use_container_width=True): 
        st.rerun()
    st.markdown(f"<div style='text-align: center; color: #6b7280; font-size: 0.75rem; font-family: monospace; margin-top: 5px; letter-spacing: 1px;'><img src='https://api.iconify.design/lucide/refresh-ccw.svg?color=%236b7280' width='12' style='vertical-align: middle;'> SYNC: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

st.divider()

# ==============================================================================
# --- CORPO DAS VMS ---
# ==============================================================================
vms_list = get_all_vms()

if not vms_list:
    st.markdown("""
    <div style='background: rgba(245, 175, 25, 0.05); border: 1px solid #f5af19; padding: 20px; text-align: center; border-radius: 8px; color: #f5af19; font-weight: bold; font-family: monospace; margin-bottom: 15px;'>
        <img src='https://api.iconify.design/lucide/search-x.svg?color=%23f5af19' width='24' style='vertical-align: middle; margin-right: 10px;'>
        NENHUMA VM WINDOWS DETECTADA PELO EXPORTER
    </div>
    """, unsafe_allow_html=True)
else:
    cols = st.columns(3)
    
    for i, vm_addr in enumerate(vms_list):
        ip = vm_addr.split(':')[0]
        nome = NOMES_VMS.get(ip, "Desconhecido")
        config = VMS.get(ip, {"apps": []})
        
        with cols[i % 3]:
            # Mantemos o container do Streamlit, mas a estilização CSS lá no topo resolve a caixa dupla
            with st.container(border=True):
                is_up = query_prom(f'up{{instance="{vm_addr}"}}') == 1.0                
                
                # Alerta apenas para quedas reais de conexão da aplicação
                has_alert = verificar_alerta_apps(config["apps"]) if (is_up and config["apps"]) else False              
                
                status_color = "%2339ff14" if is_up else "%23ff416c"
                alert_html = f"<img src='https://api.iconify.design/lucide/triangle-alert.svg?color=%23ff416c' width='24' style='animation: blink 1s infinite;' title='Falha de Comunicacao na App'>" if has_alert else ""
                
                st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 10px; margin-bottom: 15px;'>
                    <div style='display: flex; align-items: center; gap: 10px;'>
                        <img src='https://api.iconify.design/lucide/server.svg?color={status_color}' width='24'>
                        <span style='font-size: 1.2rem; font-weight: bold; color: #fff; letter-spacing: 1px;'>{nome}</span>
                    </div>
                    {alert_html}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"<div style='color: #64748b; font-size: 0.8rem; font-family: monospace; margin-bottom: 15px;'><img src='https://api.iconify.design/lucide/network.svg?color=%2364748b' width='12' style='vertical-align: middle;'> {ip}</div>", unsafe_allow_html=True)
                
                if is_up:
                    cpu = query_prom(f'100 - (avg(rate(windows_cpu_time_total{{instance="{vm_addr}", mode="idle"}}[2m])) * 100)')
                    ram = query_prom(f'100 - ((windows_memory_available_bytes{{instance="{vm_addr}"}} / windows_memory_physical_total_bytes{{instance="{vm_addr}"}}) * 100)')
                    disco = query_prom(f'100 - ((windows_logical_disk_free_bytes{{instance="{vm_addr}", volume="C:"}} / windows_logical_disk_size_bytes{{instance="{vm_addr}", volume="C:"}}) * 100)')
                    
                    def get_metric_class(val):
                        return "metric-val alert" if (val and val > 85) else "metric-val"
                        
                    def format_val(val):
                        return f"{val:.1f}%" if val is not None else "---"

                    # Renderizando métricas perfeitamente alinhadas e sem bordas
                    st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; gap: 10px; margin-bottom: 20px;'>
                        <div class='metric-box'>
                            <div class='metric-label'><img src='https://api.iconify.design/lucide/cpu.svg?color=%2364748b' width='14'> CPU</div>
                            <div class='{get_metric_class(cpu)}'>{format_val(cpu)}</div>
                        </div>
                        <div class='metric-box'>
                            <div class='metric-label'><img src='https://api.iconify.design/lucide/memory-stick.svg?color=%2364748b' width='14'> RAM</div>
                            <div class='{get_metric_class(ram)}'>{format_val(ram)}</div>
                        </div>
                        <div class='metric-box'>
                            <div class='metric-label'><img src='https://api.iconify.design/lucide/hard-drive.svg?color=%2364748b' width='14'> DISCO</div>
                            <div class='{get_metric_class(disco)}'>{format_val(disco)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if config["apps"]:
                        btn_text = f"ABRIR CONSOLE [{len(config['apps'])}]"
                        if has_alert: btn_text = f"VERIFICAR ERRO [{len(config['apps'])}]"
                        
                        if st.button(btn_text, key=f"btn_{ip}", use_container_width=True):
                            mostrar_detalhes_apps(ip, config["apps"])
                    else:
                        st.markdown("<div style='text-align: center; color: #475569; font-size: 0.8rem; padding: 10px; border: 1px dashed #1e293b; border-radius: 6px; font-family: monospace;'>Nenhuma app mapeada.</div>", unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='background: rgba(255, 65, 108, 0.05); border: 1px solid #ff416c; padding: 20px; text-align: center; border-radius: 8px; color: #ff416c; font-weight: bold; margin-bottom: 15px; font-family: monospace;'>
                        <img src='https://api.iconify.design/lucide/server-off.svg?color=%23ff416c' width='30' style='margin-bottom: 10px;'><br>
                        VM OFFLINE OU SEM COMUNICACAO
                    </div>
                    """, unsafe_allow_html=True)