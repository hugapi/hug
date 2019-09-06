from coverage.control import Coverage
from coveralls.report import CoverallsReporter


class coveralls(Coverage):
    def coveralls(self, base_dir, ignore_errors=False, merge_file=None):
        reporter = CoverallsReporter(self, self.config)
        reporter.find_file_reporters(None)
        return reporter.report(base_dir, ignore_errors=ignore_errors, merge_file=merge_file)
