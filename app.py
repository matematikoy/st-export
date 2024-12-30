import streamlit as st
import requests
import os
from datetime import datetime
import io


# Função para obter o token de autorização e salvar em um arquivo
def obter_token_autorizacao(usuario, senha):
    url_login = "https://api.grupohne.com.br/api/login"
    dados_login = {
        "usuario": usuario,  
        "password": senha     
    }

    headers = {
        "Content-Type": "application/json" 
    }

    try:
        # Realiza a requisição de login
        response = requests.post(url_login, headers=headers, json=dados_login)

        if response.ok:
            data = response.json()
            if "token" in data:
                token = data["token"]

                with open("token.txt", "w", encoding="utf-8") as token_file:
                    token_file.write(token)
                return token
            else:
                return None
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None

# Função de login usando a API para obter o token
def login(username, password):
    token = obter_token_autorizacao(username, password)
    if token:
        return True, token
    else:
        return False, None

# Função para enviar os livros
def enviar_livros(token, unidade, data_inicial, data_final):
    url = "https://api.grupohne.com.br/api/v1/aluno/enviar-livros?page=1&pageSize=10"
    headers = {
        "Authorization": f"Bearer {token}",  
        "Content-Type": "application/json"   
    }

    payload = {
        "filtro": {
            "tipo": "pacsedex",
            "tipo_curso": "",
            "cidade": "",
            "unidade": unidade,
            "status_inscricao": "",
            "material_entrega": {"pac": True, "sedex": True},
            "data_inicial": data_inicial,
            "data_final": data_final
        },
        "page": 1,
        "pageSize": 350
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        ids_nomes_cursos_emitidos = [(item['id'], item['nome'], item.get('curso', 'Curso não disponível')) for item in data['data'] if item['nota'] == "EMITIDA"]
        
        if ids_nomes_cursos_emitidos:
            return ids_nomes_cursos_emitidos
        else:
            return []
    else:
        return []
    

def exportar_correios(token, ids):
    url = "https://api.grupohne.com.br/api/v1/aluno/exportar_correios"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "ids": ids
    }

    response = requests.post(url, json=payload, headers=headers)

    # Verificar se a requisição foi bem-sucedida

    if response.status_code == 200:
        # Obter a data de hoje
        data_hoje = datetime.today().strftime("%d%m%Y")
        
        linhas = response.content.decode('utf-8').splitlines()
        
        if len(linhas) > 1:

            # Criar um arquivo CSV na memória
            csv_buffer = io.StringIO()
            
            # Definir o cabeçalho do arquivo CSV
            cabecalho = "SERVICO;DESTINATARIO;CEP;LOGRADOURO;NUMERO;COMPLEMENTO;BAIRRO;EMAIL;;;CPF/CNPJ;VALOR_DECLARADO;;TIPO_OBJETO;;;;;AR;MP;;;OBSERVACAO\n"
            csv_buffer.write(cabecalho)
            
            for linha in linhas[1:]:
                csv_buffer.write(linha + "\n")
            
            # Retornar o conteúdo do CSV e o nome do arquivo
            return csv_buffer.getvalue(), f"CORREIOS_{data_hoje}.csv"

        else:
            return None, None
    else:
        return None, None

# Função para criar a nav-bar
def criar_navbar():
    # Barra de navegação no topo
    st.markdown("""
        <style>
            .navbar {
                background-color: #4CAF50;
                overflow: hidden;
                position: fixed;
                top: 0;
                width: 100%;
                padding: 10px 0;
                z-index: 1000;
            }
            .navbar a {
                color: white;
                padding: 14px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 17px;
                display: inline-block;
            }
            .navbar a:hover {
                background-color: #45a049;
            }
        </style>
    """, unsafe_allow_html=True)

    # Barra de navegação com links (não há links definidos, é só para visual)
    st.markdown('<div class="navbar">', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Função principal que será chamada após o login
def main():

    criar_navbar()

    # Verificar se já existe um token no session_state
    if 'token' not in st.session_state:

        # Caso o token não esteja no session_state, mostra a tela de login
        st.title("Login")
        st.subheader("Digite suas credenciais do Sistema Grupo HNe")

        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        login_button = st.button("Entrar")

        if login_button:
            sucesso, token = login(usuario, senha)
            if sucesso:
                st.session_state.token = token
                st.success("Login bem-sucedido!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
                return
        return



    if 'envio_confirmado' not in st.session_state or not st.session_state.envio_confirmado:
        st.title("Filtre os alunos.")
        centro_custo = st.selectbox("Escolha o Centro de Custo", ["BH", "GO", "ES"])

        unidade = []
        if centro_custo == "BH":
            unidade = [29, 27, 18, 1, 30, 19, 20, 28, 12, 7, 8, 21, 22, 10, 25, 4, 26, 9, 11, 23, 13, 24]
        elif centro_custo == "GO":
            unidade = [14]
        elif centro_custo == "ES":
            unidade = [3]

        st.subheader("Escolha as datas")

        col1, col2 = st.columns(2)

        # Data inicial
        with col1:
            data_inicial = st.date_input("Data Inicial", datetime.today())

        # Data final
        with col2:
            data_final = st.date_input("Data Final", datetime.today())

        st.write(f"Período do Curso: de {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")

        # Realizar a requisição de envio de livros
        if st.button("Enviar Livros"):
            if data_final < data_inicial:
                st.error("A data final não pode ser anterior à data inicial.")
            else:
                ids_nomes_cursos_emitidos = enviar_livros(st.session_state.token, unidade, data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d"))

                if ids_nomes_cursos_emitidos:
                    st.session_state.ids_nomes_cursos_emitidos = ids_nomes_cursos_emitidos
                    
                    confirmar_envio = st.radio(f"Deseja confirmar a exportação de {len(ids_nomes_cursos_emitidos)} alunos?", ['Sim', 'Não'])

                    if confirmar_envio == 'Sim':
                        st.session_state.envio_confirmado = True  # Marca que o envio foi confirmado
                        st.rerun()
                else:
                    st.warning("Nenhum aluno encontrado para exportação.")
    
    if 'envio_confirmado' in st.session_state and st.session_state.envio_confirmado:
        st.title("Detalhes dos alunos a serem exportados")

        with st.expander("Lista de alunos a exportar", expanded=True):
            # Obter os dados dos alunos armazenados no session_state
            ids_nomes_cursos_emitidos = st.session_state.get('ids_nomes_cursos_emitidos', [])

            html_content = """
            <div style="max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; margin-bottom: 10px;">
            """

            for item in ids_nomes_cursos_emitidos:
                nome, curso = item[1], item[2]
                html_content += f"<p style='background-color: #d8d4dc; padding: 10px; border-radius: 5px; border: 1px solid #d8d4dc;'><b>Aluno:</b> {nome}<br><b>Curso:</b> {curso}</p>"

            html_content += "</div>"

            st.markdown(html_content, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 5])
        with col1:

            # Verificar se o botão "EXPORTAR" foi pressionado
            if st.button("EXPORTAR"):
                # Chamar a função de exportação para obter o conteúdo CSV e o nome do arquivo
                csv_data, file_name = exportar_correios(st.session_state.token, [item[0] for item in ids_nomes_cursos_emitidos])  # Passar os IDs dos alunos

                if csv_data:

                    st.download_button(
                        label="BAIXAR AQUIVO CSV",
                        data=csv_data,
                        file_name=file_name,
                        mime="text/csv"
                    )
                else:
                    st.warning("Erro ao exportar dados. Verifique a resposta da API.")
                
        with col2:
            if st.button("CANCELAR"):
                st.session_state.envio_confirmado = False
                st.rerun()
                

if __name__ == "__main__":
    main()