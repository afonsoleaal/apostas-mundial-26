import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURAÇÃO BASE E LIGAÇÃO À NUVEM
# ==========================================
st.set_page_config(page_title="Dashboard Apostas Mundial", layout="wide")

# 🚨 !!! COLA AQUI O ID DA TUA FOLHA DO GOOGLE SHEETS !!! 🚨
ID_DA_FOLHA = "1M_G3Y4u-G6TDZu8VHNdE4QOU5I5uv7nfVBbKyc__XlI"
URL_DA_FOLHA = f"https://docs.google.com/spreadsheets/d/{ID_DA_FOLHA}/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Trocámos o ttl=0 para ttl=15 (O site memoriza o Excel durante 15 segundos)
        df_users = conn.read(spreadsheet=URL_DA_FOLHA, worksheet="Utilizadores", ttl=15)
        df_bets = conn.read(spreadsheet=URL_DA_FOLHA, worksheet="Apostas", ttl=15)
        return df_users, df_bets
    except Exception as e:
        st.warning("A sincronizar com a Google... Aguarda uns segundos e recarrega a página.")
        return pd.DataFrame(), pd.DataFrame()

df_utilizadores, df_todas_apostas = carregar_dados()

# Limpeza e Garantia de Colunas (Prevenção de erros caso a folha esteja desatualizada)
if not df_todas_apostas.empty:
    df_todas_apostas = df_todas_apostas.dropna(subset=["Odd", "Estado"])
    if "Tipo de Aposta" not in df_todas_apostas.columns:
        df_todas_apostas["Tipo de Aposta"] = "Simples"

if df_todas_apostas.empty or "Apostador" not in df_todas_apostas.columns:
    df_todas_apostas = pd.DataFrame(columns=["Apostador", "Tipo de Aposta", "Jogo", "Mercado", "Odd", "Aposta (€)", "Estado", "Retorno (€)"])


# ==========================================
# 2. SISTEMA DE LOGIN DE SESSÃO
# ==========================================
if 'user_logado' not in st.session_state:
    st.session_state.user_logado = None

if st.session_state.user_logado is None:
    st.title("🔐 Acesso ao Portal - Mundial 2026")
    if not df_utilizadores.empty:
        with st.form("form_login"):
            user_input = st.selectbox("Quem és tu?", df_utilizadores["Apostador"].tolist())
            pin_input = st.text_input("Insere o teu PIN de 4 dígitos", type="password")
            btn_login = st.form_submit_button("Iniciar Sessão", use_container_width=True)
            
            if btn_login:
                pin_real = str(df_utilizadores[df_utilizadores["Apostador"] == user_input]["PIN"].values[0]).replace('.0', '')
                if str(pin_input).strip() == pin_real.strip():
                    st.session_state.user_logado = user_input
                    st.rerun()
                else:
                    st.error("PIN incorreto!")
    st.stop()

usuario_atual = st.session_state.user_logado

# ==========================================
# 3. BARRA LATERAL (NAVEGAÇÃO GLOBAL & SEGURANÇA)
# ==========================================
st.sidebar.header(f"👤 Sessão: {usuario_atual}")
if st.sidebar.button("Sair / Logout"):
    st.session_state.user_logado = None
    st.rerun()

st.sidebar.divider()

lista_apostadores = df_utilizadores["Apostador"].tolist() if not df_utilizadores.empty else [usuario_atual]
perfil_selecionado = st.sidebar.selectbox("📋 Visualizar Perfil de:", lista_apostadores, index=lista_apostadores.index(usuario_atual) if usuario_atual in lista_apostadores else 0)

if perfil_selecionado == usuario_atual:
    st.sidebar.divider()
    st.sidebar.subheader("➕ Adicionar Nova Aposta")
    
    if 'limpa_campos' not in st.session_state: st.session_state.limpa_campos = 0
    k = st.session_state.limpa_campos

    tipo_aposta = st.sidebar.radio("Tipo de Aposta", ["Simples", "Múltipla"], horizontal=True, key=f"tipo_{k}")

    if tipo_aposta == "Múltipla":
        num_jogos = st.sidebar.number_input("Quantos jogos na Múltipla?", min_value=2, max_value=10, value=2, key=f"num_{k}")
        jogos, mercados = [], []
        for i in range(num_jogos):
            col1, col2 = st.sidebar.columns(2)
            with col1: jogos.append(st.text_input(f"Jogo {i+1}", key=f"j_{i}_{k}"))
            with col2: mercados.append(st.text_input(f"Mercado {i+1}", key=f"m_{i}_{k}"))
        novo_jogo = " | ".join(filter(None, jogos))
        novo_mercado = " | ".join(filter(None, mercados))
    else:
        novo_jogo = st.sidebar.text_input("Jogo", key=f"jogo_{k}")
        novo_mercado = st.sidebar.text_input("Mercado", key=f"mercado_{k}")

    nova_odd = st.sidebar.number_input("Odd Total", min_value=1.00, step=0.01, format="%.2f", value=1.00, key=f"odd_{k}")
    nova_aposta = st.sidebar.number_input("Aposta (€)", min_value=0.50, step=0.50, format="%.2f", value=0.50, key=f"aposta_{k}")
    novo_estado = st.sidebar.selectbox("Estado", ["Pendente", "Ganha", "Perdida"], key=f"estado_{k}")

    retorno_potencial = nova_odd * nova_aposta
    st.sidebar.info(f"💰 Retorno Potencial: **{retorno_potencial:.2f} €**")

    if novo_estado == "Ganha": novo_retorno = retorno_potencial
    else: novo_retorno = 0.00

    if st.sidebar.button("Guardar Aposta na Nuvem", use_container_width=True):
        if novo_jogo and nova_odd >= 1:
            nova_linha = pd.DataFrame([{
                "Apostador": usuario_atual,
                "Tipo de Aposta": tipo_aposta, # <-- GUARDADO AQUI
                "Jogo": novo_jogo,
                "Mercado": novo_mercado,
                "Odd": nova_odd,
                "Aposta (€)": nova_aposta,
                "Estado": novo_estado,
                "Retorno (€)": novo_retorno
            }])
            df_atualizado = pd.concat([df_todas_apostas, nova_linha], ignore_index=True)
            conn.update(spreadsheet=URL_DA_FOLHA, worksheet="Apostas", data=df_atualizado)
            st.session_state.limpa_campos += 1
            st.rerun()
        else:
            st.sidebar.error("Preenche os campos corretamente!")
else:
    st.sidebar.warning("🔒 Estás em modo de leitura.")

# ==========================================
# 4. PÁGINA PRINCIPAL (DASHBOARD DINÂMICO & CARTÕES UI)
# ==========================================
st.title("🏆 O Nosso Placard - Mundial 2026")
st.header(f"Estatísticas de: {perfil_selecionado}")

df_perfil = df_todas_apostas[df_todas_apostas["Apostador"] == perfil_selecionado]

if not df_perfil.empty:
    total_apostado = pd.to_numeric(df_perfil["Aposta (€)"]).sum()
    apostas_resolvidas = df_perfil[df_perfil["Estado"].isin(["Ganha", "Perdida"])]
    lucro_prejuizo = pd.to_numeric(apostas_resolvidas["Retorno (€)"]).sum() - pd.to_numeric(apostas_resolvidas["Aposta (€)"]).sum()
    total_ganhas = len(df_perfil[df_perfil["Estado"] == "Ganha"])
    total_resolvidas = len(apostas_resolvidas)
    win_rate = (total_ganhas / total_resolvidas * 100) if total_resolvidas > 0 else 0
else:
    total_apostado, lucro_prejuizo, win_rate = 0.0, 0.0, 0.0

col1, col2, col3 = st.columns(3)
col1.metric("Total Apostado", f"{total_apostado:.2f} €")
col2.metric("Lucro / Prejuízo", f"{lucro_prejuizo:.2f} €", delta=f"{lucro_prejuizo:.2f} €")
col3.metric("Win Rate", f"{win_rate:.1f} %")

st.divider()
st.subheader("📝 Histórico de Apostas")

if not df_perfil.empty:
    cartoes_html = ""
    
    # Inverter para mostrar as mais recentes primeiro
    df_perfil_reversed = df_perfil.iloc[::-1]
    
    for idx, row in df_perfil_reversed.iterrows():
        tipo = str(row.get("Tipo de Aposta", "Simples"))
        estado = str(row["Estado"])
        jogos = str(row["Jogo"]).split(" | ")
        mercados = str(row["Mercado"]).split(" | ")
        
        # Configurar Cores e Badges dependendo do Estado
        if estado == "Ganha":
            cor_borda = "#4ade80" # Verde
            badge = f"<span style='background-color:rgba(74, 222, 128, 0.15); color:#4ade80; border: 1px solid #4ade80; padding:4px 12px; border-radius:6px; font-weight:800; font-size:11px; letter-spacing: 1px;'>✓ GANHO</span>"
            valor_rodape = f"<span style='color:#4ade80'>+ {float(row['Retorno (€)']):.2f}€</span>"
            titulo_rodape = "GANHO"
        elif estado == "Perdida":
            cor_borda = "#f87171" # Vermelho
            badge = f"<span style='background-color:rgba(248, 113, 113, 0.15); color:#f87171; border: 1px solid #f87171; padding:4px 12px; border-radius:6px; font-weight:800; font-size:11px; letter-spacing: 1px;'>✗ PERDIDO</span>"
            valor_rodape = f"<span style='color:#f87171'>0.00€</span>"
            titulo_rodape = "GANHO"
        else: # Pendente
            cor_borda = "#fbbf24" # Amarelo
            badge = f"<span style='background-color:rgba(251, 191, 36, 0.15); color:#fbbf24; border: 1px solid #fbbf24; padding:4px 12px; border-radius:6px; font-weight:800; font-size:11px; letter-spacing: 1px;'>⏳ PENDENTE</span>"
            valor_rodape = f"<span style='color:#9ca3af'>{float(row['Odd']) * float(row['Aposta (€)']):.2f}€</span>"
            titulo_rodape = "POTENCIAL"

        titulo_cartao = f"MÚLTIPLA ({len(jogos)})" if tipo == "Múltipla" else "SIMPLES"
        
        # Aqui está o truque: escrever o HTML todo sem quebras de linha/indentações que confundem o Markdown
        cartao = f"<div style='background-color: #151b2b; border-radius: 12px; border-left: 5px solid {cor_borda}; margin-bottom: 24px; padding: 24px; font-family: sans-serif; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); border-top: 1px solid #1e293b; border-right: 1px solid #1e293b; border-bottom: 1px solid #1e293b;'>"
        cartao += f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #1e293b; padding-bottom: 15px;'><div style='color: #64748b; font-size: 13px; font-weight: 800; letter-spacing: 1.5px;'>{titulo_cartao}</div><div>{badge}</div></div>"
        
        for i in range(len(jogos)):
            j = jogos[i]
            m = mercados[i] if i < len(mercados) else ""
            cartao += f"<div style='display: flex; align-items: center; margin-bottom: 16px;'><div style='font-size: 22px; margin-right: 18px; color: #f59e0b;'>⚽</div><div><div style='color: #f8fafc; font-weight: 700; font-size: 16px; margin-bottom: 2px;'>{j}</div><div style='color: #94a3b8; font-size: 14px;'>{m}</div></div></div>"

        cartao += f"<div style='display: flex; justify-content: space-between; background-color: #0f131f; padding: 18px; border-radius: 8px; margin-top: 24px; text-align: center; border: 1px solid #1e293b;'><div style='flex: 1; border-right: 1px solid #1e293b;'><div style='color: #64748b; font-size: 11px; font-weight: 800; margin-bottom: 6px; letter-spacing: 1px;'>ODD TOTAL</div><div style='color: #f8fafc; font-weight: 800; font-size: 18px;'>{float(row['Odd']):.2f}</div></div><div style='flex: 1; border-right: 1px solid #1e293b;'><div style='color: #64748b; font-size: 11px; font-weight: 800; margin-bottom: 6px; letter-spacing: 1px;'>VALOR APOSTADO</div><div style='color: #f8fafc; font-weight: 800; font-size: 18px;'>{float(row['Aposta (€)']):.2f}€</div></div><div style='flex: 1;'><div style='color: #64748b; font-size: 11px; font-weight: 800; margin-bottom: 6px; letter-spacing: 1px;'>{titulo_rodape}</div><div style='font-weight: 800; font-size: 18px;'>{valor_rodape}</div></div></div></div>"
        
        cartoes_html += cartao

    st.markdown(cartoes_html, unsafe_allow_html=True)
else:
    st.info("Ainda não existem apostas registadas neste perfil.")

# ==========================================
# 5. RESOLVER PENDENTES (APENAS DO PRÓPRIO)
# ==========================================
if perfil_selecionado == usuario_atual and not df_perfil.empty:
    df_pendentes = df_perfil[df_perfil["Estado"] == "Pendente"]
    
    if not df_pendentes.empty:
        st.divider()
        st.subheader("✏️ Resolver as minhas Apostas Pendentes")
        
        opcoes_pendentes = []
        indices_reais = []
        for idx, row in df_pendentes.iterrows():
            tipo_txt = row.get("Tipo de Aposta", "Simples")
            # Mostrar os jogos de forma abreviada no menu dropdown
            jogos_abreviados = str(row['Jogo']).replace(" | ", " + ")
            if len(jogos_abreviados) > 40: jogos_abreviados = jogos_abreviados[:40] + "..."
            
            opcoes_pendentes.append(f"[{tipo_txt.upper()}] {jogos_abreviados} - {float(row['Aposta (€)']):.2f}€")
            indices_reais.append(idx)
            
        col_sel, col_est, col_btn = st.columns([2, 1, 1])
        with col_sel:
            aposta_selecionada = st.selectbox("Escolhe a aposta para fechar:", range(len(opcoes_pendentes)), format_func=lambda x: opcoes_pendentes[x])
        with col_est:
            novo_status_pendente = st.selectbox("Resultado Final:", ["Ganha", "Perdida"])
        with col_btn:
            st.write(""); st.write("")
            if st.button("Atualizar na Nuvem", use_container_width=True):
                idx_original_na_bd = indices_reais[aposta_selecionada]
                
                df_todas_apostas.at[idx_original_na_bd, "Estado"] = novo_status_pendente
                odd_real = float(df_todas_apostas.at[idx_original_na_bd, "Odd"])
                aposta_real = float(df_todas_apostas.at[idx_original_na_bd, "Aposta (€)"])
                
                if novo_status_pendente == "Ganha":
                    df_todas_apostas.at[idx_original_na_bd, "Retorno (€)"] = odd_real * aposta_real
                else:
                    df_todas_apostas.at[idx_original_na_bd, "Retorno (€)"] = 0.00
                
                conn.update(spreadsheet=URL_DA_FOLHA, worksheet="Apostas", data=df_todas_apostas)
                st.rerun()
