import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Configurações de Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "compras.db")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

st.set_page_config(page_title="Solicitação de Compras - Fri On Line", page_icon="🛒", layout="wide")

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DE E-MAIL
# -----------------------------------------------------------------------------
EMAIL_DESTINO_ADMIN = "franciel.frionline@gmail.com"
EMAIL_REMETENTE = "franciel.frionline@gmail.com"
SENHA_EMAIL_APP = "hieatxaemkrmfjmx"

# Função para obter a hora exata no Fuso Horário de Brasília
def obter_hora_brasilia():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

# Função para envio de e-mails via SMTP Gmail
def enviar_email(destino, assunto, corpo, caminho_anexo=None):
    if not SENHA_EMAIL_APP or SENHA_EMAIL_APP == "sua_senha_de_app_aqui":
        st.warning("⚠️ E-mail não enviado: A senha do aplicativo Google ainda não foi configurada no código.")
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

# Inicialização e Migração do Banco de Dados
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes (
            protocolo TEXT PRIMARY KEY,
            data_pedido TEXT,
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
            status TEXT,
            aprovado TEXT,
            data_compra TEXT,
            previsao_entrega TEXT,
            motivo_reprovacao TEXT
        )
    ''')
    
    # Adiciona a coluna 'motivo_reprovacao' se a tabela já existia sem ela
    c.execute("PRAGMA table_info(solicitacoes)")
    colunas = [coluna[1] for coluna in c.fetchall()]
    if "motivo_reprovacao" not in colunas:
        c.execute("ALTER TABLE solicitacoes ADD COLUMN motivo_reprovacao TEXT DEFAULT '-'")
        
    conn.commit()
    conn.close()

init_db()

def gerar_protocolo():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM solicitacoes")
    count = c.fetchone()[0] + 1
    conn.close()
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

# Exibição da Logo no Topo do Menu Lateral
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
                
                caminho_salvo = "-"
                if arquivo_anexo is not None:
                    caminho_salvo = os.path.join(UPLOADS_DIR, f"{protocolo}_{arquivo_anexo.name}")
                    with open(caminho_salvo, "wb") as f:
                        f.write(arquivo_anexo.getbuffer())

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO solicitacoes 
                    (protocolo, data_pedido, requisitante, email_requisitante, setor, produtos_qtd, tipo_solicitacao, 
                     previsto_orcamento, valor_orcamento, justificativa, fornecedores, tem_rateio, 
                     detalhe_rateio, caminho_anexo, status, aprovado, data_compra, previsao_entrega, motivo_reprovacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (protocolo, data_pedido, requisitante, email_requisitante, setor, produtos_qtd, tipo_solicitacao, 
                      previsto_orcamento, valor_orcamento, justificativa, fornecedores, tem_rateio, 
                      detalhe_rateio if tem_rateio == "Outro" else "-", caminho_salvo, "Aguardando", "Pendente", "-", "-", "-"))
                conn.commit()
                conn.close()
                
                # Notificação por E-mail para a Logística
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

                # Confirmação por E-mail para o Colaborador
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
            conn = sqlite3.connect(DB_PATH)
            query = "SELECT * FROM solicitacoes WHERE protocolo = ?"
            df = pd.read_sql_query(query, conn, params=(proto_busca,))
            conn.close()
            
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
                elif item['aprovado'] == "Não":
    st.error(f"❌ **Compra Não Autorizada.**")
    st.warning(f"<b>Motivo da Não Aprovação:</b> {item.get('motivo_reprovacao', 'Não especificado')}")
                else:
                    st.info("⏳ **Solicitação em análise pelo setor de compras.**")
            else:
                st.error("Protocolo não encontrado.")

# -----------------------------------------------------------------------------
# 3. ABA: DASHBOARD & PAINEL DE GESTÃO (VOCÊ - COMPRAS)
# -----------------------------------------------------------------------------
elif menu == "📊 Dashboard & Gestão (Compras)":
    st.title("📊 Painel de Gestão e Métricas de Compras")
    
    senha = st.sidebar.text_input("Senha do Administrador", type="password")
    if senha == "Frion@2603":
        st.sidebar.success("Acesso Autorizado")
        
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM solicitacoes", conn)
        conn.close()
        
        if not df.empty:
            st.subheader("📈 Visão Geral dos Pedidos")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total de Pedidos", len(df))
            col_m2.metric("Aguardando Cotação", len(df[df['status'] == 'Aguardando']))
            col_m3.metric("Compras Aprovadas", len(df[df['aprovado'] == 'Sim']))
            col_m4.metric("Compras Recusadas", len(df[df['aprovado'] == 'Não']))
            
            st.markdown("---")
            
            st.subheader("📥 Exportar Dados")
            col_exp1, col_exp2 = st.columns(2)
            
            csv_data = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            col_exp1.download_button(
                label="💾 Baixar Tabela em CSV (Excel)",
                data=csv_data,
                file_name="solicitacoes_compras.csv",
                mime="text/csv"
            )
            
            html_table = df.to_html(index=False)
            col_exp2.download_button(
                label="📊 Baixar Tabela Compatível Excel (.xls)",
                data=html_table,
                file_name="solicitacoes_compras.xls",
                mime="application/vnd.ms-excel"
            )

            st.markdown("---")
            
            st.subheader("📋 Solicitações Registradas")
            st.dataframe(df, use_container_width=True)
            
            st.subheader("✏️ Atualizar Pedido e Status")
            protocolo_sel = st.selectbox("Selecione o Protocolo para Atualizar:", df["protocolo"].tolist())
            dado_atual = df[df["protocolo"] == protocolo_sel].iloc[0]
            
            if dado_atual['caminho_anexo'] != "-" and os.path.exists(dado_atual['caminho_anexo']):
                with open(dado_atual['caminho_anexo'], "rb") as file:
                    st.download_button(
                        label="📎 Baixar Anexo Enviado pelo Colaborador",
                        data=file,
                        file_name=os.path.basename(dado_atual['caminho_anexo'])
                    )

            with st.form("form_atualizar"):
                c_a, c_b = st.columns(2)
                with c_a:
                    novo_status = st.selectbox("Status do Pedido", ["Aguardando", "Em Cotação", "Cotação Enviada", "Finalizado"],
                        index=["Aguardando", "Em Cotação", "Cotação Enviada", "Finalizado"].index(dado_atual['status']) if dado_atual['status'] in ["Aguardando", "Em Cotação", "Cotação Enviada", "Finalizado"] else 0)
                with c_b:
                    nova_aprovacao = st.selectbox("Compra Aprovada?", ["Pendente", "Sim", "Não"],
                        index=["Pendente", "Sim", "Não"].index(dado_atual['aprovado']) if dado_atual['aprovado'] in ["Pendente", "Sim", "Não"] else 0)
                
                c_c, c_d = st.columns(2)
                with c_c:
                    dt_compra = st.text_input("Data da Compra (DD/MM/AAAA)", value=dado_atual['data_compra'])
                with c_d:
                    dt_entrega = st.text_input("Previsão de Entrega (DD/MM/AAAA)", value=dado_atual['previsao_entrega'])
                
                # Campo de Justificativa de Reprovação
                motivo_reprovacao = st.text_area(
                    "Motivo da Não Aprovação (Obrigatório se selecionou 'Não' em Compra Aprovada):",
                    value=dado_atual.get('motivo_reprovacao', '') if dado_atual.get('motivo_reprovacao') != '-' else ''
                )

                if st.form_submit_button("Salvar Alterações e Notificar Requisitante"):
                    if nova_aprovacao == "Não" and not motivo_reprovacao.strip():
                        st.error("⚠️ Digite o motivo da não aprovação para prosseguir.")
                    else:
                        motivo_salvar = motivo_reprovacao.strip() if nova_aprovacao == "Não" else "-"
                        
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute('''
                            UPDATE solicitacoes 
                            SET status = ?, aprovado = ?, data_compra = ?, previsao_entrega = ?, motivo_reprovacao = ?
                            WHERE protocolo = ?
                        ''', (novo_status, nova_aprovacao, dt_compra, dt_entrega, motivo_salvar, protocolo_sel))
                        conn.commit()
                        conn.close()
                        
                        # E-mail enviado ao colaborador
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

                        st.success(f"Protocolo {protocolo_sel} atualizado e e-mail enviado para {dado_atual['email_requisitante']} com sucesso!")
                        st.rerun()
        else:
            st.info("Nenhuma solicitação encontrada.")
    else:
        st.warning("Insira a senha do administrador para acessar o painel de compras.")
