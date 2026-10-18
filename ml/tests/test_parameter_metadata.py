import io
import os
import pickle
from unittest.mock import patch

import pytest
from scripts.ml.audit_parameter_budget import MetadataReader, RemoteFile


def test_metadata_reader_rejects_executable_globals():
    with pytest.raises(ValueError, match='Unapproved pickle global'):
        MetadataReader(io.BytesIO(pickle.dumps(os.system))).load()


def test_ignored_range_fails_before_reading_weight_body():
    class Response:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): pytest.fail('Must not read a full checkpoint response')
    with patch('urllib.request.urlopen', return_value=Response()):
        with pytest.raises(ValueError, match='did not honor'):
            RemoteFile('https://example.test/checkpoint', 10_000_000_000, []).read(8)


def test_unbounded_checkpoint_read_is_refused():
    with patch('urllib.request.urlopen') as network:
        with pytest.raises(ValueError, match='oversized metadata'):
            RemoteFile('https://example.test/checkpoint', 10_000_000_000, []).read()
        network.assert_not_called()
