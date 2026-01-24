"""
Script para criar administrador dummy inicial
Este script cria um usuário admin padrão (admin/admin) para primeiro acesso
"""
import sys
import os

# Adicionar diretório raiz ao path ANTES dos imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from auth.auth_utils import hash_password
from database.models import User
from database.connection import get_db, init_db


def seed_admin():
    """Cria um administrador dummy inicial"""
    try:
        # Inicializar banco
        init_db()
        db = get_db()
        user_model = User(db.users)

        # Verificar se já existe o admin dummy
        existing_admin = user_model.find_by_username("admin")
        if existing_admin:
            print("ℹ️  Administrador dummy já existe")
            print(f"   Username: admin")
            print(f"   Email: {existing_admin.get('email', 'N/A')}")
            return

        # Verificar se já existe algum admin
        existing_admins = user_model.get_all(role="admin")
        if existing_admins:
            print(f"⚠️  Já existem {len(existing_admins)} administrador(es) cadastrado(s).")
            print("   O seed do admin dummy não será criado.")
            return

        # Criar admin dummy
        password_hash = hash_password("admin")
        user_id = user_model.create(
            username="admin",
            email="admin@paics.local",
            password_hash=password_hash,
            role="admin",
            nome="Administrador Dummy",
            ativo=True,
            primeiro_acesso=False,  # Admin dummy não precisa alterar senha
            senha_temporaria=None
        )

        print("=" * 60)
        print("✅ Administrador Dummy Criado com Sucesso!")
        print("=" * 60)
        print()
        print("📋 Credenciais de Acesso:")
        print("   Username: admin")
        print("   Senha: admin")
        print()
        print("⚠️  IMPORTANTE:")
        print("   1. Faça login com essas credenciais")
        print("   2. Crie seu próprio usuário administrador")
        print("   3. Exclua este usuário dummy na página de Gerenciamento de Usuários")
        print()
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Erro ao criar administrador dummy: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    seed_admin()
