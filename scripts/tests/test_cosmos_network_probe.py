import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


SPEC = importlib.util.spec_from_file_location(
    'private_network_probe',
    Path(__file__).resolve().parents[2] / 'experiments/cosmos-checkpointer/private_network_probe.py',
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


@pytest.mark.parametrize('resolved,expected,success', [
    (['10.30.6.4'], ['10.30.6.4', '10.30.6.5'], True),
    (['10.30.6.4', '20.1.2.3'], ['10.30.6.4'], False),
    ([], ['10.30.6.4'], False),
    (['10.30.6.4'], [], False),
])
def test_private_dns_requires_only_expected_addresses(monkeypatch, resolved, expected, success):
    monkeypatch.setattr(probe.socket, 'getaddrinfo', lambda *args: [(None, None, None, None, (value, 443)) for value in resolved])
    if success:
        assert probe.verify_dns('https://account.documents.azure.com', expected) == resolved
    else:
        with pytest.raises(RuntimeError):
            probe.verify_dns('https://account.documents.azure.com', expected)


@pytest.mark.parametrize('read_failure', [False, True])
def test_synthetic_document_is_cleaned_up(read_failure):
    container = Mock()
    written = {}
    container.create_item.side_effect = written.update
    if read_failure:
        container.read_item.side_effect = RuntimeError('read failed')
        with pytest.raises(RuntimeError, match='read failed'):
            probe.probe_container(container)
    else:
        container.read_item.side_effect = lambda *args, **kwargs: written
        assert probe.probe_container(container)['delete'] == 'passed'
    container.delete_item.assert_called_once_with(written['id'], partition_key=written['id'])


def test_failed_create_does_not_delete_existing_document():
    container = Mock()
    container.create_item.side_effect = RuntimeError('create failed')
    with pytest.raises(RuntimeError, match='create failed'):
        probe.probe_container(container)
    container.delete_item.assert_not_called()