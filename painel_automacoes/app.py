import streamlit as st
import requests
import sqlite3
import pandas as pd
from datetime import datetime
import concurrent.futures
from nomes_vm import NOMES_VMS
from config_vms import VMS, get_all_vms, query_prom
import streamlit.components.v1 as components

# 1. Configurações da página
st.set_page_config(page_title="Ops Command Center", page_icon="https://api.iconify.design/lucide/terminal.svg", layout="wide", initial_sidebar_state="collapsed")

# ==============================================================================
# --- BANCO DE DADOS: KNOWLEDGE BASE ---
# ==============================================================================
def init_db():
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manuals (
            app_name TEXT PRIMARY KEY,
            how_to_start TEXT,
            error_guide TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# --- JAVASCRIPT: CHUVA MATRIX & AUTO-SYNC ---
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

auto_sync_code = """
<script>
    // Auto-sync a cada 30 minutos (1.800.000 ms)
    setTimeout(function() {
        window.parent.location.reload();
    }, 1800000); 
</script>
"""
components.html(auto_sync_code, height=0, width=0)

# ==============================================================================
# --- CSS CUSTOMIZADO ---
# ==============================================================================
css = """
<style>   
    .stApp { background: transparent !important; }    
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
   
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

    div[data-testid="stDialog"] div[role="dialog"] {
        width: 80vw !important;
        max-width: 1200px !important;
        background-color: rgba(10, 10, 14, 0.98) !important;
        border: 1px solid #1e293b !important;
        box-shadow: 0 0 30px rgba(0, 0, 0, 0.8) !important;
        border-radius: 12px !important;
    }

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

    #manual-btn-wrapper button div[data-testid="stMarkdownContainer"] p {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
    }

    #manual-btn-wrapper button div[data-testid="stMarkdownContainer"] p::before {
        content: "";
        display: inline-block;
        width: 18px;
        height: 18px;
        background-image: url('https://api.iconify.design/lucide/book-open.svg?color=%23fecc16');
        background-repeat: no-repeat;
        background-size: contain;
        margin-right: 10px; /* Espaço entre ícone e texto */
    }

    .tech-container { display: flex; flex-direction: row; gap: 20px; justify-content: center; flex-wrap: wrap; }
    .tech-card { background: #0a0a0c; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; flex: 1; min-width: 250px; font-family: monospace; }
    .tech-title { font-size: 1.1rem; color: #fff; font-weight: bold; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 10px; }
    .tech-data { color: #aaa; font-size: 0.9rem; margin-bottom: 5px; display: flex; align-items: center; gap: 8px;}
    .tech-time { color: #555; font-size: 0.8rem; margin-top: 15px; display: flex; align-items: center; gap: 8px;}
    
    .status-run { color: #39ff14; font-weight: bold; text-shadow: 0 0 5px rgba(57,255,20,0.5); }
    .status-stop { color: #f5af19; font-weight: bold; }
    .status-err { color: #ff416c; font-weight: bold; text-shadow: 0 0 5px rgba(255,65,108,0.5); }
    
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
# --- PERFORMANCE & MODAIS (COM REQUISIÇÕES CONCORRENTES BALANCEADAS) ---
# ==============================================================================
@st.cache_data(ttl=30)
def get_all_apps_status(urls):
    """Busca o status limitando a concorrência e reaproveitando conexões."""
    results = {}
    
    # Session reaproveita conexões TCP, aliviando as VMs
    session = requests.Session()
    
    def fetch(url):
        try:
            # Timeout aumentado para 5s para tolerar filas em APIs single-thread
            r = session.get(url, timeout=5)
            return url, r.json()
        except:
            return url, None

    # Reduzido para 5 workers. Evita afogar VMs com múltiplas portas
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url, data = future.result()
            results[url] = data
            
    return results

@st.dialog("DOCUMENTAÇÃO DAS APLICAÇÕES", width="large")
def mostrar_manual_apps():
    # 1. Preparar lista de Apps
    todas_apps = []
    for ip, info in VMS.items():
        for app in info['apps']:
            todas_apps.append(app['nome'])
    todas_apps = sorted(list(set(todas_apps)))

    # --- INICIALIZAÇÃO DE ESTADOS ---
    if 'app_selecionada' not in st.session_state: st.session_state.app_selecionada = todas_apps[0] if todas_apps else ""
    if 'editando_start' not in st.session_state: st.session_state.editando_start = False
    if 'editando_erro' not in st.session_state: st.session_state.editando_erro = False
    if 'search_input' not in st.session_state: st.session_state.search_input = ""

    # --- CALLBACKS ---
    def limpar_busca(): st.session_state.search_input = ""
    def toggle_start(): st.session_state.editando_start = not st.session_state.editando_start
    def toggle_erro(): st.session_state.editando_erro = not st.session_state.editando_erro
    
    # Callback quando clica num botão de aplicação
    def selecionar_app(app_name):
        st.session_state.app_selecionada = app_name
        st.session_state.editando_start = False
        st.session_state.editando_erro = False

    def salvar_start_bd(app, erro_atual):
        novo_texto = st.session_state.get(f"text_i_{app}", "")
        conexao = sqlite3.connect('knowledge_base.db')
        c = conexao.cursor()
        c.execute("INSERT OR REPLACE INTO manuals (app_name, how_to_start, error_guide) VALUES (?, ?, ?)", (app, novo_texto, erro_atual))
        conexao.commit()
        conexao.close()
        st.session_state.editando_start = False

    def salvar_erro_bd(app, start_atual):
        novo_erro = st.session_state.get(f"text_e_{app}", "")
        conexao = sqlite3.connect('knowledge_base.db')
        c = conexao.cursor()
        c.execute("INSERT OR REPLACE INTO manuals (app_name, how_to_start, error_guide) VALUES (?, ?, ?)", (app, start_atual, novo_erro))
        conexao.commit()
        conexao.close()
        st.session_state.editando_erro = False

    # --- CSS NEON PARA OS BOTÕES ---
    st.markdown("""
        <style>
            /* Design base para todos os botões não selecionados (Secundários) */
            div[data-testid="stButton"] button[kind="secondary"] {
                background: transparent !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                color: #e2e8f0 !important;
                justify-content: flex-start !important; 
                border-radius: 4px !important;
            }
            div[data-testid="stButton"] button[kind="secondary"]:hover {
                border-color: rgba(57, 255, 20, 0.5) !important;
                background: rgba(57, 255, 20, 0.05) !important;
            }
            
            /* Design para o botão SELECIONADO (Primário) */
            div[data-testid="stButton"] button[kind="primary"] {
                background: rgba(57, 255, 20, 0.1) !important;
                border: 2px solid #39ff14 !important;
                box-shadow: 0 0 10px rgba(57, 255, 20, 0.2) !important;
                color: #39ff14 !important;
                font-weight: bold !important;
                justify-content: flex-start !important;
                border-radius: 4px !important;
            }

            /* Centraliza apenas os botões de Lápis/Editar */
            div[data-testid="stButton"] button[help^="Editar"] {
                justify-content: center !important;
            }

            .target-header {
                text-align: center; background: rgba(57, 255, 20, 0.05); border: 1px solid rgba(57, 255, 20, 0.2);
                padding: 10px; border-radius: 8px; margin-bottom: 25px; color: #39ff14; font-family: monospace;
                letter-spacing: 5px; text-shadow: 0 0 8px rgba(57, 255, 20, 0.4);
            }
        </style>
    """, unsafe_allow_html=True)

    col_list, col_content = st.columns([1, 2.5], gap="large")

    # --- COLUNA 1: NAVEGAÇÃO COM BOTÕES ---
    with col_list:
        st.markdown("<p style='color: #64748b; font-size: 0.7rem; letter-spacing: 2px; font-weight: bold; margin-bottom: 10px;'>SEARCH_FILTER</p>", unsafe_allow_html=True)
        search_query = st.text_input("Filtrar...", placeholder="Digite e dê Enter...", key="search_input", label_visibility="collapsed")
        
        if search_query:
            st.button("LIMPAR FILTRO", use_container_width=True, on_click=limpar_busca)

        vms_filtradas = [app for app in todas_apps if search_query.lower() in app.lower()]

        if not vms_filtradas:
            st.error("NADA ENCONTRADO")
            return
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        
        # A GAIOLA DA ESQUERDA: Prende os botões num espaço com scroll!
        with st.container(height=550, border=False):
            for app in vms_filtradas:
                tipo_botao = "primary" if app == st.session_state.app_selecionada else "secondary"
                st.button(
                    app, 
                    key=f"btn_{app}", 
                    type=tipo_botao, 
                    use_container_width=True, 
                    on_click=selecionar_app, 
                    args=(app,)
                )

    # Buscar dados da aplicação selecionada
    app_atual = st.session_state.app_selecionada
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    cursor.execute("SELECT how_to_start, error_guide FROM manuals WHERE app_name = ?", (app_atual,))
    result = cursor.fetchone()
    h_start, e_guide = (result[0], result[1]) if result else ("", "")
    conn.close()

    # --- COLUNA 2: CONTEÚDO ---
    with col_content:
        # A GAIOLA DA DIREITA: Prende o texto num espaço do exato mesmo tamanho da esquerda!
        with st.container(height=550, border=False):
            st.markdown(f"<div class='target-header'>TARGET: {app_atual.upper()}</div>", unsafe_allow_html=True)

            c_init, c_err = st.columns(2, gap="medium")

            # --- COLUNA INICIALIZAÇÃO ---
            with c_init:
                h_col1, h_col2 = st.columns([4, 1])
                h_col1.markdown("<b style='color:#39ff14; font-size:0.8rem;'>🟢 START_PROTOCOL</b>", unsafe_allow_html=True)
                
                h_col2.button("", icon=":material/edit:", key=f"btn_edit_i_{app_atual}", help="Editar Inicialização", on_click=toggle_start)
                st.markdown("<div style='height: 1px; background: #39ff14; opacity: 0.3; margin-bottom: 15px;'></div>", unsafe_allow_html=True)
                
                if st.session_state.editando_start:
                    st.text_area("Edit:", value=h_start, height=300, label_visibility="collapsed", key=f"text_i_{app_atual}")
                    st.button("SALVAR START", use_container_width=True, on_click=salvar_start_bd, args=(app_atual, e_guide))
                else:
                    if h_start:
                        h_html = h_start.replace('\n', '<br>')
                        st.markdown(f"""
                            <div style="background: rgba(57, 255, 20, 0.05); border: 1px solid rgba(57, 255, 20, 0.2); 
                                        padding: 15px; border-radius: 5px; color: #bdfcc9; font-size: 0.85rem; 
                                        font-family: monospace;">{h_html}</div>
                        """, unsafe_allow_html=True)
                    else: 
                        st.markdown("<p style='color: #444; font-style: italic;'>No data...</p>", unsafe_allow_html=True)

            # --- COLUNA TROUBLESHOOTING ---
            with c_err:
                h_col1, h_col2 = st.columns([4, 1])
                h_col1.markdown("<b style='color:#ff416c; font-size:0.8rem;'>🔴 ERROR_LOG_FIX</b>", unsafe_allow_html=True)
                
                h_col2.button("", icon=":material/edit:", key=f"btn_edit_e_{app_atual}", help="Editar Erros", on_click=toggle_erro)
                st.markdown("<div style='height: 1px; background: #ff416c; opacity: 0.3; margin-bottom: 15px;'></div>", unsafe_allow_html=True)
                
                if st.session_state.editando_erro:
                    st.text_area("Edit:", value=e_guide, height=300, label_visibility="collapsed", key=f"text_e_{app_atual}")
                    st.button("SALVAR ERROS", use_container_width=True, on_click=salvar_erro_bd, args=(app_atual, h_start))
                else:
                    if e_guide:
                        e_html = e_guide.replace('\n', '<br>')
                        st.markdown(f"""
                            <div style="background: rgba(255, 65, 108, 0.05); border: 1px solid rgba(255, 65, 108, 0.2); 
                                        padding: 15px; border-radius: 5px; color: #ffcbd1; font-size: 0.85rem; 
                                        font-family: monospace;">{e_html}</div>
                        """, unsafe_allow_html=True)
                    else: 
                        st.markdown("<p style='color: #444; font-style: italic;'>No data...</p>", unsafe_allow_html=True)

    conn.close()

def verificar_alerta_apps(apps, app_statuses):
    for app in apps:
        if app_statuses.get(app["url"]) is None:
            return True 
    return False

@st.dialog("Detalhes das Aplicacoes")
def mostrar_detalhes_apps(vm_ip, apps, app_statuses):
    st.markdown(f"<div style='display: flex; align-items: center; gap: 10px; color: #fff; margin-bottom: 20px;'><img src='https://api.iconify.design/lucide/satellite-dish.svg?color=%234facfe' width='20'> <b>IP DA MAQUINA:</b> <code style='color: #00f2fe; background: transparent;'>{vm_ip}</code></div>", unsafe_allow_html=True)
    html = "<div class='tech-container'>"
    for app in apps:
        r = app_statuses.get(app["url"])
        if r:
            is_run = r.get("is_running", False)
            status = "RUNNING" if is_run else "STOPPED"
            color = "status-run" if is_run else "status-stop"
            msg = r.get("messages", ["Aguardando..."])[-1]
            data = r.get("last_update") or r.get("ultima_atualizacao", "---")
            html += f"<div class='tech-card'><div class='tech-title'><span>{app['nome']}</span><span class='{color}'>{status}</span></div>"
            html += f"<div class='tech-data'>Acao: {msg}</div>"
            html += f"<div class='tech-time'>Atualizado: {data}</div></div>"
        else:
            html += f"<div class='tech-card' style='border-color: #ff416c;'><div class='tech-title'><span>{app['nome']}</span><span class='status-err'>OFFLINE</span></div>"
            html += "<div class='tech-data' style='color:#ff416c;'>Erro de conexao com API.</div></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    if st.button("FECHAR CONSOLE", use_container_width=True): st.rerun()


# ==============================================================================
# --- HEADER ---
# ==============================================================================
col1, col2, col3 = st.columns([3.5, 1, 1])
with col1:
    st.markdown("""
<div style="display: flex; align-items: center; gap: 15px; margin-top: 10px;">
    <img src="https://api.iconify.design/lucide/command.svg?color=%2339ff14" width="40" style="animation: flicker 1.5s infinite alternate;">
    <h2 style="color: #39ff14; margin-bottom: 0; font-weight: 900; letter-spacing: 4px; padding-top: 10px; text-shadow: 0 0 5px #39ff14, 0 0 10px #39ff14; animation: flicker 1.5s infinite alternate;">SYSTEMS COMMAND CENTER</h2>
</div>
""", unsafe_allow_html=True)

with col2:
    if st.button('MANUAL APPS', icon=":material/menu_book:", use_container_width=True):
        mostrar_manual_apps()

with col3:
    if st.button('ATUALIZAR', icon=":material/refresh:", use_container_width=True): 
        st.rerun()
    st.markdown(f"<div style='text-align: center; color: #6b7280; font-size: 0.50rem; font-family: monospace; margin-top: 5px;'>Last update: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

st.divider()

# ==============================================================================
# --- FETCH CENTRALIZADO DE APPS (CONCORRENTE BALANCEADO) ---
# ==============================================================================
vms_list = get_all_vms()

# Coleta todas as URLs disponíveis antes de montar o grid
todas_urls_apps = []
if vms_list:
    for vm_addr in vms_list:
        ip = vm_addr.split(':')[0]
        config = VMS.get(ip, {"apps": []})
        for app in config["apps"]:
            todas_urls_apps.append(app["url"])

# Realiza o fetch balanceado e deixa guardado no cache para este ciclo
status_global_apps = get_all_apps_status(tuple(todas_urls_apps))


# ==============================================================================
# --- GRID VMS ---
# ==============================================================================
if not vms_list:
    st.error("NENHUMA VM DETECTADA")
else:
    cols = st.columns(3)
    for i, vm_addr in enumerate(vms_list):
        ip = vm_addr.split(':')[0]
        nome = NOMES_VMS.get(ip, "Desconhecido")
        config = VMS.get(ip, {"apps": []})
        with cols[i % 3]:
            with st.container(border=True):
                is_up = query_prom(f'up{{instance="{vm_addr}"}}') == 1.0
                has_alert = verificar_alerta_apps(config["apps"], status_global_apps) if (is_up and config["apps"]) else False
                status_color = "%2339ff14" if is_up else "%23ff416c"
                alert_html = f"<img src='https://api.iconify.design/lucide/triangle-alert.svg?color=%23ff416c' width='24' style='animation: blink 1s infinite;'>" if has_alert else ""
                
                st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 10px; margin-bottom: 15px;'> <div style='display: flex; align-items: center; gap: 10px;'><img src='https://api.iconify.design/lucide/server.svg?color={status_color}' width='24'><span style='font-size: 1.2rem; font-weight: bold; color: #fff;'>{nome}</span></div>{alert_html}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='color: #64748b; font-size: 0.8rem; margin-bottom: 15px;'>{ip}</div>", unsafe_allow_html=True)

                if is_up:
                    cpu = query_prom(f'100 - (avg(rate(windows_cpu_time_total{{instance="{vm_addr}", mode="idle"}}[2m])) * 100)')
                    ram = query_prom(f'100 - ((windows_memory_available_bytes{{instance="{vm_addr}"}} / windows_memory_physical_total_bytes{{instance="{vm_addr}"}}) * 100)')
                    disco = query_prom(f'100 - ((windows_logical_disk_free_bytes{{instance="{vm_addr}", volume="C:"}} / windows_logical_disk_size_bytes{{instance="{vm_addr}", volume="C:"}}) * 100)')
                    
                    def get_metric_class(val): return "metric-val alert" if (val and val > 85) else "metric-val"
                    def format_val(val): return f"{val:.1f}%" if val is not None else "---"

                    st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; gap: 10px; margin-bottom: 20px;'>
                        <div class='metric-box'><div class='metric-label'>CPU</div><div class='{get_metric_class(cpu)}'>{format_val(cpu)}</div></div>
                        <div class='metric-box'><div class='metric-label'>RAM</div><div class='{get_metric_class(ram)}'>{format_val(ram)}</div></div>
                        <div class='metric-box'><div class='metric-label'>DISCO</div><div class='{get_metric_class(disco)}'>{format_val(disco)}</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    if config["apps"]:
                        btn_text = f"VERIFICAR ERRO [{len(config['apps'])}]" if has_alert else f"ABRIR CONSOLE [{len(config['apps'])}]"
                        if st.button(btn_text, key=f"btn_{ip}", use_container_width=True): mostrar_detalhes_apps(ip, config["apps"], status_global_apps)
                else:
                    st.error("VM OFFLINE")
                    