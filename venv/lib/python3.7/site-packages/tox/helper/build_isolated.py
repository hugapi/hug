import sys

dist_folder = sys.argv[1]
backend_spec = sys.argv[2]
backend_obj = sys.argv[3] if len(sys.argv) >= 4 else None

backend = __import__(backend_spec, fromlist=[None])
if backend_obj:
    backend = getattr(backend, backend_obj)

basename = backend.build_sdist(dist_folder, {"--global-option": ["--formats=gztar"]})
print(basename)
