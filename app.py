import streamlit as st
import requests
import os
from datetime import datetime

# Função para obter o token de autorização e salvar em um arquivo
def obter_token_autorizacao(usuario, senha):
    url_login = "https://api.grupohne.com.br/api/login"  # URL de login
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
                # Salva o token
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

# Função para enviar os livros (endpoint da API)
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
            "unidade": unidade,  # Unidade baseada no Centro de Custo
            "status_inscricao": "",
            "material_entrega": {"pac": True, "sedex": True},
            "data_inicial": data_inicial,  # API espera no formato yyyy-mm-dd
            "data_final": data_final       # API espera no formato yyyy-mm-dd
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

    # Enviar requisição POST para exportar os correios
    response = requests.post(url, json=payload, headers=headers)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        # Obter a data de hoje no formato ddmmaaaa para nomear o arquivo
        data_hoje = datetime.today().strftime("%d%m%Y")
        
        # O conteúdo da resposta será em formato CSV
        linhas = response.content.decode('utf-8').splitlines()
        
        if len(linhas) > 1:
            # Criar um arquivo CSV na memória
            csv_buffer = io.StringIO()
            
            # Definir o cabeçalho do arquivo CSV
            cabecalho = "SERVICO;DESTINATARIO;CEP;LOGRADOURO;NUMERO;COMPLEMENTO;BAIRRO;EMAIL;;;CPF/CNPJ;VALOR_DECLARADO;;TIPO_OBJETO;;;;;AR;MP;;;OBSERVACAO\n"
            csv_buffer.write(cabecalho)
            
            # Escrever as linhas do CSV
            for linha in linhas[1:]:
                csv_buffer.write(linha + "\n")
            
            # Criar o botão de download no Streamlit
            st.download_button(
                label="Baixar CSV de Correios",
                data=csv_buffer.getvalue(),
                file_name=f"CORREIOS_{data_hoje}.csv",
                mime="text/csv"
            )

            st.success(f"Arquivo CSV gerado com sucesso! Clique no botão acima para baixar.")
        else:
            st.warning("Resposta da API não contém dados válidos.")
    else:
        st.warning(f"Erro ao exportar correios: {response.status_code}")


# Função principal que será chamada após o login
def main():
    # Verificar se já existe um token no session_state
    if 'token' not in st.session_state:
        # Caso o token não esteja no session_state, mostra apenas a tela de login
        st.title("Login")
        st.subheader("Digite suas credenciais")

        # Limpar a tela, exibir apenas campos de login
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        login_button = st.button("Entrar")

        if login_button:
            sucesso, token = login(usuario, senha)
            if sucesso:
                st.session_state.token = token  # Armazenar o token no session_state
                st.success("Login bem-sucedido!")
                st.rerun()  # Redefine a página para exibir o conteúdo principal
            else:
                st.error("Usuário ou senha incorretos.")
                return
        return  # Não executa nada mais após o login



    # Exibir os filtros (Centro de Custo, Datas) se ainda não foram cancelados
    if 'envio_confirmado' not in st.session_state or not st.session_state.envio_confirmado:
            # Se o token estiver no session_state, continua a execução normal
        st.title("Filtre os alunos.")
        # Mostrar o centro de custo (ComboBox)
        centro_custo = st.selectbox("Escolha o Centro de Custo", ["BH", "GO", "ES"])

        unidade = []
        if centro_custo == "BH":
            unidade = [29, 27, 18, 1, 30, 19, 20, 28, 12, 7, 8, 21, 22, 10, 25, 4, 26, 9, 11, 23, 13, 24]
        elif centro_custo == "GO":
            unidade = [14]
        elif centro_custo == "ES":
            unidade = [3]

        # Solicitar a data inicial e final com os calendários
        st.subheader("Escolha as datas")

        # Criar colunas para exibir as datas lado a lado
        col1, col2 = st.columns(2)

        # Data inicial
        with col1:
            data_inicial = st.date_input("Data Inicial", datetime.today())

        # Data final
        with col2:
            data_final = st.date_input("Data Final", datetime.today())

        # Exibir as datas selecionadas
        st.write(f"Período do Curso: de {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")

        # Realizar a requisição de envio de livros
        if st.button("Enviar Livros"):
            if data_final < data_inicial:
                st.error("A data final não pode ser anterior à data inicial.")
            else:
                ids_nomes_cursos_emitidos = enviar_livros(st.session_state.token, unidade, data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d"))

                if ids_nomes_cursos_emitidos:
                    # Armazenar os dados dos alunos no session_state para garantir que estarão disponíveis
                    st.session_state.ids_nomes_cursos_emitidos = ids_nomes_cursos_emitidos
                    
                    # Perguntar se o usuário quer enviar os IDs para exportação
                    confirmar_envio = st.radio(f"Deseja confirmar a exportação de {len(ids_nomes_cursos_emitidos)} alunos?", ['Sim', 'Não'])

                    if confirmar_envio == 'Sim':
                        st.session_state.envio_confirmado = True  # Marcar que o envio foi confirmado
                        st.rerun()  # Recarregar a tela para exibir o expander
                else:
                    st.warning("Nenhum aluno encontrado para exportação.")
    
    # Exibir o expander se o envio for confirmado
    if 'envio_confirmado' in st.session_state and st.session_state.envio_confirmado:
        st.title("Detalhes dos Alunos a Serem Enviados")

        # Criar um expander com rolagem
        with st.expander("Lista de alunos a exportar", expanded=True):
            # Obter os dados dos alunos armazenados no session_state
            ids_nomes_cursos_emitidos = st.session_state.get('ids_nomes_cursos_emitidos', [])

            # Verifique o conteúdo da lista de alunos
            #st.write(ids_nomes_cursos_emitidos)  # Adicione isso para verificar a lista

            # Definir o conteúdo HTML para a rolagem
            html_content = """
            <div style="max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; margin-bottom: 10px;">
            """

            # Adicionar os alunos ao conteúdo HTML com rolagem
            for item in ids_nomes_cursos_emitidos:
                nome, curso = item[1], item[2]  # Desempacotar os dados de nome e curso
                #st.write(f"Aluno: {nome} - Curso: {curso}")  # Exibição simples sem HTML
                html_content += f"<p style='background-color: #d8d4dc; padding: 10px; border-radius: 5px; border: 1px solid #d8d4dc;'><b>Aluno:</b> {nome}<br><b>Curso:</b> {curso}</p>"

            # Fechar a tag <div> e adicionar ao Streamlit
            html_content += "</div>"

            # Exibir o conteúdo com rolagem dentro do expander
            st.markdown(html_content, unsafe_allow_html=True)

        # Criar colunas para os botões de Exportar e Cancelar
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Exportar"):
                # Aqui você pode chamar a função de exportação
                exportar_correios(st.session_state.token, [item[0] for item in ids_nomes_cursos_emitidos])  # Passar os IDs dos alunos
                

                
        with col2:
            if st.button("Cancelar"):
                st.session_state.envio_confirmado = False  # Voltar para a tela de filtros
                st.rerun()  # Recarregar a tela para exibir novamente o filtro
                

# Rodar o aplicativo Streamlit
if __name__ == "__main__":
    main()


