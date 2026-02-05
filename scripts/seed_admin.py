"""
Script para criar administrador e clínica iniciais.
- Admin: usuário admin (admin/admin) para primeiro acesso.
- Clínica com 2 veterinários e usuário de login vinculado à clínica (user/user).
  O login pertence à clínica; no formulário de requisições o usuário escolhe qual dos 2 veterinários é o requisitante.
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
            print("   Usuário: admin")
            print(f"   E-mail: {existing_admin.get('email', 'N/A')}")
            return

        # Verificar se já existe algum admin
        existing_admins = user_model.get_all(role="admin")
        if existing_admins:
            print(f"⚠️  Já existem {len(existing_admins)} administrador(es) cadastrado(s).")
            print("   O seed do admin dummy não será criado.")
            return

        # Criar admin dummy (sem clínica)
        password_hash = hash_password("admin")
        user_model.create(
            username="admin",
            email="admin@paics.local",
            password_hash=password_hash,
            role="admin",
            nome="Administrador Dummy",
            ativo=True,
            primeiro_acesso=False,  # Admin dummy não precisa alterar senha
            senha_temporaria=None,
            clinica_id=None,
        )

        print("=" * 60)
        print("✅ Administrador Dummy Criado com Sucesso!")
        print("=" * 60)
        print()
        print("📋 Credenciais de Acesso (Admin):")
        print("   Usuário: admin")
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


def seed_clinica_and_user():
    """Cria uma clínica com 2 veterinários e um usuário de login vinculado à clínica."""
    try:
        init_db()
        db = get_db()
        clinica_model = Clinica(db.clinicas)
        veterinario_model = Veterinario(db.veterinarios)
        user_model = User(db.users)

        nome_clinica = "Clínica Dummy PAICS"
        clinicas = clinica_model.get_all(apenas_ativas=False)
        clinica_dummy = next((c for c in clinicas if (c.get("nome") or "").strip() == nome_clinica), None)

        if clinica_dummy:
            print("ℹ️  Clínica já existe:", clinica_dummy.get("nome"))
            clinica_id = clinica_dummy["id"]
            # Garantir que existem 2 veterinários na clínica
            vets = veterinario_model.find_by_clinica(clinica_id, apenas_ativos=False)
            if len(vets) < 2:
                for i in range(2 - len(vets)):
                    idx = len(vets) + i + 1
                    veterinario_model.create(
                        nome=f"Dr(a). Veterinário(a) {idx}",
                        crmv=f"CRMV-DUMMY-{idx}",
                        clinica_id=clinica_id,
                        email=f"vet{idx}@clinicadummy.paics.local",
                        ativo=True,
                    )
                print("✅ Segundo veterinário criado na clínica (total: 2)")
        else:
            # Criar clínica
            clinica_id = clinica_model.create(
                nome=nome_clinica,
                cnpj="00.000.000/0001-00",
                endereco="Rua Exemplo, 123",
                telefone="(00) 0000-0000",
                email="contato@clinicadummy.paics.local",
                ativa=True,
            )
            print("✅ Clínica criada:", clinica_id)

            # Criar 2 veterinários na clínica
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
            print("✅ 2 veterinários criados na clínica")

        # Verificar se já existe o usuário de login da clínica
        if user_model.find_by_username("user"):
            print("ℹ️  Usuário de login da clínica (user) já existe")
            return

        # Criar usuário de login vinculado à clínica (o login pertence à clínica)
        password_hash = hash_password("user")
        user_model.create(
            username="user",
            email="user@paics.local",
            password_hash=password_hash,
            role="user",
            nome="Usuário Clínica (login da clínica)",
            ativo=True,
            primeiro_acesso=False,
            senha_temporaria=None,
            clinica_id=clinica_id,
        )
        print("✅ Usuário de login criado e vinculado à clínica")

        print()
        print("📋 Credenciais do usuário da clínica (login pertence à clínica):")
        print("   Usuário: user")
        print("   Senha: user")
        print("   No formulário de requisições será possível escolher qual dos 2 veterinários é o requisitante.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Erro ao criar clínica/usuário dummy: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    seed_admin()
    print()
    seed_clinica_and_user()
