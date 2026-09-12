"""
Fixtures compartilhadas pelos testes.

`db_session` roda cada teste dentro de uma transação externa que é
sempre revertida no final, usando o padrão "join a transaction, bind
a SAVEPOINT" do próprio SQLAlchemy: quando um teste provoca um erro
de integridade de propósito (ex.: violar um UNIQUE) e o SQLAlchemy
reverte a sessão internamente, um listener reabre a savepoint na
hora, então o teste seguinte ainda roda isolado dentro da mesma
transação externa, sem sujar o Postgres de desenvolvimento e sem
precisar de um banco de teste separado nesta fase inicial. Isso muda
a partir de quando a suíte crescer o bastante pra valer a pena
isolar um banco de teste próprio.

**Bug de infraestrutura de teste corrigido na ETAPA 22** (achado ao
escrever `test_scheduler_service.py`, que foi o primeiro teste da
suíte a chamar `session.rollback()` explicitamente no meio do teste,
e não só o `db.commit()` que todo service já fazia): o listener
original verificava `transaction.nested and not transaction._parent.nested`
(o jeito documentado pro SQLAlchemy 1.x) — depois de alguns ciclos de
commit/reabertura de savepoint, essa condição parava de disparar, e
um `session.rollback()` chamado depois disso revertia a transação
INTEIRA (a de fora, nunca reaberta pelo teste), apagando até dado já
"commitado" antes. A correção é a recomendada pelos docs do
SQLAlchemy 2.0 pra este mesmo padrão: checar
`connection.in_nested_transaction()` (estado da conexão, não do
objeto `SessionTransaction` do ORM) — reproduzido e confirmado à mão
antes de aplicar aqui, ver `docs/decisions.md`.

`client` reusa a MESMA sessão transacional via override de `get_db`
— sem isso, uma requisição HTTP feita pelo TestClient usaria uma
sessão própria contra o Postgres real e faria commit de verdade,
poluindo o banco de desenvolvimento a cada rodada de teste.
"""
import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import engine, get_db
from app.main import app
from app.models.user import User


@pytest.fixture()
def db_session() -> Session:
    connection = engine.connect()
    outer_transaction = connection.begin()

    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    session.begin_nested()  # SAVEPOINT

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, transaction):
        if not connection.in_nested_transaction():
            connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# Helpers repetidos em quase todo módulo de teste a partir da ETAPA 8
# (qualquer coisa que exija usuário autenticado). Centralizados aqui
# depois de aparecerem duplicados, palavra por palavra, em 10+
# arquivos — encontrado numa revisão geral da suíte.

def register_and_login(client, email: str, password: str) -> dict:
    """Registra e loga um usuário, devolvendo o header pronto pra usar."""
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    tokens = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def user_id(db_session: Session, email: str):
    """Busca o id do usuário direto no banco — usado quando um teste
    precisa inserir uma linha (ex.: `FunctionalIndicator`/`DeviationEvent`)
    direto via `db_session`, sem passar pela API."""
    return db_session.query(User).filter_by(email=email).one().id


def post_checkin(client, headers: dict, days_ago: int, **fields):
    """Cria um check-in retroativo (`checkin_date` = hoje - days_ago)
    com os campos passados — usado por qualquer teste que precise
    simular histórico (baseline, motor de desvio, estado, explicação)."""
    checkin_date = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()
    response = client.post("/api/v1/checkins", json={"checkin_date": checkin_date, **fields}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()
