"""
Script para limpar o banco de dados e recriar dados iniciais:
- Administrador (admin/admin)
- Uma clínica com 2 veterinários
- Usuário de login da clínica (user/user) vinculado à clínica — os veterinários aparecem no formulário de requisição
"""
import sys
import os

# Adicionar diretório raiz ao path ANTES dos imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from auth.auth_utils import hash_password  # noqa: E402
from database.models import User, Clinica, Veterinario  # noqa: E402
from database.connection import get_db, init_db  # noqa: E402


def reset_db():
    """Limpa o banco e cria: admin, clínica com 2 veterinários, usuário da clínica (user = login da clínica)."""
    try:
        init_db()
        db = get_db()

        print("=" * 60)
        print("🗑️  Limpando banco de dados...")
        print("=" * 60)

        collections_to_clear = [
            "users",
            "requisicoes",
            "laudos",
            "faturas",
            "knowledge_base",
            "sessions",
            "clinicas",
            "veterinarios",
            "learning_history",
            "correcoes_laudo",
        ]

        for collection_name in collections_to_clear:
            collection = getattr(db, collection_name, None)
            if collection is not None:
                count = collection.count_documents({})
                collection.delete_many({})
                print(f"   ✅ {collection_name}: {count} documento(s) removido(s)")

        print()
        print("=" * 60)
        print("👤 Criando administrador e clínica com usuário...")
        print("=" * 60)

        user_model = User(db.users)
        clinica_model = Clinica(db.clinicas)
        veterinario_model = Veterinario(db.veterinarios)

        # 1. Admin (sem clínica)
        password_hash_admin = hash_password("admin")
        user_model.create(
            username="admin",
            email="admin@paics.local",
            password_hash=password_hash_admin,
            role="admin",
            nome="Administrador Dummy",
            ativo=True,
            primeiro_acesso=False,
            senha_temporaria=None,
            clinica_id=None,
        )
        print("   ✅ Administrador criado (admin / admin)")

        # 2. Clínica
        clinica_id = clinica_model.create(
            nome="Clínica Dummy PAICS",
            cnpj="00.000.000/0001-00",
            endereco="Rua Exemplo, 123",
            telefone="(00) 0000-0000",
            email="contato@clinicadummy.paics.local",
            ativa=True,
        )
        print("   ✅ Clínica criada: Clínica Dummy PAICS")

        # 3. Dois veterinários na clínica
        veterinario_model.create(
            nome="Dr. Veterinário 1",
            crmv="CRMV-DUMMY-1",
            clinica_id=clinica_id,
            email="vet1@clinicadummy.paics.local",
            ativo=True,
        )
        veterinario_model.create(
            nome="Dra. Veterinária 2",
            crmv="CRMV-DUMMY-2",
            clinica_id=clinica_id,
            email="vet2@clinicadummy.paics.local",
            ativo=True,
        )
        print("   ✅ 2 veterinários criados na clínica")

        # 4. Usuário de login da clínica (user = clínica; no formulário de requisição aparecem os 2 veterinários)
        password_hash_user = hash_password("user")
        user_model.create(
            username="user",
            email="user@paics.local",
            password_hash=password_hash_user,
            role="user",
            nome="Usuário Clínica (login da clínica)",
            ativo=True,
            primeiro_acesso=False,
            senha_temporaria=None,
            clinica_id=clinica_id,
        )
        print("   ✅ Usuário da clínica criado (user / user) e vinculado à clínica")

        print()
        print("=" * 60)
        print("✅ Banco de dados resetado com sucesso!")
        print("=" * 60)
        print()
        print("📋 Credenciais:")
        print()
        print("   👨‍⚕️ Administrador: admin / admin")
        print()
        print("   👤 Clínica (login da clínica): user / user")
        print("      → No formulário de requisições: escolha entre os 2 veterinários como requisitante.")
        print()
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Erro ao resetar banco de dados: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    reset_db()
