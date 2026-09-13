import os
os.environ.setdefault("BOT_TOKEN","test-token")
import asyncio
from bot.services.v70_platform import code_analyze, verify_facts, source_intelligence, init_v70_tables
from bot.services.downloader import is_url

def test_v70_code_analyze_and_sources():
    assert code_analyze('def x():\n    return 1')['ok']
    assert not code_analyze('def x(:')['ok']
    assert len(verify_facts('This is a factual statement that needs a source.')['claims']) == 1
    assert source_intelligence('see https://example.com/a').get('domains') == ['example.com']

def test_downloader_url_validation_shape():
    assert is_url('https://example.com/file.mp4')
    assert not is_url('example.com/file.mp4')

def test_v70_tables():
    init_v70_tables()
