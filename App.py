import streamlit as st

# Oculta a barra de topo (header) e o rodapé da página
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from sqlalchemy import create_engine, text

# Configurações de Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

st.set_page_config(page_title="Solicitação de Compras - Fri On Line", page_icon="🛒", layout="wide")

# -----------------------------------------------------------------------------
# CONEXÃO COM BANCO DE DADOS (SUPABASE / POSTGRESQL)
# -----------------------------------------------------------------------------
def get_db_engine():
    db_url = st.secrets["postgres"]["url"]
    return create_engine(db_url)

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DE E-MAIL
# -----------------------------------------------------------------------------
EMAIL_DESTINO_ADMIN = "franciel.frionline@gmail.com"
EMAIL_REMETENTE = "franciel.frionline@gmail.com"

# Busca a senha do app Gmail preferencialmente dos Secrets do Streamlit Cloud
SENHA_EMAIL_APP = st.secrets.get("smtp", {}).get("password", "hieatxaemkrmfjmx")

def obter_hora_brasilia():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

def enviar_email(destino, assunto, corpo, caminho_anexo=None):
    if not SENHA_EMAIL_APP or SENHA_EMAIL_APP == "sua_senha_de_app_aqui":
        st.warning("⚠️ E-mail não enviado: A senha do aplicativo Google ainda não foi configurada.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = destino
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'html'))

        if caminho_anexo and os.path.exists(caminho_anexo):
            filename = os.path.basename(caminho_anexo)
            with open(caminho_anexo, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {filename}")
                msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, SENHA_EMAIL_APP)
        server.sendmail(EMAIL_REMETENTE, destino, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# Inicialização e Migração da Tabela no PostgreSQL
def init_db():
    engine = get_db_engine()
    sql_create = text('''
        CREATE TABLE IF NOT EXISTS solicitacoes (
            protocolo VARCHAR(30) PRIMARY KEY,
            data_pedido VARCHAR(30),
            requisitante TEXT,
            email_requisitante TEXT,
            setor TEXT,
            produtos_qtd TEXT,
            tipo_solicitacao TEXT,
            previsto_orcamento TEXT,
            valor_orcamento TEXT,
            justificativa TEXT,
            fornecedores TEXT,
            tem_rateio TEXT,
            detalhe_rateio TEXT,
            caminho_anexo TEXT,
            status VARCHAR(50),
            aprovado VARCHAR(20),
            data_compra VARCHAR(30),
            previsao_entrega VARCHAR(30),
            motivo_reprovacao TEXT DEFAULT '-',
            valor_final TEXT DEFAULT '-',
            forma_pagamento TEXT DEFAULT '-',
            historico_log TEXT DEFAULT ''
        );
    ''')
    with engine.begin() as conn:
        conn.execute(sql_create)

init_db()

def gerar_protocolo():
    engine = get_db_engine()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM solicitacoes;")).fetchone()
        count = res[0] + 1 if res else 1
    ano = datetime.now(ZoneInfo("America/Sao_Paulo")).year
    return f"FOL-{ano}-{count:04d}"

LISTA_SETORES = [
    "Administração", "Back Office Atendimento", "Back Office Comercial", 
    "Diretoria Gestão", "Diretoria Operacional", "Estoque Fri On Line", 
    "Frota Fri On Line", "Gerência Comercial", "Gerência de Atendimento", 
    "Gerência de Mercado", "Gerência de Rede", "Gerência de RH", 
    "Gerência de Suprimentos", "Gerência Financeira", "Gerência Operacional", 
    "Governança", "Jurídico", "Logística", "Marketing", "Ouvidoria", 
    "Presidência", "Recepção Fri On Line", "Supervisão de Atendimento", 
    "Supervisão de Compras", "Supervisão Financeira", "Supervisão Operacional", 
    "Suporte de Atendimento", "Unidades Fri On Line", "Unidades Noroeste"
]

LISTA_STATUS_OPCOES = ["Aguardando", "Em Cotação", "Cotação Enviada", "Comprado", "Compra não Autorizada"]

if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)

st.sidebar.title("📌 Menu Principal")
menu = st.sidebar.radio(
    "Navegação",
    ["📝 Nova Solicitação", "🔍 Consultar Protocolo", "📊 Dashboard & Gestão (Compras)"]
)

# -----------------------------------------------------------------------------
# 1. ABA: NOVA SOLICITAÇÃO (COLABORADOR)
# -----------------------------------------------------------------------------
if menu == "📝 Nova Solicitação":
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=180)
    with col_titulo:
        st.title("Solicitação de Compras (Geral)")
        st.write("Preencha as informações abaixo para gerar seu pedido de compra.")
        
    st.markdown("---")

    with st.form("form_compra", clear_on_submit=True):
        st.subheader("1. Identificação do Solicitante")
        col1, col2, col3 = st.columns(3)
        with col1:
            requisitante = st.text_input("Nome do Requisitante *")
        with col2:
            email_requisitante = st.text_input("E-mail do Requisitante *")
        with col3:
            setor = st.selectbox("Setor *", ["Selecione..."] + LISTA_SETORES)

        st.subheader("2. Detalhes dos Produtos / Serviços")
        produtos_qtd = st.text_area(
            "Produtos / Serviços Solicitados e Quantidades *",
            placeholder="Exemplo:\n1 - Monitor 24 polegadas\n5 - Mouse USB\n2 - Suporte de Notebook"
        )
        
        col4, col5 = st.columns(2)
        with col4:
            tipo_solicitacao = st.selectbox("Essa Solicitação é? *", ["Normal", "Urgente", "Apenas para Cotação"])
        with col5:
            previsto_orcamento = st.selectbox("Está Previsto em Orçamento? *", ["Sim", "Não"])

        valor_orcamento = st.text_input("Valor previsto em orçamento disponível (R$)", placeholder="Ex: R$ 1.500,00")

        st.subheader("3. Justificativa, Fornecedores e Anexos")
        justificativa = st.text_area("Justificativa da Compra *")
        fornecedores = st.text_area("Fornecedores sugeridos (opcional)")
        
        arquivo_anexo = st.file_uploader("Anexar Documento / Foto / Cotação (PDF, PNG, JPG, XLSX)", type=["pdf", "png", "jpg", "jpeg", "xlsx"])

        st.subheader("4. Rateio e Centro de Custo")
        tem_rateio = st.selectbox(
            "Essa aquisição tem Rateio no Centro de custo? *", 
            ["Não", "Outro"]
        )
        
        detalhe_rateio = st.text_area(
            "Especifique o valor ou porcentagem do rateio (Necessário caso selecione 'Outro'):",
            placeholder="Exemplo:\n50% TI (R$ 500,00) / 50% Financeiro (R$ 500,00)"
        )

        st.markdown("---")
        submitted = st.form_submit_button("🚀 Enviar Solicitação")
        
        if submitted:
            erros = []
            if not requisitante or not email_requisitante:
                erros.append("Nome e E-mail do Requisitante são obrigatórios.")
            if setor == "Selecione...":
                erros.append("Selecione um Setor válido.")
            if not produtos_qtd or not justificativa:
                erros.append("Informe os produtos e a justificativa.")
            if tem_rateio == "Outro" and not detalhe_rateio.strip():
                erros.append("Ao selecionar 'Outro' em Rateio, é obrigatório digitar os valores ou porcentagens correspondentes.")

            if erros:
                for erro in erros:
                    st.error(f"⚠️ {erro}")
            else:
                protocolo = gerar_protocolo()
                data_pedido = obter_hora_brasilia()
                log_inicial = f"[{data_pedido}] Solicitação criada pelo colaborador.\n"
                
                caminho_salvo = "-"
                if arquivo_anexo is not None:
                    caminho_salvo = os.path.join(UPLOADS_DIR, f"{protocolo}_{arquivo_anexo.name}")
                    with open(caminho_salvo, "wb") as f:
                        f.write(arquivo_anexo.getbuffer())

                engine = get_db_engine()
                sql_insert = text('''
                    INSERT INTO solicitacoes 
                    (protocolo, data_pedido, requisitante, email_requisitante, setor, produtos_qtd, tipo_solicitacao, 
                     previsto_orcamento, valor_orcamento, justificativa, fornecedores, tem_rateio, 
                     detalhe_rateio, caminho_anexo, status, aprovado, data_compra, previsao_entrega, motivo_reprovacao,
                     valor_final, forma_pagamento, historico_log)
                    VALUES (:protocolo, :data_pedido, :requisitante, :email_requisitante, :setor, :produtos_qtd, :tipo_solicitacao, 
                            :previsto_orcamento, :valor_orcamento, :justificativa, :fornecedores, :tem_rateio, 
                            :detalhe_rateio, :caminho_anexo, :status, :aprovado, :data_compra, :previsao_entrega, :motivo_reprovacao,
                            :valor_final, :forma_pagamento, :historico_log)
                ''')
                
                with engine.begin() as conn:
                    conn.execute(sql_insert, {
                        "protocolo": protocolo,
                        "data_pedido": data_pedido,
                        "requisitante": requisitante,
                        "email_requisitante": email_requisitante,
                        "setor": setor,
                        "produtos_qtd": produtos_qtd,
                        "tipo_solicitacao": tipo_solicitacao,
                        "previsto_orcamento": previsto_orcamento,
                        "valor_orcamento": valor_orcamento,
                        "justificativa": justificativa,
                        "fornecedores": fornecedores,
                        "tem_rateio": tem_rateio,
                        "detalhe_rateio": detalhe_rateio if tem_rateio == "Outro" else "-",
                        "caminho_anexo": caminho_salvo,
                        "status": "Aguardando",
                        "aprovado": "Pendente",
                        "data_compra": "-",
                        "previsao_entrega": "-",
                        "motivo_reprovacao": "-",
                        "valor_final": "-",
                        "forma_pagamento": "-",
                        "historico_log": log_inicial
                    })
                
                corpo_email_admin = f"""
                <h2>Nova Solicitação de Compra Recebida - Fri On Line</h2>
                <p><b>Protocolo:</b> {protocolo}</p>
                <p><b>Data do Pedido:</b> {data_pedido}</p>
                <p><b>Requisitante:</b> {requisitante} ({email_requisitante})</p>
                <p><b>Setor:</b> {setor}</p>
                <p><b>Tipo:</b> {tipo_solicitacao}</p>
                <p><b>Produtos:</b><br>{produtos_qtd.replace('\n', '<br>')}</p>
                <p><b>Rateio:</b> {tem_rateio} ({detalhe_rateio if tem_rateio == 'Outro' else 'N/A'})</p>
                <p><b>Justificativa:</b> {justificativa}</p>
                """
                enviar_email(EMAIL_DESTINO_ADMIN, f"[NOVO PEDIDO] Protocolo {protocolo} - {requisitante}", corpo_email_admin, caminho_salvo if caminho_salvo != "-" else None)

                corpo_email_usuario = f"""
                <h2>Solicitação de Compra Registrada - Fri On Line</h2>
                <p>Olá, {requisitante}!</p>
                <p>Sua solicitação de compra foi registrada com sucesso.</p>
                <p><b>Número do Protocolo:</b> {protocolo}</p>
                <p><b>Data:</b> {data_pedido}</p>
                <p>Você pode acompanhar o status do seu pedido na aba 'Consultar Protocolo' do nosso aplicativo.</p>
                """
                enviar_email(email_requisitante, f"Confirmação de Solicitação - Protocolo {protocolo}", corpo_email_usuario)

                st.success("✅ Solicitação enviada com sucesso!")
                st.info(f"📋 **Seu Número de Protocolo é:** `{protocolo}`")

# -----------------------------------------------------------------------------
# 2. ABA: CONSULTAR PROTOCOLO (COLABORADOR)
# -----------------------------------------------------------------------------
elif menu == "🔍 Consultar Protocolo":
    st.title("🔍 Acompanhar Status da Solicitação")
    
    proto_busca = st.text_input("Digite o Número do Protocolo (ex: FOL-2026-0001):").strip()
    
    if st.button("Buscar"):
        if proto_busca:
            engine = get_db_engine()
            query = text("SELECT * FROM solicitacoes WHERE UPPER(protocolo) = :protocolo")
            with engine.connect() as conn:
                df = pd.read_sql_query(query, conn, params={"protocolo": proto_busca.upper()})
            
            if not df.empty:
                item = df.iloc[0]
                st.subheader(f"Protocolo: {item['protocolo']}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Data do Pedido", item['data_pedido'])
                c2.metric("Status Atual", item['status'])
                c3.metric("Compra Aprovada?", item['aprovado'])
                
                st.markdown("---")
                st.write(f"**Requisitante:** {item['requisitante']} ({item['email_requisitante']}) | **Setor:** {item['setor']}")
                st.write(f"**Produtos / Serviços:**\n{item['produtos_qtd']}")
                st.write(f"**Rateio:** {item['tem_rateio']} ({item['detalhe_rateio']})")
                
                if item['aprovado'] == "Sim":
                    st.success(f"📅 **Data da Compra:** {item['data_compra']} | 🚚 **Previsão de Entrega:** {item['previsao_entrega']}")
                elif item['aprovado'] == "Não" or item['status'] == "Compra não Autorizada":
                    st.error(f"❌ **Compra Não Autorizada.**")
                    st.warning(f"**Motivo da Não Aprovação:** {item.get('motivo_reprovacao', 'Não especificado')}")
                else:
                    st.info("⏳ **Solicitação em análise pelo setor de compras.**")
            else:
                st.error("Protocolo não encontrado.")

# -----------------------------------------------------------------------------
# 3. ABA: DASHBOARD & PAINEL DE GESTÃO (APENAS ADMINISTRADOR)
# -----------------------------------------------------------------------------
elif menu == "📊 Dashboard & Gestão (Compras)":
    st.title("📊 Painel de Gestão e Métricas de Compras")
    
    senha = st.sidebar.text_input("Senha do Administrador", type="password")
    if senha == "Frion@2603":
        st.sidebar.success("Acesso Autorizado")
        
        engine = get_db_engine()
        with engine.connect() as conn:
            df_raw = pd.read_sql_query(text("SELECT * FROM solicitacoes ORDER BY protocolo DESC;"), conn)
        
        if not df_raw.empty:
            df_raw['data_dt'] = pd.to_datetime(df_raw['data_pedido'].str.slice(0, 10), format='%d/%m/%Y', errors='coerce')
            
            agora = pd.to_datetime(datetime.now(ZoneInfo("America/Sao_Paulo")).date())
            df_raw['dias_parado'] = (agora - df_raw['data_dt']).dt.days
            pendentes_antigos = df_raw[(df_raw['status'] == 'Aguardando') & (df_raw['dias_parado'] >= 2)]
            
            if not pendentes_antigos.empty:
                st.warning(
                    f"⏰ **LEMBRETE DE PENDÊNCIAS:** Você tem **{len(pendentes_antigos)} solicitação(ões)** com status 'Aguardando' há mais de 2 dias sem alteração!\n\n" +
                    " Protocolos: " + ", ".join(f"`{p}`" for p in pendentes_antigos['protocolo'].tolist())
                )

            st.subheader("📈 Visão Geral dos Pedidos")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total de Pedidos", len(df_raw))
            col_m2.metric("Aguardando Cotação", len(df_raw[df_raw['status'] == 'Aguardando']))
            col_m3.metric("Compras Aprovadas", len(df_raw[df_raw['aprovado'] == 'Sim']))
            col_m4.metric("Compras Recusadas", len(df_raw[(df_raw['aprovado'] == 'Não') | (df_raw['status'] == 'Compra não Autorizada')]))
            
            st.write("**Filtrar lista rápida por categoria:**")
            col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
            
            if "filtro_status" not in st.session_state:
                st.session_state.filtro_status = "Todos"

            def selecionar_filtro(status_nome):
                st.session_state.filtro_status = status_nome

            if col_b1.button("📋 Todos"):
                selecionar_filtro("Todos")
            if col_b2.button("⏳ Aguardando Cotação"):
                selecionar_filtro("Aguardando")
            if col_b3.button("🔄 Em Cotação"):
                selecionar_filtro("Em Cotação")
            if col_b4.button("✅ Compras Aprovadas"):
                selecionar_filtro("Aprovados")
            if col_b5.button("❌ Compras Recusadas"):
                selecionar_filtro("Recusados")

            st.markdown("---")

            st.subheader("📊 Gráfico de Solicitações por Setor")
            setores_count = df_raw['setor'].value_counts()
            st.bar_chart(setores_count)

            st.markdown("---")
            
            st.subheader("📥 Exportar Relatórios e Selecionar Período")
            st.write("Por padrão, a tabela exporta **todo o histórico**. Se desejar um período específico, altere as datas abaixo:")
            
            col_f1, col_f2 = st.columns(2)
            datas_validas = df_raw['data_dt'].dropna()
            min_date = datas_validas.min().date() if not datas_validas.empty else date.today()
            max_date = datas_validas.max().date() if not datas_validas.empty else date.today()
            
            dt_inicio = col_f1.date_input("Data Inicial", min_date, format="DD/MM/YYYY")
            dt_fim = col_f2.date_input("Data Final", max_date, format="DD/MM/YYYY")
            
            df_export = df_raw[(df_raw['data_dt'].dt.date >= dt_inicio) & (df_raw['data_dt'].dt.date <= dt_fim)].copy()
            if df_export.empty:
                df_export = df_raw.copy()
            
            col_exp1, col_exp2 = st.columns(2)
            csv_data = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            col_exp1.download_button(
                label="💾 Baixar Relatório em CSV (Excel)",
                data=csv_data,
                file_name="relatorio_compras.csv",
                mime="text/csv"
            )
            
            html_table = df_export.to_html(index=False)
            col_exp2.download_button(
                label="📊 Baixar Relatório em .XLS (Excel)",
                data=html_table,
                file_name="relatorio_compras.xls",
                mime="application/vnd.ms-excel"
            )

            st.markdown("---")
            
            st.subheader(f"📋 Solicitações Registradas - Categoria Filtrada: ({st.session_state.filtro_status})")
            
            df_exibicao = df_raw.copy()
            if st.session_state.filtro_status == "Aguardando":
                df_exibicao = df_exibicao[df_exibicao['status'] == 'Aguardando']
            elif st.session_state.filtro_status == "Em Cotação":
                df_exibicao = df_exibicao[df_exibicao['status'] == 'Em Cotação']
            elif st.session_state.filtro_status == "Aprovados":
                df_exibicao = df_exibicao[df_exibicao['aprovado'] == 'Sim']
            elif st.session_state.filtro_status == "Recusados":
                df_exibicao = df_exibicao[(df_exibicao['aprovado'] == 'Não') | (df_exibicao['status'] == 'Compra não Autorizada')]

            setor_pesquisa = st.selectbox(
                "🔍 Pesquisar/Filtrar por Setor Específico:",
                ["Todos os Setores"] + LISTA_SETORES
            )
            
            if setor_pesquisa != "Todos os Setores":
                df_exibicao = df_exibicao[df_exibicao['setor'] == setor_pesquisa]

            st.write(f"Exibindo **{len(df_exibicao)}** solicitação(ões):")
            
            for _, row in df_exibicao.iterrows():
                tag_urgencia = "🟢 Normal"
                if row['tipo_solicitacao'] == "Urgente":
                    tag_urgencia = "🔴 URGENTE"
                elif row['tipo_solicitacao'] == "Apenas para Cotação":
                    tag_urgencia = "🟡 Cotação"
                
                status_icon = "⏳" if row['status'] == "Aguardando" else "🔄"
                if row['aprovado'] == "Sim" or row['status'] == "Comprado":
                    status_icon = "✅"
                elif row['aprovado'] == "Não" or row['status'] == "Compra não Autorizada":
                    status_icon = "❌"

                titulo_cartao = f"{status_icon} [{row['protocolo']}] - {row['requisitante']} ({row['setor']}) | {tag_urgencia} | Status: {row['status']}"
                
                with st.expander(titulo_cartao):
                    col_card1, col_card2 = st.columns(2)
                    with col_card1:
                        st.markdown(f"**Data do Pedido:** {row['data_pedido']}")
                        st.markdown(f"**E-mail:** {row['email_requisitante']}")
                        st.markdown(f"**Previsto em Orçamento?:** {row['previsto_orcamento']} ({row['valor_orcamento']})")
                        st.markdown(f"**Rateio:** {row['tem_rateio']} ({row['detalhe_rateio']})")
                    with col_card2:
                        st.markdown(f"**Status Atual:** {row['status']}")
                        st.markdown(f"**Compra Aprovada?:** {row['aprovado']}")
                        st.markdown(f"**Data da Compra:** {row['data_compra']} | **Previsão:** {row['previsao_entrega']}")
                        st.markdown(f"**Valor Final:** {row.get('valor_final', '-')} | **Forma Pagto:** {row.get('forma_pagamento', '-')}")
                        if row['aprovado'] == "Não" or row['status'] == "Compra não Autorizada":
                            st.markdown(f"**Motivo da Recusa:** {row['motivo_reprovacao']}")
                    
                    st.markdown(f"**📦 Produtos / Serviços Solicitados:**\n{row['produtos_qtd']}")
                    st.markdown(f"**📝 Justificativa:**\n{row['justificativa']}")
                    
                    if row['fornecedores']:
                        st.markdown(f"**🔗 Fornecedores Sugeridos / Links:**\n{row['fornecedores']}")
                    
                    if row.get('historico_log'):
                        st.markdown(f"**📜 Histórico de Alterações:**\n```text\n{row['historico_log']}\n```")

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if row['caminho_anexo'] != "-" and os.path.exists(row['caminho_anexo']):
                            with open(row['caminho_anexo'], "rb") as file:
                                st.download_button(
                                    label="📎 Baixar Anexo",
                                    data=file,
                                    file_name=os.path.basename(row['caminho_anexo']),
                                    key=f"btn_anexo_{row['protocolo']}"
                                )
                    with col_btn2:
                        if st.button(f"📧 Reenviar Notificação E-mail", key=f"reenviar_{row['protocolo']}"):
                            corpo_reenvio = f"""
                            <h2>Notificação de Acompanhamento - Fri On Line</h2>
                            <p>Olá, <b>{row['requisitante']}</b>!</p>
                            <p><b>Protocolo:</b> {row['protocolo']}</p>
                            <p><b>Status Atual:</b> {row['status']}</p>
                            <p><b>Aprovado?:</b> {row['aprovado']}</p>
                            """
                            enviar_email(row['email_requisitante'], f"[LEMBRETE] Pedido {row['protocolo']}", corpo_reenvio)
                            st.success("E-mail reenviado com sucesso!")

            st.markdown("---")

            # -----------------------------------------------------------------
            # ATUALIZAR PEDIDO E STATUS
            # -----------------------------------------------------------------
            st.subheader("✏️ Atualizar Pedido e Status")
            
            opcoes_protocolo = ["Selecione um protocolo..."] + df_raw["protocolo"].tolist()

            protocolo_sel = st.selectbox(
                "Selecione o Protocolo para Editar:",
                opcoes_protocolo,
                key="protocolo_selecionado"
            )

            if protocolo_sel != "Selecione um protocolo...":
                dado_atual = df_raw[df_raw["protocolo"] == protocolo_sel].iloc[0]

                if dado_atual['caminho_anexo'] != "-" and os.path.exists(dado_atual['caminho_anexo']):
                    with open(dado_atual['caminho_anexo'], "rb") as file:
                        st.download_button(
                            label="📎 Baixar Anexo deste Pedido",
                            data=file,
                            file_name=os.path.basename(dado_atual['caminho_anexo']),
                            key="btn_anexo_editar"
                        )

                with st.form("form_atualizar"):
                    c_a, c_b = st.columns(2)
                    with c_a:
                        idx_status = LISTA_STATUS_OPCOES.index(dado_atual['status']) if dado_atual['status'] in LISTA_STATUS_OPCOES else 0
                        novo_status = st.selectbox("Status do Pedido", LISTA_STATUS_OPCOES, index=idx_status)
                    with c_b:
                        idx_aprov = ["Pendente", "Sim", "Não"].index(dado_atual['aprovado']) if dado_atual['aprovado'] in ["Pendente", "Sim", "Não"] else 0
                        nova_aprovacao = st.selectbox("Compra Aprovada?", ["Pendente", "Sim", "Não"], index=idx_aprov)
                    
                    c_c, c_d = st.columns(2)
                    with c_c:
                        dt_compra = st.text_input("Data da Compra (DD/MM/AAAA)", value=dado_atual['data_compra'])
                    with c_d:
                        dt_entrega = st.text_input("Previsão de Entrega (DD/MM/AAAA)", value=dado_atual['previsao_entrega'])
                    
                    c_e, c_f = st.columns(2)
                    with c_e:
                        v_final = st.text_input("Valor Final da Compra (R$)", value=dado_atual.get('valor_final', '-'))
                    with c_f:
                        f_pagto = st.text_input("Forma de Pagamento", value=dado_atual.get('forma_pagamento', '-'))

                    motivo_reprovacao = st.text_area(
                        "Motivo da Não Aprovação (Obrigatório se selecionou 'Não' em Compra Aprovada ou 'Compra não Autorizada' no Status):",
                        value=dado_atual.get('motivo_reprovacao', '') if dado_atual.get('motivo_reprovacao') != '-' else ''
                    )

                    if st.form_submit_button("Salvar Alterações e Notificar Requisitante"):
                        e_reprovado = (nova_aprovacao == "Não") or (novo_status == "Compra não Autorizada")
                        
                        if e_reprovado and not motivo_reprovacao.strip():
                            st.error("⚠️ Digite o motivo da não aprovação para prosseguir.")
                        else:
                            motivo_salvar = motivo_reprovacao.strip() if e_reprovado else "-"
                            if novo_status == "Compra não Autorizada":
                                nova_aprovacao = "Não"
                            elif novo_status == "Comprado" and nova_aprovacao == "Pendente":
                                nova_aprovacao = "Sim"

                            hora_atual = obter_hora_brasilia()
                            novo_log_item = f"[{hora_atual}] Status: {novo_status} | Aprovado: {nova_aprovacao}\n"
                            log_atualizado = str(dado_atual.get('historico_log', '')) + novo_log_item

                            engine = get_db_engine()
                            sql_update = text('''
                                UPDATE solicitacoes 
                                SET status = :status, aprovado = :aprovado, data_compra = :data_compra, previsao_entrega = :previsao_entrega, 
                                    motivo_reprovacao = :motivo_reprovacao, valor_final = :valor_final, forma_pagamento = :forma_pagamento, historico_log = :historico_log
                                WHERE protocolo = :protocolo
                            ''')
                            with engine.begin() as conn:
                                conn.execute(sql_update, {
                                    "status": novo_status,
                                    "aprovado": nova_aprovacao,
                                    "data_compra": dt_compra,
                                    "previsao_entrega": dt_entrega,
                                    "motivo_reprovacao": motivo_salvar,
                                    "valor_final": v_final,
                                    "forma_pagamento": f_pagto,
                                    "historico_log": log_atualizado,
                                    "protocolo": protocolo_sel
                                })
                            
                            if nova_aprovacao == "Não":
                                corpo_email_usuario = f"""
                                <h2>Atualização sobre o seu Pedido de Compra - Fri On Line</h2>
                                <p>Olá, <b>{dado_atual['requisitante']}</b>!</p>
                                <p>Sua solicitação de compra <b>(Protocolo {protocolo_sel})</b> foi analisada e <b>NÃO FOI APROVADA</b>.</p>
                                <p><b>Motivo da Não Aprovação:</b><br>{motivo_salvar}</p>
                                <p>Caso tenha dúvidas, entre em contato com o setor de suprimentos/logística.</p>
                                """
                            else:
                                corpo_email_usuario = f"""
                                <h2>Atualização sobre o seu Pedido de Compra - Fri On Line</h2>
                                <p>Olá, <b>{dado_atual['requisitante']}</b>!</p>
                                <p><b>Protocolo:</b> {protocolo_sel}</p>
                                <p><b>Status Atual:</b> {novo_status}</p>
                                <p><b>Compra Aprovada?:</b> {nova_aprovacao}</p>
                                <p><b>Data da Compra:</b> {dt_compra}</p>
                                <p><b>Previsão de Entrega:</b> {dt_entrega}</p>
                                """
                                
                            enviar_email(dado_atual['email_requisitante'], f"[ATUALIZAÇÃO] Pedido {protocolo_sel}", corpo_email_usuario)

                            if "protocolo_selecionado" in st.session_state:
                                del st.session_state["protocolo_selecionado"]

                            st.success(f"Protocolo {protocolo_sel} atualizado e e-mail enviado com sucesso!")
                            st.rerun()
            else:
                st.info("👆 Selecione um protocolo na caixa acima para abrir e atualizar os dados do pedido.")
        else:
            st.info("Nenhuma solicitação encontrada.")
    else:
        st.warning("Insira a senha do administrador para acessar o painel de compras.")
