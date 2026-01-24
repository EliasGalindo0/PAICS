"""
Script para criar usuário administrador inicial
"""
from database.connection import get_db, init_db
from database.models import User
from auth.auth_utils import hash_password
import sys
import os

# Adicionar diretório raiz ao path ANTES dos imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def create_admin():
    """Cria um usuário administrador"""
    try:
        # Inicializar banco
        init_db()
        db = get_db()
        user_model = User(db.users)

        print("=" * 50)
        print("Criação de Usuário Administrador")
        print("=" * 50)

        # Verificar se já existe admin
        existing_admins = user_model.get_all(role="admin")
        if existing_admins:
            print(f"\n⚠️  Já existem {len(existing_admins)} administrador(es) cadastrado(s).")
            resposta = input("Deseja criar outro? (s/n): ").lower()
            if resposta != 's':
                print("Operação cancelada.")
                return

        # Coletar dados
        print("\nPreencha os dados do administrador:")
        nome = input("Nome completo: ").strip()
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = input("Senha: ").strip()
        password_confirm = input("Confirmar senha: ").strip()

        # Validações
        if not all([nome, username, email, password]):
            print("❌ Erro: Todos os campos são obrigatórios!")
            return

        if password != password_confirm:
            print("❌ Erro: As senhas não coincidem!")
            return

        # Verificar se email ou username já existem
        if user_model.find_by_email(email):
            print(f"❌ Erro: Email {email} já está cadastrado!")
            return

        if user_model.find_by_username(username):
            print(f"❌ Erro: Username {username} já está em uso!")
            return

        # Criar usuário
        password_hash = hash_password(password)
        user_id = user_model.create(
            username=username,
            email=email,
            password_hash=password_hash,
            role="admin",
            nome=nome,
            ativo=True
        )

        print(f"\n✅ Administrador criado com sucesso!")
        print(f"   ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print("\nVocê pode fazer login agora no sistema.")

    except Exception as e:
        print(f"\n❌ Erro ao criar administrador: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_admin()
