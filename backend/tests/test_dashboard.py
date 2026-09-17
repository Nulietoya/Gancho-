"""
ETAPA 23/24 — dashboards. Cobre a visão diária e analítica do dono
(agregando dado que outras ETAPAs já testaram na origem — aqui só
verifica a montagem/formatação) e a visão da pessoa de confiança
(o que muda em relação às outras duas: cada seção só aparece se a
permissão correspondente estiver concedida).
"""
import datetime

from app.models.deviation import Alert, DeviationEvent
from app.models.enums import AlertState, DeviationEngine, PermissionKey
from app.models.trust import TrustedPersonRelationship
from tests.conftest import post_checkin as _post_checkin
from tests.conftest import register_and_login as _register_and_login
from tests.conftest import user_id as _user_id

OWNER_EMAIL = "dash-dono@example.com"
OWNER_PASSWORD = "senhaForte123"
TRUSTED_EMAIL = "dash-confianca@example.com"
TRUSTED_PASSWORD = "outraSenhaForte123"


def _fully_connected_relationship(client, db_session):
    owner_headers = _register_and_login(client, OWNER_EMAIL, OWNER_PASSWORD)
    client.post("/api/v1/trusted-people/invite", json={"email": TRUSTED_EMAIL}, headers=owner_headers)
    raw_token = (
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().invite_token
    )
    trusted_headers = _register_and_login(client, TRUSTED_EMAIL, TRUSTED_PASSWORD)
    client.post("/api/v1/trusted-people/accept", json={"invite_token": raw_token}, headers=trusted_headers)
    relationship_id = str(
        db_session.query(TrustedPersonRelationship).filter_by(invite_email=TRUSTED_EMAIL).one().id
    )
    return owner_headers, trusted_headers, relationship_id


def _grant(client, owner_headers, relationship_id, permission_key, indicator_scope=None):
    payload = {"permission_key": permission_key, "is_granted": True}
    if indicator_scope is not None:
        payload["indicator_scope"] = indicator_scope
    response = client.put(
        f"/api/v1/trusted-people/{relationship_id}/permissions",
        json={"permissions": [payload]},
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text


def _insert_alert(db_session, owner_id, state: AlertState):
    alert = Alert(user_id=owner_id, state=state, reason_summary=f"estado {state.value} de teste")
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


# --- dashboard diário (ETAPA 23) --------------------------------------------


def test_daily_dashboard_defaults_when_nothing_recorded_yet(client):
    headers = _register_and_login(client, "dash-vazio@example.com", "senhaForte123")
    response = client.get("/api/v1/dashboard/daily", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "green"
    assert body["state_since"] is None
    assert body["checkin_submitted_today"] is False
    assert body["checkin"] is None
    assert body["medications_today"] == []
    assert body["active_interventions"] == []
    assert body["unread_notifications_count"] == 0
    assert body["recent_notifications"] == []


def test_daily_dashboard_reflects_todays_checkin(client):
    headers = _register_and_login(client, "dash-checkin@example.com", "senhaForte123")
    client.post("/api/v1/checkins", json={"mood": 4}, headers=headers)

    body = client.get("/api/v1/dashboard/daily", headers=headers).json()
    assert body["checkin_submitted_today"] is True
    assert body["checkin"]["mood"] == 4


def test_daily_dashboard_lists_todays_medication_dose_and_its_status(client):
    headers = _register_and_login(client, "dash-medicacao@example.com", "senhaForte123")
    medication = client.post(
        "/api/v1/medications", json={"name": "Sertralina"}, headers=headers
    ).json()
    schedule = client.post(
        f"/api/v1/medications/{medication['id']}/schedules",
        json={"time_of_day": "08:00:00"},
        headers=headers,
    ).json()

    body = client.get("/api/v1/dashboard/daily", headers=headers).json()
    assert len(body["medications_today"]) == 1
    dose = body["medications_today"][0]
    assert dose["medication_name"] == "Sertralina"
    assert dose["status"] is None  # nenhum evento registrado ainda hoje

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.post(
        f"/api/v1/medications/{medication['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": now, "status": "taken"},
        headers=headers,
    )

    body = client.get("/api/v1/dashboard/daily", headers=headers).json()
    assert body["medications_today"][0]["status"] == "taken"


def test_daily_dashboard_medication_skips_dose_not_scheduled_for_today(client):
    """Horário com `weekdays` que não inclui hoje não aparece na lista de hoje."""
    headers = _register_and_login(client, "dash-medicacao-outrodia@example.com", "senhaForte123")
    medication = client.post("/api/v1/medications", json={"name": "Vitamina D"}, headers=headers).json()
    not_today = (datetime.date.today().weekday() + 1) % 7
    client.post(
        f"/api/v1/medications/{medication['id']}/schedules",
        json={"time_of_day": "09:00:00", "weekdays": [not_today]},
        headers=headers,
    )

    body = client.get("/api/v1/dashboard/daily", headers=headers).json()
    assert body["medications_today"] == []


def test_daily_dashboard_lists_only_active_interventions(client):
    headers = _register_and_login(client, "dash-intervencao@example.com", "senhaForte123")
    active = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    finished = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{finished['id']}/start", headers=headers)
    client.post(f"/api/v1/interventions/{finished['id']}/finish", headers=headers)

    body = client.get("/api/v1/dashboard/daily", headers=headers).json()
    ids = [i["id"] for i in body["active_interventions"]]
    assert active["id"] in ids
    assert finished["id"] not in ids


def test_daily_dashboard_counts_unread_notifications(client):
    headers = _register_and_login(client, "dash-notif@example.com", "senhaForte123")
    # primeiro /alerts/sync sem nenhum DeviationEvent cria o Alert inicial (VERDE) e notifica o dono
    client.post("/api/v1/alerts/sync", headers=headers)

    body = client.get("/api/v1/dashboard/daily", headers=headers).json()
    assert body["unread_notifications_count"] == 1
    assert len(body["recent_notifications"]) == 1

    notif_id = body["recent_notifications"][0]["id"]
    client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)

    body = client.get("/api/v1/dashboard/daily", headers=headers).json()
    assert body["unread_notifications_count"] == 0


# --- dashboard analítico (ETAPA 24) -----------------------------------------


def test_analytics_dashboard_defaults_when_nothing_recorded_yet(client):
    headers = _register_and_login(client, "dash-analitico-vazio@example.com", "senhaForte123")
    response = client.get("/api/v1/dashboard/analytics", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["period_days"] == 30
    assert body["alert_timeline"] == []
    assert body["indicators"] == []
    assert body["deviation_timeline"] == []
    assert body["medication_adherence"] == {
        "period_days": 30,
        "scheduled_count": 0,
        "taken_count": 0,
        "adherence_rate": None,
    }
    assert body["intervention_stats"] == {
        "total": 0,
        "by_status": {},
        "helped_count": 0,
        "not_helped_count": 0,
        "no_result_count": 0,
    }


def test_analytics_dashboard_days_query_param_is_bounded(client):
    headers = _register_and_login(client, "dash-dias@example.com", "senhaForte123")
    assert client.get("/api/v1/dashboard/analytics?days=6", headers=headers).status_code == 422
    assert client.get("/api/v1/dashboard/analytics?days=366", headers=headers).status_code == 422
    assert client.get("/api/v1/dashboard/analytics?days=7", headers=headers).status_code == 200


def test_analytics_dashboard_includes_active_baseline_as_indicator_trend(client):
    headers = _register_and_login(client, "dash-baseline@example.com", "senhaForte123")
    for days_ago in range(6):
        _post_checkin(client, headers, days_ago, mood=3)
    response = client.post("/api/v1/baseline/mood/recompute", headers=headers)
    assert response.status_code == 200, response.text

    body = client.get("/api/v1/dashboard/analytics", headers=headers).json()
    trends = {t["indicator_key"]: t for t in body["indicators"]}
    assert "mood" in trends
    assert trends["mood"]["baseline_mean"] == 3.0
    assert trends["mood"]["sample_size"] == 6


def test_analytics_dashboard_alert_timeline_and_deviation_timeline(client, db_session):
    headers = _register_and_login(client, "dash-timeline@example.com", "senhaForte123")
    owner_id = _user_id(db_session, "dash-timeline@example.com")

    now = datetime.datetime.now(datetime.timezone.utc)
    db_session.add(
        DeviationEvent(
            user_id=owner_id,
            engine=DeviationEngine.EXECUTIVE,
            detected_at=now,
            magnitude=2.0,
            duration_days=3,
            domains_count=1,
            convergence_score=1.0,
            triggering_indicator_keys=["ability_to_start_tasks"],
            baseline_snapshot={},
            explanation="teste",
        )
    )
    db_session.commit()
    client.post("/api/v1/alerts/sync", headers=headers)

    body = client.get("/api/v1/dashboard/analytics", headers=headers).json()
    assert len(body["alert_timeline"]) == 1
    assert len(body["deviation_timeline"]) == 1
    assert body["deviation_timeline"][0]["engine"] == "executive"


def test_analytics_dashboard_medication_adherence_and_intervention_stats(client):
    headers = _register_and_login(client, "dash-adesao@example.com", "senhaForte123")
    medication = client.post("/api/v1/medications", json={"name": "Fluoxetina"}, headers=headers).json()
    schedule = client.post(
        f"/api/v1/medications/{medication['id']}/schedules", json={"time_of_day": "08:00:00"}, headers=headers
    ).json()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.post(
        f"/api/v1/medications/{medication['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": now, "status": "taken"},
        headers=headers,
    )

    helped_one = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{helped_one['id']}/start", headers=headers)
    client.post(f"/api/v1/interventions/{helped_one['id']}/finish", headers=headers)
    client.put(f"/api/v1/interventions/{helped_one['id']}/result", json={"helped": True}, headers=headers)

    # ETAPA 33-34: os dois ramos abaixo (`not_helped`/`no_result`)
    # nunca tinham sido exercitados — só `helped=True` (achado via
    # `pytest --cov`). Contagem errada aqui reportaria efetividade de
    # intervenção enganosa pra pessoa, exatamente o tipo de bug que
    # vale a pena travar com teste.
    not_helped_one = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{not_helped_one['id']}/start", headers=headers)
    client.post(f"/api/v1/interventions/{not_helped_one['id']}/finish", headers=headers)
    client.put(f"/api/v1/interventions/{not_helped_one['id']}/result", json={"helped": False}, headers=headers)

    no_result_one = client.post("/api/v1/interventions/suggest", json={}, headers=headers).json()
    client.post(f"/api/v1/interventions/{no_result_one['id']}/start", headers=headers)
    client.post(f"/api/v1/interventions/{no_result_one['id']}/finish", headers=headers)
    # sem registrar resultado

    body = client.get("/api/v1/dashboard/analytics", headers=headers).json()
    assert body["medication_adherence"] == {
        "period_days": 30,
        "scheduled_count": 1,
        "taken_count": 1,
        "adherence_rate": 1.0,
    }
    assert body["intervention_stats"]["total"] == 3
    assert body["intervention_stats"]["helped_count"] == 1
    assert body["intervention_stats"]["not_helped_count"] == 1
    assert body["intervention_stats"]["no_result_count"] == 1
    assert body["intervention_stats"]["by_status"] == {"finished": 3}


# --- dashboard da pessoa de confiança ----------------------------------------


def test_trusted_dashboard_404_when_relationship_still_pending(client, db_session):
    owner_headers = _register_and_login(client, "dash-pendente-dono@example.com", "senhaForte123")
    invite = client.post(
        "/api/v1/trusted-people/invite", json={"email": "dash-pendente-confianca@example.com"}, headers=owner_headers
    ).json()
    trusted_headers = _register_and_login(client, "dash-pendente-confianca@example.com", "senhaForte123")

    response = client.get(f"/api/v1/trusted-people/{invite['id']}/dashboard", headers=trusted_headers)
    assert response.status_code == 404  # convite ainda não aceito, relacionamento não está ativo


def test_trusted_dashboard_404_for_relationship_not_owned_by_caller(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    other_headers = _register_and_login(client, "dash-outraconfianca@example.com", "senhaForte123")

    response = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=other_headers)
    assert response.status_code == 404


def test_trusted_dashboard_green_state_always_visible_without_any_permission(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    _insert_alert(db_session, owner_id, AlertState.GREEN)

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["state"] == "green"
    assert body["medication_adherence"] is None
    assert body["indicators"] is None
    assert body["alert_timeline"] is None
    assert body["deviation_timeline"] is None
    assert body["pending_support_requests"] is None


def test_trusted_dashboard_yellow_state_hidden_without_matching_permission(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    _insert_alert(db_session, owner_id, AlertState.YELLOW)

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["state"] is None
    assert body["state_reason"] is None
    assert body["alert_explanation"] is None

    _grant(client, owner_headers, relationship_id, PermissionKey.RECEIVE_ALERT_YELLOW.value)
    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["state"] == "yellow"
    # alert_explanation segue o MESMO gate de state/state_reason (pedido do
    # usuário: respaldo científico das variações também pra quem observa) —
    # nunca número por indicador, só o texto agregado por motor.
    assert body["alert_explanation"] is not None
    assert body["alert_explanation"]["state"] == "yellow"
    assert "baseline_mean" not in str(body["alert_explanation"])


def test_trusted_dashboard_alert_explanation_carries_real_scientific_context(client, db_session):
    """Diferente do teste acima (Alert inserido direto, sem motor
    nenhum convergindo): aqui o desvio é real, então `engines` vem
    preenchido de verdade e `trusted_person_scientific_context` roda —
    ver app/services/psychoeducation.py."""
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    for days_ago in range(12, 2, -1):
        _post_checkin(client, owner_headers, days_ago, mood=4)
    for days_ago in (2, 1, 0):
        _post_checkin(client, owner_headers, days_ago, mood=1)
    client.post("/api/v1/deviation/run", headers=owner_headers)
    client.post("/api/v1/alerts/sync", headers=owner_headers)

    _grant(client, owner_headers, relationship_id, PermissionKey.RECEIVE_ALERT_YELLOW.value)
    _grant(client, owner_headers, relationship_id, PermissionKey.RECEIVE_ALERT_RED.value)

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    explanation = body["alert_explanation"]
    assert explanation is not None
    assert len(explanation["engines"]) >= 1
    engine = explanation["engines"][0]
    assert engine["scientific_context"]
    assert "baseline_mean" not in engine  # forma pobre de propósito — sem número por indicador
    assert "indicators" not in engine


def test_trusted_dashboard_red_state_requires_its_own_permission_not_yellows(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    _insert_alert(db_session, owner_id, AlertState.RED)
    _grant(client, owner_headers, relationship_id, PermissionKey.RECEIVE_ALERT_YELLOW.value)

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["state"] is None  # só tem permissão pra AMARELO, estado real é VERMELHO

    _grant(client, owner_headers, relationship_id, PermissionKey.RECEIVE_ALERT_RED.value)
    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["state"] == "red"


def test_trusted_dashboard_medication_adherence_gated_by_permission(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    medication = client.post("/api/v1/medications", json={"name": "Sertralina"}, headers=owner_headers).json()
    schedule = client.post(
        f"/api/v1/medications/{medication['id']}/schedules", json={"time_of_day": "08:00:00"}, headers=owner_headers
    ).json()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client.post(
        f"/api/v1/medications/{medication['id']}/schedules/{schedule['id']}/events",
        json={"scheduled_for": now, "status": "taken"},
        headers=owner_headers,
    )

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["medication_adherence"] is None

    _grant(client, owner_headers, relationship_id, PermissionKey.VIEW_MEDICATION.value)
    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["medication_adherence"]["taken_count"] == 1


def test_trusted_dashboard_indicators_limited_to_scope(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    for days_ago in range(6):
        _post_checkin(client, owner_headers, days_ago, mood=3, energy=4)
    client.post("/api/v1/baseline/mood/recompute", headers=owner_headers)
    client.post("/api/v1/baseline/energy/recompute", headers=owner_headers)

    _grant(
        client,
        owner_headers,
        relationship_id,
        PermissionKey.VIEW_SPECIFIC_INDICATORS.value,
        indicator_scope=["mood"],
    )

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    keys = {t["indicator_key"] for t in body["indicators"]}
    assert keys == {"mood"}  # energy liberado no baseline, mas fora do indicator_scope concedido


def test_trusted_dashboard_full_history_gated_by_permission(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    owner_id = _user_id(db_session, OWNER_EMAIL)
    _insert_alert(db_session, owner_id, AlertState.GREEN)

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["alert_timeline"] is None
    assert body["deviation_timeline"] is None

    _grant(client, owner_headers, relationship_id, PermissionKey.VIEW_FULL_HISTORY.value)
    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert len(body["alert_timeline"]) == 1


def test_trusted_dashboard_pending_support_requests_gated_by_help_with_task(client, db_session):
    owner_headers, trusted_headers, relationship_id = _fully_connected_relationship(client, db_session)
    intervention = client.post(
        "/api/v1/interventions/suggest", json={"type": "body_doubling_session"}, headers=owner_headers
    ).json()
    client.post(
        f"/api/v1/interventions/{intervention['id']}/request",
        json={"support_relationship_id": relationship_id},
        headers=owner_headers,
    )

    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert body["pending_support_requests"] is None

    _grant(client, owner_headers, relationship_id, PermissionKey.HELP_WITH_TASK.value)
    body = client.get(f"/api/v1/trusted-people/{relationship_id}/dashboard", headers=trusted_headers).json()
    assert len(body["pending_support_requests"]) == 1
    assert body["pending_support_requests"][0]["id"] == intervention["id"]
