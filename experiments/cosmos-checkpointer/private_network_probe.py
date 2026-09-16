"""Verify private Cosmos DNS and one synthetic managed-identity CRUD cycle."""

import json
import os
import socket
import uuid
from urllib.parse import urlparse


def verify_dns(endpoint, expected_addresses):
    hostname = urlparse(endpoint).hostname
    if not hostname or not endpoint.startswith('https://'):
        raise ValueError('A HTTPS Cosmos endpoint is required')
    resolved = sorted({entry[4][0] for entry in socket.getaddrinfo(hostname, 443)})
    if not resolved or not expected_addresses or not set(resolved) <= set(expected_addresses):
        raise RuntimeError(f'DNS does not resolve exclusively to the expected endpoint: {resolved}')
    return resolved


def probe_container(container):
    document_id = f'private-network-probe-{uuid.uuid4()}'
    document = {'id': document_id, 'partition_key': document_id, 'purpose': 'private-network-validation'}
    created = False
    try:
        container.create_item(document)
        created = True
        result = container.read_item(document_id, partition_key=document_id)
        if any(result.get(key) != value for key, value in document.items()):
            raise RuntimeError('Cosmos read did not match the synthetic write')
    finally:
        if created:
            container.delete_item(document_id, partition_key=document_id)
    return {'create': 'passed', 'read': 'passed', 'delete': 'passed', 'document_id': document_id}


def main():
    from azure.cosmos import CosmosClient
    from azure.identity import ManagedIdentityCredential

    endpoint = os.environ['COSMOS_ENDPOINT']
    addresses = verify_dns(endpoint, os.environ['EXPECTED_PRIVATE_IPS'].split(','))
    with ManagedIdentityCredential(client_id=os.environ['AZURE_CLIENT_ID']) as credential:
        with CosmosClient(endpoint, credential=credential) as client:
            container = client.get_database_client('threat-assessment-agent').get_container_client('checkpoints')
            operations = probe_container(container)
    print(json.dumps({'dns_addresses': addresses, 'operations': operations, 'checkpointing_enabled': False}))


if __name__ == '__main__':
    main()