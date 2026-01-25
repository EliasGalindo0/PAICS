"""
Script para limpar o banco de dados e criar admin e usuário dummy
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


def reset_db():
    """Limpa o banco de dados e cria admin e usuário dummy"""
    try:
        # Inicializar banco
        init_db()
        db = get_db()

        print("=" * 60)
        print("🗑️  Limpando banco de dados...")
        print("=" * 60)

        # Limpar todas as coleções
        collections_to_clear = [
            "users",
            "requisicoes",
            "laudos",
            "faturas",
            "knowledge_base"
        ]

        for collection_name in collections_to_clear:
            collection = getattr(db, collection_name, None)
            if collection:
                count = collection.count_documents({})
                collection.delete_many({})
                print(f"   ✅ {collection_name}: {count} documento(s) removido(s)")

        print()
        print("=" * 60)
        print("👤 Criando usuários dummy...")
        print("=" * 60)

        user_model = User(db.users)

        # Criar admin dummy
        password_hash_admin = hash_password("admin")
        user_model.create(
            username="admin",
            email="admin@paics.local",
            password_hash=password_hash_admin,
            role="admin",
            nome="Administrador Dummy",
            ativo=True,
            primeiro_acesso=False,  # Admin dummy não precisa alterar senha
            senha_temporaria=None
        )
        print("   ✅ Admin dummy criado")
        print("      Username: admin")
        print("      Senha: admin")

        # Criar usuário dummy
        password_hash_user = hash_password("user")
        user_model.create(
            username="user",
            email="user@paics.local",
            password_hash=password_hash_user,
            role="user",
            nome="Usuário Dummy",
            ativo=True,
            primeiro_acesso=False,  # Usuário dummy não precisa alterar senha
            senha_temporaria=None
        )
        print("   ✅ Usuário dummy criado")
        print("      Username: user")
        print("      Senha: user")

        print()
        print("=" * 60)
        print("✅ Banco de dados resetado com sucesso!")
        print("=" * 60)
        print()
        print("📋 Credenciais de acesso:")
        print()
        print("   👨‍⚕️ Administrador:")
        print("      Username: admin")
        print("      Senha: admin")
        print()
        print("   👤 Usuário:")
        print("      Username: user")
        print("      Senha: user")
        print()
        print("⚠️  IMPORTANTE:")
        print("   - Faça login com essas credenciais para testar")
        print("   - Crie seus próprios usuários na interface")
        print("   - Exclua os usuários dummy quando não precisar mais")
        print()
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Erro ao resetar banco de dados: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    reset_db()
