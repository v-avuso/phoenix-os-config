"""Native GitHub resolver regression; run by the pinned package's pytest hook."""
import asyncio
import io
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

try:
    from instawow import ctx
    from instawow._sources.github import GithubResolver
    from instawow.wow_installations import Flavour
    from instawow.resolvers import BaseResolver
    from instawow.definitions import Defn
    from instawow.results import InternalError
except ImportError as error:
    raise unittest.SkipTest('requires the pinned InstaWoW Python environment') from error


class RangeResponse:
    ok = True
    status = 206
    def __init__(self, data, start, end):
        self.headers = {'Content-Range': f'bytes {start}-{end}/{len(data)}'}
        self.data = data[start:end + 1]
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def read(self):
        return self.data


class ExplicitRangeTests(unittest.IsolatedAsyncioTestCase):
    async def check_archive(self, count, toc_last):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            if not toc_last:
                archive.writestr('Fixture/Fixture.toc', '## Interface: 120105\n')
            for number in range(count):
                archive.writestr(f'Fixture/voice-{number}.txt', 'payload' * 10)
            if toc_last:
                archive.writestr('Fixture/Fixture.toc', '## Interface: 120105\n')
        data = buffer.getvalue()
        requests = []
        class Client:
            def get(client, url, **kwargs):
                header = kwargs['headers'].get('Range', '')
                self.assertRegex(header, r'^bytes=\d+-\d+$',
                                 'suffix/open ranges and full-ZIP fallback are forbidden')
                start, end = map(int, header.removeprefix('bytes=').split('-'))
                self.assertLessEqual(end, len(data) - 1)
                requests.append((start, end))
                return RangeResponse(data, start, end)
        token = ctx.http.web_client.set(Client())
        asset = dict(name='Fixture.zip', state='uploaded', content_type='application/zip',
                     url='https://fixture.invalid/asset', size=len(data))
        try:
            with patch.object(GithubResolver, 'make_request_headers', return_value={}):
                result = await GithubResolver()._GithubResolver__find_match_from_zip_contents(
                    [asset], Flavour.Mainline)
        finally:
            ctx.http.web_client.reset(token)
        self.assertEqual(result, asset)
        self.assertEqual(requests[0], (max(0, len(data) - 25000), len(data) - 1))
        if count == 1000:
            self.assertGreater(len(requests), 1, 'exercise large central directory and TOC ranges')

    async def test_small_archive_uses_explicit_complete_range(self):
        await self.check_archive(0, True)

    async def test_large_directory_and_first_toc_use_bounded_ranges(self):
        await self.check_archive(1000, False)

    async def test_last_toc_has_explicit_end(self):
        await self.check_archive(1000, True)


class DeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_slow_resolver_isolated_from_ready_result(self):
        class FixtureResolver(BaseResolver):
            metadata = SimpleNamespace(strategies=frozenset())
            async def resolve_one(self, defn, metadata):
                if defn.alias == 'slow':
                    await asyncio.sleep(10)
                return 'ready'
        resolver = FixtureResolver()
        with patch.dict('os.environ', INSTAWOW_NETWORK_TIMEOUT='0.02'):
            values = await asyncio.gather(
                resolver.resolve_one(Defn('fixture', 'slow'), None),
                resolver.resolve_one(Defn('fixture', 'fast'), None), return_exceptions=True)
        self.assertIsInstance(values[0], InternalError)
        self.assertIn('budget exhausted', str(values[0]))
        self.assertEqual(values[1], 'ready')

    async def test_socket_timeout_keeps_its_original_error(self):
        class FixtureResolver(BaseResolver):
            metadata = SimpleNamespace(strategies=frozenset())
            async def resolve_one(self, defn, metadata):
                raise TimeoutError('socket read timed out')
        with self.assertRaisesRegex(TimeoutError, 'socket read timed out'):
            await FixtureResolver().resolve_one(Defn('fixture', 'addon'), None)

    async def test_download_reuses_resolution_deadline(self):
        class FixtureResolver(BaseResolver):
            metadata = SimpleNamespace(strategies=frozenset())
            async def resolve_one(self, defn, metadata):
                return 'ready'
        resolver = FixtureResolver()
        defn = Defn('fixture', 'addon', '123')
        with patch.dict('os.environ', INSTAWOW_NETWORK_TIMEOUT='0.01'):
            await resolver.resolve_one(defn, None)
        await asyncio.sleep(.02)
        # CLI aliases without IDs still share the canonical resolution deadline.
        with self.assertRaises(InternalError):
            async with resolver._network_timeout(Defn('fixture', 'addon')):
                await asyncio.sleep(.01)


if __name__ == '__main__':
    unittest.main()
