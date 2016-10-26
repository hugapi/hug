from hug._reloader import FileCheckerThread

def test_reloader(tmpdir, monkeypatch):
    module_path = tmpdir.join('module.py')
    module = module_path.open('w')
    module.close()
    monkeypatch.syspath_prepend(tmpdir)

    lockfile_path = tmpdir.join('lockfile')
    lockfile = lockfile_path.open('w')
    lockfile.close()
    print(lockfile_path.ensure())
    checks = FileCheckerThread(lockfile_path, 200)

    with checks:
        assert checks.status is None
        # module.write('hello!')

    assert checks.status is not None
