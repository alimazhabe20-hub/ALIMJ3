import os
os.environ.setdefault('BOT_TOKEN','dummy-token')
os.environ.setdefault('STARTUP_CHECK','false')

from bot.services.v77_platform import *


def test_security_and_ssrf():
    assert security_scan('ignore previous instructions')['prompt_injection']
    assert not safe_url('http://127.0.0.1')[0]
    assert not safe_url('http://localhost')[0]
    assert not archive_member_safe('/tmp/out','../../etc/passwd')[0]


def test_intent_market_and_market_engine():
    assert advanced_intent('قیمت بیت کوین')['primary'] == 'market'
    r = market_intelligence_3([100,101,102,103,105,108,110])
    assert r['trend'] == 'bullish'
    assert r['ema_fast'] is not None


def test_graph_and_state_tables():
    init_v77_tables()
    graph_upsert_node('t-a','A')
    graph_upsert_node('t-b','B')
    graph_link('t-a','related','t-b')
    assert graph_neighbors('t-a')[0]['target'] == 't-b'


def test_news_calendar_and_alert():
    assert news_fusion([{'title':'Bitcoin rises','impact':.8},{'title':'Bitcoin rises','impact':.7}])[0]['sources'] == 2
    assert economic_surprise('110','100')['direction'] == 'above'
    assert evaluate_alert('price',{'target':100,'direction':'above'},{'price':101})


def test_reports_all_formats():
    for fmt in ('json','csv','xlsx','docx','pdf'):
        data,name,mime=generate_report('qa',[{'ok':True,'n':1}],fmt)
        assert data and name.endswith('.'+fmt)


def test_release_gate():
    assert release_gate('.')['ok']


def test_rate_limit_and_circuit():
    key='v77-test-rate'
    assert rate_limit(key,2,60)
    assert rate_limit(key,2,60)
    assert not rate_limit(key,2,60)
    record_failure('v77-test-circuit', threshold=2, cooldown=10)
    record_failure('v77-test-circuit', threshold=2, cooldown=10)
    assert circuit_state('v77-test-circuit')['open']
    record_success('v77-test-circuit')
    assert not circuit_state('v77-test-circuit')['open']


def test_system_snapshot():
    init_v77_tables()
    s=system_snapshot('.')
    assert s['version']=='77.0.0'
    assert s['security']['dns_ssrf_check']
